"""Offline exact-lease push tests for the opt-in pinned original engine.

Network: disposable local bare Git remote only. No models or GitHub mutations.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from issue_orchestrator.execution import git_push_operations as ops
except ImportError:
    ops = None


@unittest.skipUnless(ops is not None and hasattr(ops, "io570_exact_lease_push_args"),
                     "pinned original engine and exact-lease patch not installed")
class ExactLeaseTests(unittest.TestCase):
    def git(self, *args, cwd, check=True):
        cp = subprocess.run(["git", *args], cwd=cwd, text=True,
                            capture_output=True, check=False, timeout=20)
        if check and cp.returncode:
            raise AssertionError(f"git command failed: {args}: {cp.stderr}")
        return cp

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="io570-s2-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.remote, self.work = root / "origin.git", root / "work"
        self.branch = "20-exact-lease/agent"
        self.git("init", "--bare", str(self.remote), cwd=root)
        self.git("init", "-b", "main", str(self.work), cwd=root)
        self.git("config", "user.name", "Stage-2 QA", cwd=self.work)
        self.git("config", "user.email", "qa@example.invalid", cwd=self.work)
        (self.work / "test.txt").write_text("baseline\n")
        self.git("add", "test.txt", cwd=self.work)
        self.git("commit", "-m", "baseline", cwd=self.work)
        self.git("remote", "add", "origin", str(self.remote), cwd=self.work)
        self.git("push", "origin", "main", cwd=self.work)
        self.git("config", "remote.origin.fetch",
                 "+refs/heads/main:refs/remotes/origin/main", cwd=self.work)
        self.git("checkout", "-b", self.branch, cwd=self.work)
        self.commit("first agent change")
        enabled = patch.dict(os.environ, {"ISSUE_ORCHESTRATOR_IO570_EXACT_LEASE_PUSH": "1"})
        enabled.start()
        self.addCleanup(enabled.stop)

    def commit(self, message):
        with (self.work / "test.txt").open("a") as f:
            f.write(message + "\n")
        self.git("add", "test.txt", cwd=self.work)
        self.git("commit", "-m", message, cwd=self.work)
        return self.git("rev-parse", "HEAD", cwd=self.work).stdout.strip()

    def run_git(self, worktree, args, *, check=True, timeout_s=None, env=None):
        c = subprocess.run(["git", *args], cwd=worktree, text=True,
                           capture_output=True, check=False, timeout=timeout_s or 20, env=env)
        if check and c.returncode:
            raise RuntimeError(c.stderr)
        return SimpleNamespace(returncode=c.returncode, stdout=c.stdout, stderr=c.stderr)

    def prepare(self, branch=None, remote="origin", **kw):
        return ops.io570_exact_lease_push_args(self.run_git, self.work, remote,
                                                 branch or self.branch, **kw)

    def remote_sha(self):
        r = self.git("ls-remote", "origin", f"refs/heads/{self.branch}", cwd=self.work)
        return r.stdout.split()[0] if r.stdout.strip() else ""

    def test_initial_push_empty_exact_lease(self):
        self.assertEqual(self.remote_sha(), "")
        args = self.prepare()
        self.assertEqual(args, ["push", f"--force-with-lease=refs/heads/{self.branch}:",
                                "-u", "origin", f"HEAD:refs/heads/{self.branch}"])
        self.git(*args, cwd=self.work)
        self.assertEqual(self.remote_sha(), self.git("rev-parse", "HEAD", cwd=self.work).stdout.strip())

    def test_limited_fetch_tracking_absent_does_not_break_push(self):
        self.git("push", "origin", f"HEAD:refs/heads/{self.branch}", cwd=self.work)
        original = self.remote_sha()
        self.git("update-ref", "-d", f"refs/remotes/origin/{self.branch}",
                 cwd=self.work, check=False)
        self.assertNotEqual(0, self.git("show-ref", "--verify", "--quiet",
              f"refs/remotes/origin/{self.branch}", cwd=self.work, check=False).returncode)
        sha = self.commit("second agent change")
        args = self.prepare()
        self.assertIn(f"--force-with-lease=refs/heads/{self.branch}:{original}", args)
        self.assertNotIn("--no-verify", args)
        self.git(*args, cwd=self.work)
        self.assertEqual(self.remote_sha(), sha)

    def test_remote_divergence_refuses_before_push(self):
        self.git("push", "origin", f"HEAD:refs/heads/{self.branch}", cwd=self.work)
        root = self.work.parent
        other = root / "other"
        self.git("clone", str(self.remote), str(other), cwd=root)
        self.git("config", "user.name", "Other", cwd=other)
        self.git("config", "user.email", "other@example.invalid", cwd=other)
        self.git("checkout", "-b", self.branch, f"origin/{self.branch}", cwd=other)
        (other / "other.txt").write_text("other\n")
        self.git("add", "other.txt", cwd=other)
        self.git("commit", "-m", "other commit", cwd=other)
        self.git("push", "origin", self.branch, cwd=other)
        expected = self.remote_sha()
        self.commit("diverging local change")
        with self.assertRaisesRegex(ValueError, "does not belong to local HEAD history"):
            self.prepare()
        self.assertEqual(self.remote_sha(), expected)

    def test_remote_race_is_rejected_by_git_cas(self):
        self.git("push", "origin", f"HEAD:refs/heads/{self.branch}", cwd=self.work)
        old = self.remote_sha()
        self.commit("agent tip")
        args = self.prepare()
        self.assertIn(old, " ".join(args))
        other = self.work.parent / "other"
        self.git("clone", str(self.remote), str(other), cwd=self.work.parent)
        self.git("config", "user.name", "Other", cwd=other)
        self.git("config", "user.email", "other@example.invalid", cwd=other)
        self.git("checkout", "-b", self.branch, f"origin/{self.branch}", cwd=other)
        (other / "other.txt").write_text("race\n")
        self.git("add", "other.txt", cwd=other)
        self.git("commit", "-m", "remote race", cwd=other)
        self.git("push", "origin", self.branch, cwd=other)
        latest = self.remote_sha()
        self.assertNotEqual(0, self.git(*args, cwd=self.work, check=False).returncode)
        self.assertEqual(latest, self.remote_sha())

    def test_dry_run_and_restricted_issue_branch(self):
        args = self.prepare(dry_run=True)
        self.assertIn("--dry-run", args)
        for branch in ("7-old/agent", "22-not-scoped/agent",
                       "20-bad/main", "21-bad/agent/extra"):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                self.prepare(branch=branch)
        with self.assertRaises(ValueError):
            self.prepare(remote="production")

    def test_missing_optin_and_wrong_head(self):
        with self.assertRaisesRegex(ValueError, "expected agent branch"):
            self.prepare(branch="21-other/agent")
        os.environ.pop("ISSUE_ORCHESTRATOR_IO570_EXACT_LEASE_PUSH", None)
        with self.assertRaisesRegex(ValueError, "opt-in"):
            self.prepare()


    def test_original_git_working_copy_can_publish_new_branch(self):
        from issue_orchestrator.execution.git_working_copy import GitWorkingCopy
        outcome = GitWorkingCopy().push(self.work)
        self.assertTrue(outcome.success, outcome.message)
        self.assertEqual(self.remote_sha(),
                         self.git("rev-parse", "HEAD", cwd=self.work).stdout.strip())

    def test_original_git_working_copy_existing_remote_with_limited_refspec(self):
        from issue_orchestrator.execution.git_working_copy import GitWorkingCopy
        self.git("push", "origin", f"HEAD:refs/heads/{self.branch}", cwd=self.work)
        self.git("update-ref", "-d", f"refs/remotes/origin/{self.branch}",
                 cwd=self.work, check=False)
        next_sha = self.commit("agent incremental")
        outcome = GitWorkingCopy().push(self.work)
        self.assertTrue(outcome.success, outcome.message)
        self.assertEqual(self.remote_sha(), next_sha)

    def test_original_git_working_copy_preflight_leaves_remote_unchanged(self):
        from issue_orchestrator.execution.git_working_copy import GitWorkingCopy
        before = self.remote_sha()
        result = GitWorkingCopy().push_preflight(self.work)
        self.assertTrue(result.would_succeed, result.error)
        self.assertEqual(self.remote_sha(), before)

    def test_original_git_working_copy_rejects_skipped_hooks(self):
        from issue_orchestrator.execution.git_working_copy import GitWorkingCopy
        before = self.remote_sha()
        result = GitWorkingCopy().push(self.work, skip_hooks=True)
        self.assertFalse(result.success)
        self.assertIn("forbids skipped hooks", result.message)
        self.assertEqual(self.remote_sha(), before)


if __name__ == "__main__":
    unittest.main()
