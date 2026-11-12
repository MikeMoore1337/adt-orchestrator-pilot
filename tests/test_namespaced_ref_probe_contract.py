"""Offline contracts for original Codex + original engine namespaced Git ref probe."""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NamespacedProbeContracts(unittest.TestCase):
    def test_probe_remains_no_model_and_uses_original_binary(self) -> None:
        path = ROOT / "scripts/probe_namespaced_codex_sandbox.py"
        code = path.read_text(encoding="utf-8")
        compile(code, str(path), "exec")
        self.assertIn("ORIGINAL_CODEX_UNMODIFIED=YES", code)
        self.assertIn("NAMESPACED_REF_WRITE=PASS", code)
        self.assertIn("VALIDATION_TIMINGS_WRITE=PASS", code)
        self.assertIn("EXACT_GIT_FILE_WRITE_RULES=0", code)
        self.assertIn("MAIN_REF_DENY=", code)
        self.assertIn("GH_CANARY_DENY=", code)
        self.assertIn("OUTSIDE_WRITE_DENY=", code)
        self.assertNotIn("codex exec", code.replace("Does not run codex exec", ""))
        self.assertNotIn("danger-full-access", code)
        self.assertNotIn("bypassPermissions", code)

    def test_prepare_engine_script_is_source_only_and_bash_valid(self) -> None:
        path = ROOT / "scripts/prepare_namespaced_original_engine.sh"
        result = subprocess.run(
            ["bash", "-n", str(path)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        content = path.read_text(encoding="utf-8")
        self.assertIn("scripts/apply_orchestrator_git_ref_fix.py", content)
        self.assertIn("worktree add --detach", content)
        self.assertIn("original-engine-namespaced", content)
        self.assertNotIn("issue-orchestrator start", content)
        self.assertNotIn("git reset --hard", content)
        self.assertNotIn("rm -rf", content)


if __name__ == "__main__":
    unittest.main()
