#!/usr/bin/env python3
"""Apply the minimal Git-ref namespace patch to exact original Issue-Orchestrator source.

This is a source patch, not a new supervisor. Never modifies a checkout without
an explicit --apply and exact Git commit/blob identity. No credentials or API.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PIN = "d4a79824ccd806089cf3f70ec632d39b8ee255ea"
PATCH = "upstream/issue-orchestrator-0.10.0-isolated-git-refs.patch"
BLOBS = {
    "src/issue_orchestrator/execution/agent_runner_providers/git_worktree_access.py":
        "fc8b8bd42ac4f59bdc47d7e4b4b027594fa72f0e",
    "src/issue_orchestrator/adapters/worktree/_worktree.py":
        "987d5acfb62f5968bf04cd7b3bbf3d47ee11030f",
    "src/issue_orchestrator/domain/branch_naming.py":
        "a726951162794d4d5757df3421497a4f536e3d27",
}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, check=False, timeout=20,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_source_checkout", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    upstream = args.original_source_checkout.expanduser().resolve(strict=True)
    patch = Path(__file__).resolve().parents[1] / PATCH
    assert patch.is_file(), "Patch not present"

    if git(upstream, "rev-parse", "HEAD").stdout.strip() != PIN:
        raise SystemExit("STOP: Issue-Orchestrator is not at the pinned upstream source SHA")
    dirty = git(upstream, "status", "--porcelain=v1", "--untracked-files=no")
    if dirty.returncode or dirty.stdout.strip():
        raise SystemExit("STOP: checkout has tracked changes; preserve existing work")
    for path, blob in BLOBS.items():
        result = git(upstream, "hash-object", path)
        if result.returncode or result.stdout.strip() != blob:
            raise SystemExit(f"STOP: upstream source blob mismatch: {path}")

    checked = git(upstream, "apply", "--check", str(patch))
    if checked.returncode:
        raise SystemExit("PATCH_APPLICABILITY=FAIL\n" + checked.stderr[:1400])
    print("ORIGINAL_ENGINE_PIN=PASS")
    print("ISOLATED_REF_PATCH_APPLICABILITY=PASS")

    if args.apply:
        applied = git(upstream, "apply", str(patch))
        if applied.returncode:
            raise SystemExit("PATCH_APPLY=FAIL\n" + applied.stderr[:1400])
        actual = git(upstream, "diff", "--name-only")
        if set(actual.stdout.splitlines()) != set(BLOBS):
            raise SystemExit("STOP: unexpected patched files")
        print("ORIGINAL_ENGINE_ISOLATED_REF_PATCH=PASS")


if __name__ == "__main__":
    main()
