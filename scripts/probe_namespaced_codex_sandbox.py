#!/usr/bin/env python3
"""No-model, fail-closed OS probe of original Codex with isolated Git refs.

This reproduces the Git metadata paths of a real issue-orchestrator session.
Creates and removes only synthetic temporary repositories and one random,
NON-SECRET canary under ~/.config/gh. Never reads the real GitHub token.
Does not run codex exec, start the engine, or spend model quota.
"""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import tempfile

from issue_orchestrator.domain.models import AgentConfig
from issue_orchestrator.domain.sandbox_scope import (
    SandboxScopeContext,
    compute_session_scope,
)
from issue_orchestrator.execution.agent_runner_providers.codex import CodexProvider
from issue_orchestrator.execution.agent_runner_providers.git_worktree_access import (
    git_worktree_filesystem_rules,
    resolve_git_worktree_access,
)
from issue_orchestrator.infra.hooks.codex_session import (
    verify_codex_runtime_home,
)

SOURCE_SHA = "d4a79824ccd806089cf3f70ec632d39b8ee255ea"
LABEL = "adt-io570-pilot-20261109"


def command(*argv: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(
        list(argv), cwd=cwd, text=True, stderr=subprocess.PIPE, timeout=20
    ).strip()


def require_environment() -> Path:
    home = Path.home()
    binary_name = shutil.which("codex")
    if not binary_name:
        raise RuntimeError("codex CLI is not on PATH")
    binary = Path(binary_name).resolve(strict=True)
    expected = home / ".local/share/adt-io570/codex-0.167.0/bin/codex"
    if binary != expected.resolve(strict=True):
        raise RuntimeError("Expected unchanged isolated Codex 0.167.0 binary")
    print("ORIGINAL_CODEX_UNMODIFIED=YES")
    if command(str(binary), "--version") != "codex-cli 0.167.0":
        raise RuntimeError("Codex version mismatch")
    if any(os.environ.get(name) for name in ("CODEX_HOME", "OPENAI_API_KEY", "CODEX_API_KEY")):
        raise RuntimeError("Parent process must not supply CODEX_HOME or API keys")
    original = home / "projects/issue-orchestrator"
    if command("git", "-C", str(original), "rev-parse", "HEAD") != SOURCE_SHA:
        raise RuntimeError("Original issue-orchestrator source pin changed")
    if os.environ.get("ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS") != "1":
        raise RuntimeError("Original engine isolated-ref opt-in is mandatory")
    import issue_orchestrator.execution.agent_runner_providers.git_worktree_access as git_policy
    patched_src = home / ".local/state/adt-io570/original-engine-namespaced-loopback/src"
    if not Path(git_policy.__file__).resolve().is_relative_to(patched_src):
        raise RuntimeError("Patched original engine source not loaded from isolated checkout")
    print("ORIGINAL_ENGINE_ISOLATED_REF_SOURCE=PASS")
    runtime = verify_codex_runtime_home()
    allowed_runtime_root = home / ".local/state/adt-io570/codex-runtime"
    if not runtime.is_relative_to(allowed_runtime_root):
        raise RuntimeError("Codex runtime outside approved isolated root")
    if runtime.is_relative_to(home / ".issue-orchestrator"):
        raise RuntimeError("Codex runtime nested under denied parent")
    return runtime


def probe(runtime: Path) -> bool:
    home = Path.home()
    gh_dir = home / ".config/gh"
    if not (gh_dir / "hosts.yml").is_file():
        raise RuntimeError("GitHub CLI auth file not present; never read its contents")
    canary = gh_dir / (".io570-linked-probe-" + secrets.token_hex(12))
    fd = os.open(canary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            target.write("HARMLESS_PROBE_ONLY\n")
        if canary.read_text(encoding="utf-8") != "HARMLESS_PROBE_ONLY\n":
            raise RuntimeError("Positive control for synthetic canary failed")

        with tempfile.TemporaryDirectory(prefix=".io570-linked-", dir=home) as tmp:
            root = Path(tmp)
            base = root / "base"
            linked = root / "linked"
            outside = root / "forbidden-write.txt"

            command("git", "init", "-q", "-b", "main", str(base))
            (base / "README.md").write_text("synthetic Git worktree\n", encoding="utf-8")
            command("git", "add", "README.md", cwd=base)
            command(
                "git", "-c", "user.name=IO570 Probe",
                "-c", "user.email=probe@example.invalid",
                "commit", "-qm", "synthetic baseline", cwd=base
            )
            command(
                "git", "worktree", "add", "-q", "-b", "7-io570-probe/agent",
                str(linked), "HEAD", cwd=base
            )
            if not (linked / ".git").is_file():
                raise RuntimeError("Fixture must be a LINKED git worktree")

            scope = compute_session_scope(
                AgentConfig(
                    prompt_path=Path(".prompts/dev.md"),
                    prompt_relative=".prompts/dev.md",
                    provider="codex",
                    sandbox=True,
                ),
                SandboxScopeContext(task_kind="code", worktree=linked),
            )
            if scope is None or "~/.config/gh" not in scope.deny_read_files:
                raise RuntimeError("Original GitHub credential deny is absent")
            args = CodexProvider().apply_scope(scope)
            if args[:5] != ["--strict-config", "-a", "never", "-C", str(linked)]:
                raise RuntimeError("Original Codex CLI sandbox argument shape changed")
            overrides = args[5:]
            if len(overrides) % 2 or any(
                overrides[i] != "-c" for i in range(0, len(overrides), 2)
            ):
                raise RuntimeError("Unreviewed Codex sandbox override detected")
            if not any(
                value.startswith("permissions.issue_orchestrator_scope=")
                for value in overrides[1::2]
            ):
                raise RuntimeError("Native permission profile was not generated")

            grants = git_worktree_filesystem_rules(resolve_git_worktree_access(linked))
            writable_file_roots = [
                path for path, grant in grants
                if grant == "write" and (
                    Path(path).is_file() or Path(path).name.endswith(".lock")
                )
            ]
            namespace = base / ".git/refs/heads/7-io570-probe"
            reflogs = base / ".git/logs/refs/heads/7-io570-probe"
            write_paths = {path for path, perm in grants if perm == "write"}
            if writable_file_roots or str(namespace) not in write_paths or str(reflogs) not in write_paths:
                raise RuntimeError("Non-isolated or exact-file Git writable roots detected")
            if str(base / ".git/refs/heads") in write_paths:
                raise RuntimeError("Shared branch refs are writable: fail closed")
            print("LINKED_WORKTREE=PASS")
            print("EXACT_GIT_FILE_WRITE_RULES=0")
            print("NAMESPACED_REF_WRITE=PASS")

            positive = linked / "positive.txt"
            quote = shlex.quote
            shell = "; ".join((
                "echo SHELL_BOOT=PASS",
                f"printf 'OK' > {quote(str(positive))}",
                f"git -C {quote(str(linked))} add -- positive.txt && "
                f"git -C {quote(str(linked))} -c user.name=IO570-Probe "
                "-c user.email=probe@example.invalid commit -qm synthetic-check "
                "&& echo GIT_COMMIT=PASS",
                f"if git -C {quote(str(linked))} update-ref refs/heads/main "
                f"$(git -C {quote(str(linked))} rev-parse HEAD) >/dev/null 2>&1; "
                "then echo MAIN_REF=WRITABLE; else echo MAIN_REF=DENIED; fi",
                f"if head -c 1 {quote(str(canary))} >/dev/null 2>&1; "
                "then echo GH_CANARY=READABLE; else echo GH_CANARY=DENIED; fi",
                f"if printf BAD > {quote(str(outside))} 2>/dev/null; "
                "then echo OUTSIDE_WRITE=ALLOWED; else echo OUTSIDE_WRITE=DENIED; fi",
            ))
            env = os.environ.copy()
            env["CODEX_HOME"] = str(runtime)
            result = subprocess.run(
                [
                    str((home / ".local/share/adt-io570/codex-0.167.0/bin/codex").resolve()),
                    "sandbox", "--permission-profile", "issue_orchestrator_scope",
                    "-C", str(linked), *overrides, "--", "/bin/sh", "-c", shell
                ],
                cwd=linked, env=env, capture_output=True, text=True, timeout=30,
                check=False
            )

            output = result.stdout
            passed = (
                result.returncode == 0
                and "SHELL_BOOT=PASS" in output
                and "GIT_COMMIT=PASS" in output
                and "MAIN_REF=DENIED" in output
                and "MAIN_REF=WRITABLE" not in output
                and (linked / "positive.txt").is_file()
                and (linked / "positive.txt").read_text(encoding="utf-8") == "OK"
                and "GH_CANARY=DENIED" in output
                and "GH_CANARY=READABLE" not in output
                and "OUTSIDE_WRITE=DENIED" in output
                and not outside.exists()
            )
            print("SANDBOX_EXIT=" + str(result.returncode))
            print("SHELL_BOOT=" + ("PASS" if "SHELL_BOOT=PASS" in output else "FAIL"))
            print("GIT_COMMIT=" + ("PASS" if "GIT_COMMIT=PASS" in output else "FAIL"))
            print("MAIN_REF_DENY=" + ("PASS" if "MAIN_REF=DENIED" in output
                  and "MAIN_REF=WRITABLE" not in output else "FAIL"))
            print(
                "GH_CANARY_DENY=" +
                ("PASS" if "GH_CANARY=DENIED" in output and
                 "GH_CANARY=READABLE" not in output else "FAIL")
            )
            print(
                "OUTSIDE_WRITE_DENY=" +
                ("PASS" if "OUTSIDE_WRITE=DENIED" in output and
                 not outside.exists() else "FAIL")
            )
            if result.stderr.strip():
                print("SANDBOX_DIAGNOSTIC=" + result.stderr.strip()[-1800:])
            print("LINKED_SANDBOX_GATE=" + ("PASS" if passed else "FAIL"))
            return passed
    finally:
        canary.unlink(missing_ok=True)


def main() -> int:
    print("MODE=NO_MODEL_NO_GITHUB_API")
    try:
        runtime = require_environment()
        return 0 if probe(runtime) else 1
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        # Never print secrets or the contents of GitHub authentication files.
        print("LINKED_SANDBOX_GATE=FAIL")
        print("PROBE_ERROR=" + type(exc).__name__ + ": " + str(exc)[:800])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
