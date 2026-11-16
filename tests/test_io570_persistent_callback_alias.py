"""Scoped *review exchange* callback handoff; tests are entirely no-model."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = os.environ.get("IO570_PATCHED_ORCHESTRATOR_SOURCE")
OPT_IN = "ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY"
ORIGINAL = "ISSUE_ORCHESTRATOR_AGENT_CALLBACK_TOKEN"
ALIAS = "ISSUE_ORCHESTRATOR_AGENT_CALLBACK_BEARER"


@unittest.skipUnless(SOURCE, "Requires patched original engine for host CI")
class PersistentReviewCallbackTests(unittest.TestCase):
    def env_for(self, role):
        from issue_orchestrator.execution.persistent_session_exchange import _build_role_env

        with patch("issue_orchestrator.control.isolation.build_agent_tool_env", return_value={}):
            return _build_role_env(
                role=role,
                response_file=Path("/tmp/io570-synthetic-review.json"),
                review_report_file=None,
                completion_path=Path("/tmp/io570-synthetic-completion.json"),
                validation_output_dir=Path("/tmp/io570-synthetic-validation"),
                worktree=Path("/tmp/io570-synthetic-worktree"),
                runtime_config=SimpleNamespace(to_env=lambda: {}),
                agent_label="agent:" + role,
                web_port=18887,
                issue_number=20,
                session_name="io570-synthetic",
                completion_capability="io570-synthetic-capability",
            )

    def test_both_roles_inherit_scoped_alias_without_admin_token(self):
        for role in ("coder", "reviewer"):
            with self.subTest(role=role), patch.dict(os.environ, {
                OPT_IN: "1", ORIGINAL: "IO570_SYNTHETIC_CALLBACK",
                "GH_TOKEN": "GH_FORBIDDEN", "ISSUE_ORCHESTRATOR_API_TOKEN": "ADMIN_FORBIDDEN"
            }, clear=True):
                env = self.env_for(role)
            self.assertEqual(env[ALIAS], "IO570_SYNTHETIC_CALLBACK")
            self.assertEqual(env["ORCHESTRATOR_API_PORT"], "18887")
            self.assertNotIn("GH_TOKEN", env)
            self.assertNotIn("ISSUE_ORCHESTRATOR_API_TOKEN", env)

    def test_codex_strict_name_filter_keeps_only_alias_for_http_callback(self):
        from issue_orchestrator.entrypoints.cli_tools.agent_callback import api_request_headers
        with patch.dict(os.environ, {OPT_IN: "1", ORIGINAL: "IO570_SYNTHETIC_CALLBACK"}, clear=True):
            env = self.env_for("coder")
        # Codex drops shell environment variable names containing TOKEN.
        stripped = {k:v for k,v in env.items() if "TOKEN" not in k.upper()}
        with patch.dict(os.environ, stripped, clear=True):
            headers = api_request_headers().to_mutable_mapping()
        self.assertEqual(headers.get("Authorization"), "Bearer IO570_SYNTHETIC_CALLBACK")

    def test_default_non_pilot_behavior_is_unchanged(self):
        with patch.dict(os.environ, {OPT_IN: "", ORIGINAL: "IO570_SYNTHETIC_CALLBACK"}, clear=True):
            env = self.env_for("coder")
        self.assertNotIn(ALIAS, env)

    def test_scoped_mode_without_callback_refuses_launch(self):
        with patch.dict(os.environ, {OPT_IN: "1", ORIGINAL: ""}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "persistent callback token unavailable"):
                self.env_for("coder")

    def test_untrusted_alias_not_accepted_as_host_source(self):
        with patch.dict(os.environ, {OPT_IN: "1", ORIGINAL: "", ALIAS: "ATTACKER_ALIAS"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "persistent callback token unavailable"):
                self.env_for("reviewer")


if __name__ == "__main__":
    unittest.main()
