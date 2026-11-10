#!/usr/bin/env python3
"""Install a CI-attested Codex CLI 0.167.0 patch in a private, separate directory.

No network calls, sudo, model execution, or mutation of the original release.
Requires the GitHub Actions artifact of the pinned, source-built Codex fix.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SOURCE_SHA = "086ccc833bc9cf01024ad2dd6af7dbd421b6bf9a"
VERSION = "codex-cli 0.167.0"
DIST = Path.home() / ".local/share/adt-io570"
UNMODIFIED = DIST / "codex-0.167.0"
PATCHED = DIST / "codex-0.167.0-io570-patched"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _provenance(directory: Path) -> str:
    metadata = (directory / "BUILD_PROVENANCE.txt").read_text(encoding="utf-8")
    if (
        f"OFFICIAL_CODEX_SOURCE_SHA={SOURCE_SHA}" not in metadata.splitlines()
        or "PATCHED_SANDBOX=regular-file-metadata-masks-only" not in metadata.splitlines()
    ):
        raise ValueError("Missing original release source or patch provenance")
    checksums = (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    if len(checksums) != 1:
        raise ValueError("Expected exactly one Codex SHA256SUMS line")
    match = re.fullmatch(r"([a-f0-9]{64})  bin/codex", checksums[0])
    if match is None:
        raise ValueError("Malformed Codex SHA256SUMS artifact")
    return match.group(1)


def attest(directory: Path = PATCHED) -> Path:
    directory = directory.expanduser().resolve(strict=True)
    if directory != PATCHED.resolve(strict=True):
        raise ValueError("Codex binary must live in the dedicated patched directory")
    expected = _provenance(directory)
    binary = directory / "bin/codex"
    if not binary.is_file() or binary.is_symlink():
        raise ValueError("Patched Codex binary missing or linked to external file")
    if _sha256(binary) != expected:
        raise ValueError("Patched Codex SHA-256 mismatch")
    if not os.access(binary, os.X_OK):
        raise ValueError("Patched Codex must be executable")
    version = subprocess.check_output(
        [str(binary), "--version"], text=True, timeout=15
    ).strip()
    if version != VERSION:
        raise ValueError(f"Codex version mismatch: {version!r}")
    return binary


def install(artifact: Path) -> Path:
    artifact = artifact.expanduser().resolve(strict=True)
    expected = _provenance(artifact)
    build_binary = artifact / "bin/codex"
    if not build_binary.is_file() or build_binary.is_symlink():
        raise ValueError("Build artifact must contain a regular Codex binary")
    if _sha256(build_binary) != expected:
        raise ValueError("Artifact SHA-256 verification failed")
    if not UNMODIFIED.is_dir() or PATCHED.exists() or PATCHED.is_symlink():
        raise ValueError("Original isolated release missing or patched destination exists")
    if not DIST.is_dir() or DIST.is_symlink() or DIST.stat().st_mode & 0o077:
        raise ValueError("Codex installation parent must be private (0700)")
    original_binary = (UNMODIFIED / "bin/codex").resolve(strict=True)
    if not original_binary.is_relative_to(UNMODIFIED.resolve()):
        raise ValueError("Original Codex binary points outside isolated release")
    original_sha = _sha256(original_binary)

    with tempfile.TemporaryDirectory(prefix=".io570-install-", dir=DIST) as tmp:
        staged = Path(tmp) / "release"
        shutil.copytree(UNMODIFIED, staged, symlinks=True)
        target = staged / "bin/codex"
        if target.is_symlink() or not target.is_file():
            raise ValueError("Invalid destination binary")
        shutil.copy2(build_binary, target)
        target.chmod(target.stat().st_mode | 0o100)
        shutil.copy2(artifact / "SHA256SUMS", staged / "SHA256SUMS")
        shutil.copy2(artifact / "BUILD_PROVENANCE.txt", staged / "BUILD_PROVENANCE.txt")
        if _sha256(target) != expected:
            raise ValueError("Installed binary failed SHA-256 verification")
        target_version = subprocess.check_output(
            [str(target), "--version"], text=True, timeout=15
        ).strip()
        if target_version != VERSION:
            raise ValueError("Built Codex binary has unexpected version")
        staged.rename(PATCHED)

    if _sha256(original_binary) != original_sha:
        raise ValueError("Original Codex binary was modified")
    return attest(PATCHED)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_directory", nargs="?", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        result = attest()
    else:
        if args.artifact_directory is None:
            parser.error("artifact_directory is required unless --verify-only")
        result = install(args.artifact_directory)
    print("PATCHED_CODEX_ARTIFACT_SHA256=PASS")
    print("PATCHED_CODEX_INSTALL=PASS")
    print("ORIGINAL_CODEX_UNMODIFIED=YES")
    print("PATCHED_CODEX_BINARY=" + str(result))


if __name__ == "__main__":
    main()
