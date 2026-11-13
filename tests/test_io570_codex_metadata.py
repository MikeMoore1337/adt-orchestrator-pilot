"""Pinned v0.10.0 Git namespace contracts with native Codex 0.167 metadata.

Only the exact protected .git/.agents/.codex/.aws empty directories may appear
beside refs/heads/<issue>/agent and its reflog. Detached sibling reviewers have
no shared branch permissions. No model, Github token or API key in these tests.

Reference: openai/codex rust-v0.167.0, protocol::PROTECTED_METADATA_PATH_NAMES,
linux-sandbox/tests/suite/nested_metadata_tests.rs.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ENGINE = os.environ.get("IO570_PATCHED_ORCHESTRATOR_SOURCE")
FLAG = "ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS"
MASKS = frozenset({".git", ".agents", ".codex", ".aws"})


def git(*args: str, cwd: Path) -> str:
    run = subprocess.run(
        ["git", *args],
        cwd=cwd, capture_output=True, text=True, check=False, timeout=20,
    )
    if run.returncode:
        raise RuntimeError(f"git {args[0]} failed: {run.stderr[:200]}")
    return run.stdout.strip()


@contextmanager
def linked_fixture(*, detached: bool = False):
    with tempfile.TemporaryDirectory(prefix="io570-codex-mask-test-") as temp:
        base = Path(temp) / "base"
        linked = Path(temp) / "linked"
        base.mkdir()
        git("init", "-q", "-b", "main", cwd=base)
        (base / "README").write_text("synthetic\n")
        git("add", "README", cwd=base)
        git("-c", "user.name=IO570", "-c",
            "user.email=probe@example.invalid",
            "commit", "-qm", "seed", cwd=base)
        branch = "8-io570-probe/agent"
        if detached:
            git("worktree", "add", "-q", "--detach",
                str(linked), "HEAD", cwd=base)
        else:
            git("worktree", "add", "-q", "-b", branch,
                str(linked), "HEAD", cwd=base)
        yield base, linked, branch


@unittest.skipUnless(ENGINE, "Only runs against exact patched upstream source")
class CodexProtectedGitNamespacesTests(unittest.TestCase):
    def setUp(self) -> None:
        from issue_orchestrator.execution.agent_runner_providers import (
            git_worktree_access as policy,
        )
        from issue_orchestrator.domain.sandbox_scope import SandboxUnsupportedError
        self.policy = policy
        self.error_type = SandboxUnsupportedError
        self.assertEqual(
            policy._CODEX_PROTECTED_METADATA, MASKS,
            "Only names documented in Codex 0.167 are permitted",
        )

    def rules(self, linked: Path) -> list[tuple[str, str]]:
        with patch.dict(os.environ, {FLAG: "1"}):
            return self.policy.git_worktree_filesystem_rules(
                self.policy.resolve_git_worktree_access(linked)
            )

    def test_empty_codex_protected_masks_are_read_only(self) -> None:
        with linked_fixture() as (base, linked, _branch):
            common = base / ".git"
            roots = [
                common / "refs/heads/8-io570-probe",
                common / "logs/refs/heads/8-io570-probe",
            ]
            pre = dict(self.rules(linked))
            self.assertTrue(all(pre[str(root)] == "write" for root in roots))
            for root in roots:
                for name in MASKS:
                    (root / name).mkdir()

            rules = self.rules(linked)
            grants = dict(rules)
            for root in roots:
                self.assertEqual(grants[str(root)], "write")
                for name in MASKS:
                    self.assertEqual(grants[str(root / name)], "read")
                    self.assertFalse(any((root / name).iterdir()))
            self.assertNotIn(str(common / "refs/heads"), [
                path for path, permission in rules if permission == "write"
            ])
            self.assertNotIn(str(common / "refs/heads/main"), [
                path for path, permission in rules if permission == "write"
            ])
            # Codex can retry without changing the Git permissions envelope.
            self.assertEqual(self.rules(linked), rules)

    def test_unknown_sibling_file_and_directory_denied(self) -> None:
        for kind in ("file", "directory", "lock"):
            with self.subTest(kind=kind), linked_fixture() as (base, linked, _):
                root = base / ".git/refs/heads/8-io570-probe"
                foreign = root / ("agent.lock" if kind == "lock" else "foreign")
                if kind == "directory":
                    foreign.mkdir()
                else:
                    foreign.write_text("not Codex metadata")
                with self.assertRaises(self.error_type):
                    self.rules(linked)

    def test_protected_masks_with_contents_or_symlinks_denied(self) -> None:
        for kind in ("file", "nested", "symlink"):
            with self.subTest(kind=kind), linked_fixture() as (base, linked, _):
                root = base / ".git/logs/refs/heads/8-io570-probe"
                mask = root / ".aws"
                if kind == "symlink":
                    target = base / "foreign-data"
                    target.mkdir()
                    mask.symlink_to(target, target_is_directory=True)
                else:
                    mask.mkdir()
                    if kind == "file":
                        (mask / "credentials").write_text("synthetic")
                    else:
                        (mask / "child").mkdir()
                with self.assertRaises(self.error_type):
                    self.rules(linked)

    def test_existing_metadata_mount_is_denied(self) -> None:
        with linked_fixture() as (base, linked, _):
            protected = base / ".git/refs/heads/8-io570-probe/.git"
            protected.mkdir()
            real_is_mount = os.path.ismount

            def mark_mount(path: object) -> bool:
                return Path(path) == protected or real_is_mount(path)

            with patch.object(self.policy.os.path, "ismount", side_effect=mark_mount):
                with self.assertRaises(self.error_type):
                    self.rules(linked)

    def test_detached_reviewer_is_private_only(self) -> None:
        with linked_fixture(detached=True) as (base, linked, _):
            access = self.policy.resolve_git_worktree_access(linked)
            self.assertIsNone(access.head_ref)
            self.assertNotEqual(access.git_dir, access.common_dir)
            grants = self.rules(linked)
            write_paths = {
                path for path, permission in grants if permission == "write"
            }
            self.assertIn(str(access.git_dir), write_paths)
            self.assertIn(str(base / ".git/objects"), write_paths)
            self.assertNotIn(str(base / ".git/refs/heads"), write_paths)
            self.assertNotIn(str(base / ".git/refs/heads/main"), write_paths)
            self.assertFalse(
                any(path.startswith(str(base / ".git/refs/heads/"))
                    for path in write_paths)
            )
            # This reviewer must not use the issue branch's namespace.
            self.assertEqual(
                git("rev-parse", "--abbrev-ref", "HEAD", cwd=linked), "HEAD"
            )

    def test_detached_reviewer_malformed_head_denied(self) -> None:
        with linked_fixture(detached=True) as (_base, linked, _):
            access = self.policy.resolve_git_worktree_access(linked)
            (access.git_dir / "HEAD").write_text("something-not-a-commit\n")
            with self.assertRaises(self.error_type):
                self.rules(linked)

    def test_main_repository_and_legacy_branch_denied(self) -> None:
        with linked_fixture() as (base, linked, _):
            with self.assertRaises(self.error_type):
                self.rules(base)
            git("checkout", "-q", "-b", "legacy-ref", cwd=linked)
            with self.assertRaises(self.error_type):
                self.rules(linked)


if __name__ == "__main__":
    unittest.main()
