"""Source-pinned, offline IO570 validation timing journal security contracts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = os.environ.get("IO570_PATCHED_ORCHESTRATOR_SOURCE")
FLAG = "ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, check=True,
        text=True, capture_output=True, timeout=20,
    )


@unittest.skipUnless(SOURCE, "Requires exact pinned original-engine test checkout")
class IO570WorktreePrivateTimingJournal(unittest.TestCase):
    def test_strict_private_linked_worktree_and_default_shared_location(self) -> None:
        from issue_orchestrator.infra.validation_timings import (
            get_shared_timings_file,
            resolve_git_common_dir,
            resolve_git_dir,
        )
        from issue_orchestrator.infra.jsonl_storage import append_jsonl

        with tempfile.TemporaryDirectory(prefix="io570-private-timing-") as temp:
            base, linked = Path(temp) / "base", Path(temp) / "linked"
            git("init", "-q", "-b", "main", str(base), cwd=Path(temp))
            (base / "README.md").write_text("synthetic\n", encoding="utf-8")
            git("add", "README.md", cwd=base)
            git(
                "-c", "user.name=CI",
                "-c", "user.email=ci@example.invalid",
                "commit", "-qm", "baseline", cwd=base,
            )
            git(
                "worktree", "add", "-q", "-b", "7-io570-timing/agent",
                str(linked), "HEAD", cwd=base,
            )
            git_dir = resolve_git_dir(linked)
            common_dir = resolve_git_common_dir(linked)
            self.assertIsNotNone(git_dir)
            self.assertIsNotNone(common_dir)
            self.assertNotEqual(git_dir, common_dir)
            shared = common_dir / "issue-orchestrator/validate-timings.jsonl"
            private = git_dir / "issue-orchestrator/validate-timings.jsonl"

            with patch.dict(os.environ, {FLAG: ""}):
                self.assertEqual(get_shared_timings_file(linked), shared)
            with patch.dict(os.environ, {FLAG: "1"}):
                self.assertEqual(get_shared_timings_file(linked), private)
                # A real JSONL append, using the same OS and storage API
                # as the mandatory original prepush/publish validation.
                append_jsonl(
                    get_shared_timings_file(linked),
                    {"kind": "synthetic", "exit_code": 0},
                )
                self.assertEqual(
                    [json.loads(line) for line in private.read_text().splitlines()],
                    [{"kind": "synthetic", "exit_code": 0}],
                )
                self.assertFalse(shared.exists())
                # Non-linked main retains the upstream common Git path.
                self.assertEqual(get_shared_timings_file(base), shared)

    def test_malformed_external_admin_pointer_fails_closed(self) -> None:
        from issue_orchestrator.infra.validation_timings import get_shared_timings_file

        with tempfile.TemporaryDirectory(prefix="io570-invalid-git-admin-") as temp:
            root = Path(temp)
            base = root / "base"
            linked = root / "linked"
            outsider = root / "outside-admin"
            outsider.mkdir()
            git("init", "-q", "-b", "main", str(base), cwd=root)
            (base / "README").write_text("synthetic\n")
            git("add", "README", cwd=base)
            git(
                "-c", "user.name=CI", "-c", "user.email=ci@example.invalid",
                "commit", "-qm", "baseline", cwd=base,
            )
            git(
                "worktree", "add", "-q", "-b", "7-io570-escape/agent",
                str(linked), "HEAD", cwd=base,
            )
            marker = linked / ".git"
            original_pointer = marker.read_text()
            (outsider / "commondir").write_text(str(base / ".git"))
            try:
                marker.write_text(f"gitdir: {outsider}\n")
                with patch.dict(os.environ, {FLAG: "1"}):
                    with self.assertRaises(RuntimeError):
                        get_shared_timings_file(linked)
            finally:
                marker.write_text(original_pointer)

    def test_probe_and_original_source_patch_are_source_only(self) -> None:
        root = Path(__file__).resolve().parents[1]
        probe = (root / "scripts/probe_namespaced_codex_sandbox.py").read_text()
        source_patch = (
            root / "upstream/issue-orchestrator-0.10.0-io570-validation-timings.patch"
        ).read_text()
        self.assertIn("VALIDATION_TIMINGS_WRITE=PASS", probe)
        self.assertIn("VALIDATION_TIMINGS_WRITE=", probe)
        self.assertIn("not shared_timings.exists()", probe)
        self.assertIn("get_shared_timings_file", source_patch)
        self.assertIn("private Git worktree", source_patch)
        self.assertNotIn("danger-full-access", source_patch)
        self.assertNotIn("git push --no-verify", probe)
        self.assertNotIn("codex exec", probe.lower().replace("does not run codex exec", ""))


if __name__ == "__main__":
    unittest.main()
