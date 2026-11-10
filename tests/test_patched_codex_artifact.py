"""No-network offline tests for isolated patched Codex artifact installation."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install_patched_codex.py"


class PatchedCodexArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="io570-installer-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        spec = importlib.util.spec_from_file_location("io570_installer_test", INSTALLER)
        assert spec is not None and spec.loader is not None
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.dist = self.root / "private"
        self.dist.mkdir(mode=0o700)
        self.original = self.dist / "codex-0.167.0"
        self.patched = self.dist / "codex-0.167.0-io570-patched"
        self.original.joinpath("bin").mkdir(parents=True)
        self.original.joinpath("bin/codex").write_bytes(
            b"#!/bin/sh\nprintf 'codex-cli 0.167.0\\n'\n"
        )
        self.original.joinpath("bin/codex").chmod(0o700)
        self.original.joinpath("codex-resources").mkdir()
        self.original.joinpath("codex-resources/bwrap").write_text("fixture")
        self.artifact = self.root / "artifact"
        self.artifact.joinpath("bin").mkdir(parents=True)
        self.artifact.joinpath("bin/codex").write_bytes(
            b"#!/bin/sh\nprintf 'codex-cli 0.167.0\\n'\n# patched\n"
        )
        self.artifact.joinpath("bin/codex").chmod(0o700)
        digest = hashlib.sha256(
            self.artifact.joinpath("bin/codex").read_bytes()
        ).hexdigest()
        self.artifact.joinpath("SHA256SUMS").write_text(
            f"{digest}  bin/codex\n", encoding="utf-8"
        )
        self.artifact.joinpath("BUILD_PROVENANCE.txt").write_text(
            f"OFFICIAL_CODEX_SOURCE_SHA={self.module.SOURCE_SHA}\n"
            "PATCHED_SANDBOX=regular-file-metadata-masks-only\n",
            encoding="utf-8",
        )
        self.patches = [
            mock.patch.object(self.module, "DIST", self.dist),
            mock.patch.object(self.module, "UNMODIFIED", self.original),
            mock.patch.object(self.module, "PATCHED", self.patched),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_installs_without_modifying_original_release(self) -> None:
        before = self.original.joinpath("bin/codex").read_bytes()
        installed = self.module.install(self.artifact)
        self.assertEqual(installed, self.patched.joinpath("bin/codex"))
        self.assertEqual(self.original.joinpath("bin/codex").read_bytes(), before)
        self.assertEqual(
            self.patched.joinpath("codex-resources/bwrap").read_text(), "fixture"
        )
        self.assertEqual(self.module.attest(self.patched), installed)
        with self.assertRaises(ValueError):
            self.module.install(self.artifact)

    def test_rejects_modified_binary_before_creating_destination(self) -> None:
        self.artifact.joinpath("bin/codex").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.module.install(self.artifact)
        self.assertFalse(self.patched.exists())

    def test_rejects_invalid_source_provenance(self) -> None:
        self.artifact.joinpath("BUILD_PROVENANCE.txt").write_text(
            "OFFICIAL_CODEX_SOURCE_SHA=unrecognized\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "provenance"):
            self.module.install(self.artifact)
        self.assertFalse(self.patched.exists())


if __name__ == "__main__":
    unittest.main()
