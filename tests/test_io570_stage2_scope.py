"""Stage-2 preparation gates. Source-only checks; no model or GitHub calls."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
LABEL = "adt-io570-stage2-20261114"


class Stage2ScopeTests(unittest.TestCase):
    def test_stage2_selection_and_wip(self):
        scope = json.loads((ROOT / ".issue-orchestrator/io570-scope.json").read_text())
        self.assertEqual(scope["target"]["issues"], [20, 21])
        self.assertEqual(scope["target"]["label"], LABEL)
        self.assertEqual(scope["target"]["dependency"], "Depends-on: #20")
        self.assertEqual(scope["constraints"]["wip"], 1)
        self.assertFalse(scope["constraints"]["allowed_runtime"])
        self.assertFalse(scope["constraints"]["immutable_issue_scope_enforced"])
        self.assertTrue(scope["constraints"]["separate_owner_activation_required"])

    def test_original_config_and_prompt_scope(self):
        config = (ROOT / ".issue-orchestrator/config/modes/upstream-pilot/main.yaml").read_text()
        self.assertIn(f'label: "{LABEL}"', config)
        self.assertIn("max_concurrent_sessions: 1", config)
        self.assertIn("max_to_start: 2", config)
        self.assertIn("seed_ref: origin/main", config)
        self.assertIn("provider: codex", config)
        self.assertIn("merge_queue:\n  enabled: false", config)
        self.assertIn("tech_lead:\n  enabled: false", config)
        worker = (ROOT / ".issue-orchestrator/prompts/dev.md").read_text()
        self.assertIn("#20", worker)
        self.assertIn("#21", worker)
        self.assertNotIn("assigned Issue #7 or #8", worker)

    def test_guard_refuses_unexpected_open_issue_or_label(self):
        start = (ROOT / "scripts/start_guarded_pilot.sh").read_text()
        self.assertIn("Unexpected open Issue", start)
        self.assertIn("Stage-2 label membership is not exactly Issues #20 and #21", start)
        self.assertIn("Depends-on: #20", start)
        self.assertIn("ISSUE_ORCHESTRATOR_IO570_EXACT_LEASE_PUSH=1", start)
        self.assertIn("IO570_EXACT_LEASE_PUSH=ENABLED_ONLY_FOR_20_21", start)
        self.assertIn("ORIGINAL_ENGINE_START=ORIGINAL_ENGINE_ONLY", start)
        self.assertNotIn("gh issue edit", start)
        self.assertNotIn("git reset --hard", start)
        self.assertNotIn(" --no-verify", start)

    def test_original_patch_integrity_gate(self):
        patched = (ROOT / "scripts/prepare_namespaced_original_engine.sh").read_text()
        gated = (ROOT / "scripts/start_guarded_pilot.sh").read_text()
        ci = (ROOT / ".github/workflows/io570-isolated-git-refs.yml").read_text()
        patchname = "issue-orchestrator-0.10.0-io570-exact-lease-push.patch"
        for body in (patched, gated, ci):
            self.assertIn(patchname, body)
        self.assertIn("apply --reverse --check", gated)
        self.assertIn('git -C "$PATCHED_ENGINE" apply --reverse --check', gated)
        self.assertIn("git_push_operations.py", ci)
        self.assertIn("git_working_copy.py", ci)
        self.assertIn("test_io570_exact_lease_push.py", ci)

    def test_shell_syntax(self):
        for filename in ("scripts/start_guarded_pilot.sh",
                         "scripts/prepare_namespaced_original_engine.sh"):
            with self.subTest(filename=filename):
                result = subprocess.run(["bash", "-n", str(ROOT / filename)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
