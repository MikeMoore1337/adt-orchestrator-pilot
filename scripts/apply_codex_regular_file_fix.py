#!/usr/bin/env python3
"""Apply the minimal upstream Codex 0.167.0 Linux regular-file mount fix.

Fails closed unless the checkout is the original immutable release source.
Never writes to the user's installed Codex, credentials or the pilot repo.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PINNED_CODEX_SHA = "086ccc833bc9cf01024ad2dd6af7dbd421b6bf9a"
PATCH_NAME = "patches/codex-rust-v0.167.0-regular-file-bwrap.patch"


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream_codex_repo", type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="Apply the reviewed patch; default is read-only check")
    args = parser.parse_args()
    upstream = args.upstream_codex_repo.resolve(strict=True)
    pilot_root = Path(__file__).resolve().parents[1]
    patch = pilot_root / PATCH_NAME
    current = run(upstream, "rev-parse", "HEAD")
    if current.returncode or current.stdout.strip() != PINNED_CODEX_SHA:
        raise SystemExit("STOP: Codex source is not rust-v0.167.0 exact HEAD")
    dirty = run(upstream, "status", "--porcelain=v1", "--untracked-files=no")
    if dirty.returncode or dirty.stdout.strip():
        raise SystemExit("STOP: upstream Codex has tracked changes; preserve them")

    expected = {
        "codex-rs/linux-sandbox/src/bwrap.rs":
            "11959d0c02248f090a568efd5b53ee1fa0e6ad9c",
        "codex-rs/linux-sandbox/src/bwrap_tests.rs":
            "9f53e2c9e72406e59605bf1a6f7560040b33dfbc",
    }
    for name, oid in expected.items():
        actual = run(upstream, "hash-object", name)
        if actual.returncode or actual.stdout.strip() != oid:
            raise SystemExit(f"STOP: mismatch in original upstream source {name}")

    cmd = ["git", "-C", str(upstream), "apply", "--check", str(patch)]
    checked = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if checked.returncode:
        raise SystemExit("PATCH_APPLICABILITY=FAIL\n" + checked.stderr[:1600])
    print("PINNED_CODEX_SOURCE=PASS")
    print("PATCH_APPLICABILITY=PASS")

    if args.apply:
        applied = subprocess.run(
            ["git", "-C", str(upstream), "apply", str(patch)],
            capture_output=True, text=True, check=False,
        )
        if applied.returncode:
            raise SystemExit("PATCH_APPLY=FAIL\n" + applied.stderr[:1600])
        print("PATCH_APPLY=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
