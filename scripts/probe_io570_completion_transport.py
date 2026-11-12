#!/usr/bin/env python3
"""No-model real coding-done transport through native Codex sandbox.

Creates a synthetic linked Git worktree and a temporary HTTP canary *only*.
Exercises original completion_submit.submit_completion_file with synthetic
per-run capability and scoped bearer, never the real Orchestrator Control API.
No real tokens, PRs, GitHub API or model execution. Prints no secret bytes.
"""
from __future__ import annotations

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
import base64
import json
import os
import subprocess
import tempfile

from issue_orchestrator.domain.models import AgentConfig
from issue_orchestrator.domain.sandbox_scope import SandboxScopeContext, compute_session_scope
from issue_orchestrator.execution.agent_runner_providers.codex import CodexProvider
from issue_orchestrator.infra.hooks.codex_session import verify_codex_runtime_home

PILOT_WORKTREES = Path.home() / "projects/adt-orchestrator-pilot-worktrees"
CODEX = Path.home() / ".local/share/adt-io570/codex-0.167.0/bin/codex"
CALLBACK_ALIAS = "ISSUE_ORCHESTRATOR_AGENT_CALLBACK_BEARER"
CALLBACK_ORIGINAL = "ISSUE_ORCHESTRATOR_AGENT_CALLBACK_TOKEN"
CANARY = b'{"io570_synthetic_completion":true}'
CAPABILITY = "IO570_SYNTHETIC_CAPABILITY"
BEARER = "IO570_SYNTHETIC_CALLBACK_BEARER"
ENTRY_ID = "a" * 64


def git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, text=True,
        capture_output=True, check=True, timeout=20,
    )


def main() -> int:
    if os.environ.get("ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY") != "1":
        raise RuntimeError("Scoped proxy opt-in not set")
    if not PILOT_WORKTREES.is_dir() or PILOT_WORKTREES.is_symlink():
        raise RuntimeError("Pilot worktree parent missing or unsafe")
    if not CODEX.is_file():
        raise RuntimeError("Pinned Codex missing")
    if any(os.environ.get(name) for name in ("OPENAI_API_KEY", "CODEX_API_KEY")):
        raise RuntimeError("Paid API credentials forbidden")
    received = Event()
    expected_sha = sha256(CANARY).hexdigest()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                self.send_error(413)
                return
            raw = self.rfile.read(length)
            if (
                self.path != "/api/completion/submissions"
                or self.headers.get("Authorization") != f"Bearer {BEARER}"
            ):
                self.send_error(401)
                return
            if self.headers.get("X-Completion-Capability") != CAPABILITY:
                self.send_error(401)
                return
            try:
                submitted = json.loads(raw)
                valid = (
                    submitted.get("content_sha256") == expected_sha
                    and submitted.get("submission_key") == expected_sha
                    and base64.b64decode(
                        submitted.get("raw_bytes", ""), validate=True
                    ) == CANARY
                )
            except (ValueError, TypeError, KeyError):
                valid = False
            if not valid:
                self.send_error(422)
                return
            received.set()
            answer = json.dumps({
                "entry_id": ENTRY_ID,
                "content_sha256": expected_sha,
            }).encode("ascii")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(answer)))
            self.end_headers()
            self.wfile.write(answer)

        def log_message(self, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(
                prefix=".io570-callback-", dir=PILOT_WORKTREES
            ) as td:
                root = Path(td)
                base, linked = root / "base", root / "linked"
                git("init", "-q", "-b", "main", str(base))
                (base / "README").write_text("synthetic\n")
                git("add", "README", cwd=base)
                git(
                    "-c", "user.name=IO570Probe",
                    "-c", "user.email=probe@example.invalid",
                    "commit", "-qm", "synthetic", cwd=base,
                )
                git(
                    "worktree", "add", "-q", "-b", "7-io570-callback/agent",
                    str(linked), "HEAD", cwd=base,
                )
                candidate = linked / "synthetic-completion.json"
                candidate.write_bytes(CANARY)
                scope = compute_session_scope(
                    AgentConfig(
                        prompt_path=Path(".prompts/dev.md"),
                        prompt_relative=".prompts/dev.md",
                        provider="codex", sandbox=True,
                    ),
                    SandboxScopeContext(task_kind="code", worktree=linked),
                )
                if scope is None:
                    raise RuntimeError("No sandbox scope")
                argv = CodexProvider().apply_scope(scope)
                if argv[:5] != ["--strict-config", "-a", "never", "-C", str(linked)]:
                    raise RuntimeError("Unexpected sandbox flags")
                if "features.network_proxy=true" not in argv:
                    raise RuntimeError("Expected managed network proxy")
                if 'shell_environment_policy.ignore_default_excludes=false' not in argv:
                    raise RuntimeError("Strict token filtering not configured")

                client = r'''
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from issue_orchestrator.entrypoints.cli_tools.completion_submit import submit_completion_file
from issue_orchestrator.entrypoints.cli_tools.agent_callback import api_request_headers

mode, candidate = sys.argv[1:]
assert not os.getenv("ISSUE_ORCHESTRATOR_AGENT_CALLBACK_TOKEN")
assert os.getenv("ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY") == "1"
assert not os.getenv("GH_TOKEN") and not os.getenv("GITHUB_TOKEN")
assert not os.getenv("OPENAI_API_KEY") and not os.getenv("CODEX_API_KEY")
try:
    result = submit_completion_file(Path(candidate))
    if mode != "positive":
        print("INVALID_BEARER_ACCEPTED")
        sys.exit(5)
    if result.entry_id != ("a" * 64):
        print("INVALID_RECEIPT")
        sys.exit(6)
    print("REAL_CODING_DONE_TRANSPORT=PASS")
except HTTPError as exc:
    if mode == "missing-bearer" and exc.code == 401:
        print("MISSING_BEARER_DENY=PASS")
    else:
        print("TRANSPORT_HTTP_FAILURE=" + str(exc.code))
        sys.exit(7)
except Exception as exc:
    print("TRANSPORT_ERROR=" + type(exc).__name__)
    sys.exit(8)
'''
                for mode in ("positive", "missing-bearer"):
                    received.clear()
                    env = os.environ.copy()
                    for forbidden in (
                        CALLBACK_ORIGINAL, CALLBACK_ALIAS, "GH_TOKEN",
                        "GITHUB_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY",
                        "ISSUE_ORCHESTRATOR_API_TOKEN",
                    ):
                        env.pop(forbidden, None)
                    env["ISSUE_ORCHESTRATOR_API_PORT"] = str(server.server_port)
                    env["ISSUE_ORCHESTRATOR_COMPLETION_CAPABILITY"] = CAPABILITY
                    env["ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY"] = "1"
                    env["CODEX_HOME"] = str(verify_codex_runtime_home())
                    if mode == "positive":
                        env[CALLBACK_ALIAS] = BEARER
                    cmd = [
                        str(CODEX), "sandbox", "--permission-profile",
                        "issue_orchestrator_scope", "-C", str(linked),
                        *argv[5:], "--", "/usr/bin/python3",
                        "-c", client, mode, str(candidate),
                    ]
                    result = subprocess.run(
                        cmd, cwd=linked, env=env, text=True,
                        capture_output=True, timeout=35, check=False,
                    )
                    wanted = (
                        "REAL_CODING_DONE_TRANSPORT=PASS" if mode == "positive"
                        else "MISSING_BEARER_DENY=PASS"
                    )
                    ok = (
                        result.returncode == 0
                        and wanted in result.stdout
                        and received.is_set() == (mode == "positive")
                    )
                    print(wanted.split("=")[0] + "=" + ("PASS" if ok else "FAIL"))
                    if not ok:
                        print("PHASE=" + mode)
                        print("SANDBOX_EXIT=" + str(result.returncode))
                        print("CLIENT_STATUS=" + " ".join(
                            result.stdout.strip().splitlines()
                        )[-240:])
                        print("SANDBOX_ERROR_TYPE=NONZERO" if result.stderr
                              else "SANDBOX_ERROR_TYPE=NONE")
                        return 1
            print("MODE=NO_MODEL_NO_GITHUB_API")
            print("IO570_COMPLETION_TRANSPORT_GATE=PASS")
            return 0
        finally:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
