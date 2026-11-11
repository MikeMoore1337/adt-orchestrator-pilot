"""Original pinned engine: explicit IO570 managed loopback opt-in, no models."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = os.environ.get("IO570_PATCHED_ORCHESTRATOR_SOURCE")


def git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        check=True, timeout=10,
    )


@unittest.skipUnless(SOURCE, "Only in source-pinned original-engine CI")
class IO570ManagedProxyPolicy(unittest.TestCase):
    def test_explicit_pilot_only_and_default_stays_deny(self) -> None:
        from issue_orchestrator.domain.models import AgentConfig
        from issue_orchestrator.domain.sandbox_scope import (
            SandboxScopeContext, SandboxUnsupportedError, compute_session_scope,
        )
        from issue_orchestrator.execution.agent_runner_providers.sandbox import (
            build_codex_sandbox_argv,
        )
        from issue_orchestrator.execution.agent_runner_providers.git_worktree_access import (
            resolve_git_worktree_access,
        )

        base_dir = Path.home() / "projects/adt-orchestrator-pilot-worktrees"
        base_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".io570-test-", dir=base_dir) as tmp:
            base, linked = Path(tmp) / "base", Path(tmp) / "linked"
            git("init", "-q", "-b", "main", str(base))
            (base / "readme").write_text("synthetic\n")
            git("add", "readme", cwd=base)
            git(
                "-c", "user.name=CI",
                "-c", "user.email=ci@example.invalid",
                "commit", "-qm", "synthetic", cwd=base,
            )
            git(
                "worktree", "add", "-q", "-b", "7-test/agent",
                str(linked), "HEAD", cwd=base,
            )
            scope = compute_session_scope(
                AgentConfig(
                    prompt_path=Path(".prompts/dev.md"),
                    prompt_relative=".prompts/dev.md",
                    provider="codex", sandbox=True,
                ),
                SandboxScopeContext(task_kind="code", worktree=linked),
            )
            self.assertIsNotNone(scope)
            access = resolve_git_worktree_access(linked)

            with patch.dict(os.environ, {
                "ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY": "",
                "ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS": "1",
            }):
                default = build_codex_sandbox_argv(scope, git_access=access)
            self.assertNotIn("features.network_proxy=true", default)
            self.assertIn("network = { enabled = false }", " ".join(default))

            with patch.dict(os.environ, {
                "ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY": "1",
                "ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS": "1",
            }):
                allowed = build_codex_sandbox_argv(scope, git_access=access)
                self.assertEqual(allowed.count("features.network_proxy=true"), 1)
                actual = " ".join(allowed)
                for required in (
                    'domains = { "127.0.0.1" = "allow" }',
                    "allow_local_binding = false",
                    "allow_upstream_proxy = false",
                    "enable_socks5 = false",
                    'web_search="disabled"',
                    "~/.config/gh",
                ):
                    self.assertIn(required, actual)
                outside_path = base_dir.parent / "io570-outside-pilot-root"
                outsider = type(scope)(
                    working_directory=outside_path,
                    read_roots=(outside_path,),
                    write_roots=(outside_path,),
                    egress="model-only",
                    deny_env=scope.deny_env,
                    deny_read_files=scope.deny_read_files,
                )
                with self.assertRaises(SandboxUnsupportedError):
                    build_codex_sandbox_argv(outsider, git_access=access)

    def test_source_only_probe_is_present(self) -> None:
        # This test does not invoke Codex, a network, or GitHub.
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts/probe_io570_loopback_proxy.py").read_text()
        compile(text, "probe_io570_loopback_proxy.py", "exec")
        self.assertIn("IO570_MANAGED_PROXY_GATE=PASS", text)
        self.assertIn('("callback", "external", "other-host", "direct")', text)
        self.assertIn('"_DENY=PASS"', text)
        self.assertNotIn('str(CODEX), "exec"', text)


if __name__ == "__main__":
    unittest.main()
