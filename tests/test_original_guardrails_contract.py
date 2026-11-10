"""Offline guards for original Issue-Orchestrator #570 pilot artifacts.

These checks validate only files, checksums and configuration. They do not
launch a model, exercise a live GitHub sandbox, or verify an E2E queue.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Original issue-orchestrator v0.10.0 at SHA
# d4a79824ccd806089cf3f70ec632d39b8ee255ea.
PINNED_GIT_BLOBS = {
    ".codex/rules/orchestrator.rules": "c47a487f60ddeabb090c92f561660fb2ff5517d2",
    ".codex/hooks/block-no-verify.sh": "794a568218960ec7b6d3909d520fa9aaa594fff9",
    ".codex/hooks/block_no_verify.py": "35a0fd4cecf4661100b1143a6e9f19a5e6c0e8a7",
    "third_party/issue-orchestrator/LICENSE": "d645695673349e3947e8e5ae42332d0ac3164cd7",
    "third_party/issue-orchestrator/NOTICE": "dce54e1d0a5959c6617341f6a2f4ee743cb18fb6",
}

MANAGED_SCRIPT_PATHS = (
    ".codex/hooks/block-no-verify.sh",
    ".codex/hooks/block_no_verify.py",
    ".githooks/pre-push",
    "scripts/agent-hooks/block_no_verify.py",
    "scripts/verify-pr.sh",
)


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\\0".encode().replace(b"\\0", b"\x00")
    return hashlib.sha1(header + content).hexdigest()


class OriginalGuardrailContracts(unittest.TestCase):
    def test_original_files_have_exact_upstream_git_blob_ids(self) -> None:
        for relpath, expected in PINNED_GIT_BLOBS.items():
            with self.subTest(path=relpath):
                self.assertEqual(
                    git_blob_sha((ROOT / relpath).read_bytes()), expected
                )

    def test_helper_contains_exact_upstream_shared_policy(self) -> None:
        helper = (ROOT / "scripts/agent-hooks/block_no_verify.py").read_text(
            encoding="utf-8"
        )
        shared_policy = (ROOT / ".codex/hooks/block_no_verify.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            helper,
            "#!/usr/bin/env python3\n"
            "# Managed by issue-orchestrator setup-guardrails: "
            "block-no-verify helper\n\n" + shared_policy,
        )

    def test_codex_hook_is_synchronous_and_bash_scoped(self) -> None:
        config = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        pretool = config.get("hooks", {}).get("PreToolUse", [])
        configured = [
            entry
            for entry in pretool
            if entry.get("matcher") == "Bash"
            and any(
                h.get("type") == "command"
                and "block-no-verify.sh" in h.get("command", "")
                and not h.get("async", False)
                for h in entry.get("hooks", [])
            )
        ]
        self.assertEqual(len(configured), 1)

    def test_pre_push_guard_preserves_portable_fail_closed_validation(self) -> None:
        script = (ROOT / "scripts/verify-pr.sh").read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", script)
        self.assertIn(
            "issue-orchestrator-selection: modes/upstream-pilot/main.yaml",
            script,
        )
        self.assertIn("PYTHON_ENV_NAME=ISSUE_ORCHESTRATOR_PYTHON", script)
        self.assertIn('if ! "$PYTHON_BIN" -c "import issue_orchestrator"', script)
        self.assertIn(
            '"$PYTHON_BIN" -m '
            "issue_orchestrator.entrypoints.cli_tools.prepush_check -v",
            script,
        )
        self.assertNotIn(
            "elif [ -x /",
            script,
            "Host-specific absolute Python fallback must not be committed",
        )
        prepush = (ROOT / ".githooks/pre-push").read_text(encoding="utf-8")
        self.assertIn('VERIFY_SCRIPT="$REPO_ROOT/scripts/verify-pr.sh"', prepush)
        self.assertIn('LOG_FILE="$HOOK_DIR/pre-push.log"', prepush)
        self.assertIn('run_verify_pr "$@"', prepush)
        self.assertNotIn("git push --no-verify", prepush)

    def test_managed_scripts_are_executable_and_bash_parses(self) -> None:
        for relpath in MANAGED_SCRIPT_PATHS:
            with self.subTest(path=relpath):
                self.assertTrue(
                    (ROOT / relpath).stat().st_mode & stat.S_IXUSR,
                    f"{relpath} must have executable permission in git",
                )
        for relpath in (".codex/hooks/block-no-verify.sh", ".githooks/pre-push",
                        "scripts/verify-pr.sh"):
            with self.subTest(bash=relpath):
                result = subprocess.run(
                    ["bash", "-n", str(ROOT / relpath)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_target_and_disabled_runtime_are_declared(self) -> None:
        config = (
            ROOT / ".issue-orchestrator/config/modes/upstream-pilot/main.yaml"
        ).read_text(encoding="utf-8")
        scope = json.loads(
            (ROOT / ".issue-orchestrator/io570-scope.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            scope["target"]["repository"], "MikeMoore1337/adt-orchestrator-pilot"
        )
        self.assertEqual(scope["target"]["issues"], [7, 8])
        self.assertFalse(scope["constraints"]["allowed_runtime"])
        self.assertTrue(scope["constraints"]["host_cli_authenticated"])
        self.assertFalse(scope["constraints"]["immutable_issue_scope_enforced"])
        self.assertIn("max_concurrent_sessions: 1", config)
        self.assertNotIn("  issue: 7", config)
        self.assertNotIn("  issue: 8", config)
        self.assertIn("  max_to_start: 2", config)
        self.assertIn("    max_concurrent_sessions: 1", config)
        self.assertIn('  label: "adt-io570-pilot-20261109"', config)
        self.assertIn("  seed_ref: origin/main", config)
        probe = ROOT / "scripts/probe_linked_codex_sandbox.py"
        compile(probe.read_text(encoding="utf-8"), str(probe), "exec")
        guarded = ROOT / "scripts/start_guarded_pilot.sh"
        shell = subprocess.run(
            ["bash", "-n", str(guarded)], capture_output=True, text=True
        )
        self.assertEqual(shell.returncode, 0, shell.stderr)
        wrapper = guarded.read_text(encoding="utf-8")
        self.assertIn("scripts/probe_linked_codex_sandbox.py", wrapper)
        self.assertIn("exec issue-orchestrator", wrapper)
        self.assertNotIn("danger-full-access", wrapper)
        self.assertNotIn("bypassPermissions", wrapper)
        self.assertIn("  seed_ref: origin/main", config)
        self.assertNotIn("  seed_ref: HEAD", config)
        self.assertIn("  enabled: false", config)
        self.assertIn("adt-io570-pilot-20261109", config)


if __name__ == "__main__":
    unittest.main()
