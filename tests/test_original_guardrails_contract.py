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
        self.assertIn("    session_timeout_minutes: 20", config)
        self.assertIn("    timeout_minutes: 15", config)
        self.assertIn("    timeout_minutes: 10", config)
        self.assertIn('  label: "adt-io570-pilot-20261109"', config)
        self.assertIn("  seed_ref: origin/main", config)
        probe = ROOT / "scripts/probe_namespaced_codex_sandbox.py"
        compile(probe.read_text(encoding="utf-8"), str(probe), "exec")
        patcher = ROOT / "scripts/apply_orchestrator_git_ref_fix.py"
        compile(patcher.read_text(encoding="utf-8"), str(patcher), "exec")
        patch = (ROOT / "upstream/issue-orchestrator-0.10.0-isolated-git-refs.patch").read_text(encoding="utf-8")
        self.assertIn("ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS", patch)
        self.assertIn("_isolated_branch_directory_rules", patch)
        self.assertNotIn("danger-full-access", patch)

        guarded = ROOT / "scripts/start_guarded_pilot.sh"
        shell = subprocess.run(
            ["bash", "-n", str(guarded)], capture_output=True, text=True
        )
        self.assertEqual(shell.returncode, 0, shell.stderr)
        wrapper = guarded.read_text(encoding="utf-8")
        self.assertIn("scripts/probe_namespaced_codex_sandbox.py", wrapper)
        self.assertIn("ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS=1", wrapper)
        self.assertIn("ORIGINAL_ENGINE_NAMESPACED_SOURCE=PASS", wrapper)
        self.assertIn("exec issue-orchestrator", wrapper)
        self.assertNotIn("danger-full-access", wrapper)
        self.assertNotIn("bypassPermissions", wrapper)
        self.assertIn("  seed_ref: origin/main", config)
        self.assertNotIn("  seed_ref: HEAD", config)
        self.assertIn("  enabled: false", config)
        self.assertIn("adt-io570-pilot-20261109", config)

    def test_launch_config_gate_is_real_python_and_fail_closed(self) -> None:
        wrapper = (ROOT / "scripts/start_guarded_pilot.sh").read_text(
            encoding="utf-8"
        )
        marker = 'if ! "$ISSUE_ORCHESTRATOR_PYTHON" - "$CONFIG" <<\'PY\'\n'
        self.assertEqual(wrapper.count(marker), 1)
        terminator = '\nPY\nthen\n  fail "Original queue configuration failed validation"\nfi\n'
        self.assertEqual(wrapper.count(terminator), 1)
        python_source = wrapper.split(marker, 1)[1].split(terminator, 1)[0]
        compile(python_source, "pilot-launch-config.py", "exec")
        self.assertIn('"repository": config.repo == "MikeMoore1337/adt-orchestrator-pilot"', python_source)
        self.assertIn('"codex_one_shot": config.agents["agent:dev"].provider_args.get("execution_mode") == "exec"', python_source)
        self.assertIn("config.retry.interrupted_sessions.enabled is False", python_source)
        self.assertIn('raise SystemExit("SEQUENTIAL_QUEUE_CONFIG=FAIL:', python_source)
        self.assertNotIn("\nassert ", python_source)

    def test_pilot_uses_bounded_one_shot_coding_and_no_auto_retry(self) -> None:
        config = (
            ROOT / ".issue-orchestrator/config/modes/upstream-pilot/main.yaml"
        ).read_text(encoding="utf-8")
        self.assertEqual(config.count("      execution_mode: exec"), 1)
        self.assertIn("  interrupted_sessions:\n    enabled: false", config)
        wrapper = (ROOT / "scripts/start_guarded_pilot.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('"$GH7" == *"io:auto-retried-interrupted-coding"*', wrapper)
        self.assertIn('if [[ "$GH7" == *"needs-human"* ]]; then', wrapper)
        self.assertIn("preserve the backed-up commit", wrapper)

    def test_agent_instructions_are_scoped_to_authorized_guarded_pilot(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("SCOPED LIVE PILOT", text)
        self.assertIn("scripts/start_guarded_pilot.sh", text)
        self.assertIn("original engine", text)
        self.assertIn("origin/main", text)
        self.assertNotIn("ENGINE NOT ACTIVATED", text)
        self.assertNotIn("SOURCE-ONLY PREPARATION", text)


if __name__ == "__main__":
    unittest.main()
