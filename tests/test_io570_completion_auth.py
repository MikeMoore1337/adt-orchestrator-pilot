"""Original 0.10.0 scoped callback token environment compatibility contracts."""
from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = os.environ.get("IO570_PATCHED_ORCHESTRATOR_SOURCE")
OPT_IN = "ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY"
ORIGINAL = "ISSUE_ORCHESTRATOR_AGENT_CALLBACK_TOKEN"
ALIAS = "ISSUE_ORCHESTRATOR_AGENT_CALLBACK_BEARER"


@unittest.skipUnless(SOURCE, "Requires exact pinned original-engine CI checkout")
class ScopedCallbackHandoffTests(unittest.TestCase):
    def test_default_is_no_change(self) -> None:
        from issue_orchestrator.control.session_env import (
            _io570_scoped_callback_bearer_export,
        )
        from issue_orchestrator.entrypoints.cli_tools.agent_callback import (
            api_request_headers,
        )
        with patch.dict(os.environ, {
            OPT_IN: "", ORIGINAL: "", ALIAS: "IO570_FAKE_ALIAS"
        }, clear=True):
            self.assertEqual(_io570_scoped_callback_bearer_export(), "")
            headers = api_request_headers().to_mutable_mapping()
            self.assertNotIn("Authorization", headers)

    def test_synthetic_alias_is_symbolic_only_and_survives_strict_name_filter(self) -> None:
        from issue_orchestrator.control.session_env import (
            _io570_scoped_callback_bearer_export,
        )
        with patch.dict(os.environ, {
            OPT_IN: "1", ORIGINAL: "IO570_TEST_VALUE", ALIAS: ""
        }, clear=True):
            export = _io570_scoped_callback_bearer_export()
        self.assertIn(ALIAS + "=", export)
        self.assertIn("$" + "{" + ORIGINAL + ":?", export)
        self.assertNotIn("IO570_TEST_VALUE", export)
        self.assertTrue(all(token not in ALIAS.upper() for token in ("KEY", "SECRET", "TOKEN")))
        self.assertIn("TOKEN", ORIGINAL)

    def test_filtered_original_uses_only_scoped_alias_for_authorization(self) -> None:
        from issue_orchestrator.entrypoints.cli_tools.agent_callback import (
            api_request_headers,
        )
        with patch.dict(os.environ, {
            OPT_IN: "1", ORIGINAL: "", ALIAS: "IO570_SYNTHETIC_BEARER"
        }, clear=True):
            headers = api_request_headers().to_mutable_mapping()
            self.assertEqual(
                headers["Authorization"], "Bearer IO570_SYNTHETIC_BEARER"
            )

    def test_conflicting_bearer_fails_closed(self) -> None:
        from issue_orchestrator.entrypoints.cli_tools.agent_callback import (
            api_request_headers,
        )
        with patch.dict(os.environ, {
            OPT_IN: "1", ORIGINAL: "A", ALIAS: "B"
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "conflicting scoped"):
                api_request_headers()

    def test_unmodified_original_token_still_works(self) -> None:
        from issue_orchestrator.entrypoints.cli_tools.agent_callback import (
            api_request_headers,
        )
        with patch.dict(os.environ, {
            OPT_IN: "", ORIGINAL: "IO570_TEST_PRIMARY", ALIAS: ""
        }, clear=True):
            headers = api_request_headers().to_mutable_mapping()
            self.assertEqual(headers["Authorization"], "Bearer IO570_TEST_PRIMARY")

    def test_scoped_alias_does_not_disable_default_credential_filter(self) -> None:
        source = (
            Path(SOURCE)
            / "src/issue_orchestrator/execution/agent_runner_providers/sandbox.py"
        ).read_text(encoding="utf-8")
        self.assertIn("shell_environment_policy.ignore_default_excludes=false", source)
        self.assertNotIn("shell_environment_policy.ignore_default_excludes=true", source)
        env = {ORIGINAL: "test1", ALIAS: "test2", "OPENAI_API_KEY": "test3"}
        filtered = {
            k: v for k, v in env.items()
            if not any(p in k.upper() for p in ("KEY", "SECRET", "TOKEN"))
        }
        self.assertEqual(filtered, {ALIAS: "test2"})

    def test_synthetic_transport_probe_never_uses_model_or_real_credentials(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "scripts/probe_io570_completion_transport.py").read_text()
        compile(source, "probe_io570_completion_transport.py", "exec")
        self.assertIn("IO570_COMPLETION_TRANSPORT_GATE=PASS", source)
        self.assertIn("REAL_CODING_DONE_TRANSPORT=PASS", source)
        self.assertIn("MISSING_BEARER_DENY=PASS", source)
        self.assertIn("submit_completion_file", source)
        self.assertIn("ThreadingHTTPServer", source)
        self.assertIn("os.environ.copy()", source)
        self.assertNotIn("codex exec", source.lower())
        self.assertNotIn("gh api", source)
        self.assertNotIn("github.com", source)
        self.assertNotIn("danger-full-access", source)


if __name__ == "__main__":
    unittest.main()
