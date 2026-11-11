"""Offline validation of the patched original Git per-Issue reference permissions.

Requires the original source to be patched in a dedicated CI checkout.
The default Pilot CI skips this test: it has no access to the patched engine.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SOURCE = os.environ.get("IO570_PATCHED_ORCHESTRATOR_SOURCE")
FLAG = "ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS"


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


@unittest.skipUnless(SOURCE, "Requires patched original engine checkout")
class OriginalEngineIsolatedRefTests(unittest.TestCase):
    def test_namespaced_git_branch_commit_and_main_ref_deny(self) -> None:
        from issue_orchestrator.adapters.worktree._worktree import (
            generate_branch_name as worktree_branch_name,
        )
        from issue_orchestrator.domain.branch_naming import (
            generate_branch_name as shared_branch_name,
        )
        from issue_orchestrator.execution.agent_runner_providers.git_worktree_access import (
            git_worktree_filesystem_rules,
            resolve_git_worktree_access,
        )

        with patch.dict(os.environ, {FLAG: "1"}):
            self.assertEqual(worktree_branch_name(7, "Pilot"), "7-pilot/agent")
            self.assertEqual(shared_branch_name(7, "Pilot"), "7-pilot/agent")

            with tempfile.TemporaryDirectory(prefix="io570-isolated-ref-test-") as temp:
                base, linked = Path(temp) / "base", Path(temp) / "linked"
                base.mkdir()
                self.assertEqual(git("init", "-q", "-b", "main", cwd=base).returncode, 0)
                (base / "data.txt").write_text("original\n", encoding="utf-8")
                self.assertEqual(git("add", "data.txt", cwd=base).returncode, 0)
                baseline = git(
                    "-c", "user.name=CI", "-c", "user.email=ci@example.invalid",
                    "commit", "-qm", "baseline", cwd=base
                )
                self.assertEqual(baseline.returncode, 0, baseline.stderr)

                branch = worktree_branch_name(7, "Pilot")
                made = git(
                    "worktree", "add", "-q", "-b", branch, str(linked), "HEAD",
                    cwd=base
                )
                self.assertEqual(made.returncode, 0, made.stderr)

                access = resolve_git_worktree_access(linked)
                rules = git_worktree_filesystem_rules(access)
                writes = {p for p, perm in rules if perm == "write"}
                common = base / ".git"
                refdir = common / "refs/heads/7-pilot"
                logdir = common / "logs/refs/heads/7-pilot"

                self.assertIn(str(refdir), writes)
                self.assertIn(str(logdir), writes)
                self.assertNotIn(str(common / "refs/heads"), writes)
                self.assertNotIn(str(common / "logs/refs/heads"), writes)
                self.assertNotIn(str(refdir / "agent"), writes)
                self.assertNotIn(str(logdir / "agent"), writes)
                self.assertFalse(any(Path(p).is_file() for p in writes))

                # Simulate Linux: the shared ref roots cannot create new .locks.
                parents = [
                    common / "refs/heads",
                    common / "logs/refs/heads",
                ]
                original_modes = [(p, p.stat().st_mode & 0o777) for p in parents]
                try:
                    for directory in parents:
                        directory.chmod(0o555)
                    (linked / "data.txt").write_text("updated\n", encoding="utf-8")
                    self.assertEqual(git("add", "data.txt", cwd=linked).returncode, 0)
                    committed = git(
                        "-c", "user.name=CI", "-c", "user.email=ci@example.invalid",
                        "commit", "-qm", "change", cwd=linked
                    )
                    self.assertEqual(committed.returncode, 0, committed.stderr)
                    newsha = git("rev-parse", "HEAD", cwd=linked).stdout.strip()
                    attempted = git(
                        "update-ref", "refs/heads/main", newsha, cwd=linked
                    )
                    self.assertNotEqual(attempted.returncode, 0)
                    self.assertTrue(
                        "Permission denied" in attempted.stderr
                        or "Read-only file system" in attempted.stderr,
                        attempted.stderr,
                    )
                finally:
                    for directory, mode in original_modes:
                        directory.chmod(mode)

    def test_legacy_root_ref_fail_closed(self) -> None:
        from issue_orchestrator.domain.sandbox_scope import SandboxUnsupportedError
        from issue_orchestrator.execution.agent_runner_providers.git_worktree_access import (
            git_worktree_filesystem_rules,
            resolve_git_worktree_access,
        )
        with tempfile.TemporaryDirectory(prefix="io570-legacy-ref-test-") as temp:
            base, linked = Path(temp) / "base", Path(temp) / "linked"
            base.mkdir()
            self.assertEqual(git("init", "-q", "-b", "main", cwd=base).returncode, 0)
            (base / "data.txt").write_text("fixture\n")
            self.assertEqual(git("add", "data.txt", cwd=base).returncode, 0)
            self.assertEqual(git(
                "-c", "user.name=CI", "-c", "user.email=ci@example.invalid",
                "commit", "-qm", "base", cwd=base
            ).returncode, 0)
            self.assertEqual(git(
                "worktree", "add", "-q", "-b", "7-legacy", str(linked), "HEAD",
                cwd=base
            ).returncode, 0)

            with patch.dict(os.environ, {FLAG: "1"}):
                with self.assertRaises(SandboxUnsupportedError):
                    git_worktree_filesystem_rules(
                        resolve_git_worktree_access(linked)
                    )


if __name__ == "__main__":
    unittest.main()
