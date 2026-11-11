#!/usr/bin/env bash
# Prepare a disposable, separately checked-out PATCHED ORIGINAL engine.
# One source patch; NO second supervisor, daemon, model, git reset or merging.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$HOME/projects/issue-orchestrator"
root="$HOME/.local/state/adt-io570"
target="$root/original-engine-namespaced"
pin="d4a79824ccd806089cf3f70ec632d39b8ee255ea"

[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$pin" ]] ||
  { echo "ENGINE_PIN=FAIL" >&2; exit 1; }
[[ -x "$source_dir/.venv/bin/python" ]] ||
  { echo "ENGINE_VENV=FAIL" >&2; exit 1; }

mkdir -p "$root"
chmod 700 "$root"

if [[ ! -e "$target" ]]; then
  git -C "$source_dir" worktree add --detach "$target" "$pin"
  "$source_dir/.venv/bin/python" "$repo/scripts/apply_orchestrator_git_ref_fix.py" "$target" --apply
fi

[[ "$(git -C "$target" rev-parse HEAD)" == "$pin" ]] ||
  { echo "PATCHED_ENGINE_SOURCE_PIN=FAIL" >&2; exit 1; }
expected="$(printf '%s\n' \
  'src/issue_orchestrator/adapters/worktree/_worktree.py' \
  'src/issue_orchestrator/domain/branch_naming.py' \
  'src/issue_orchestrator/execution/agent_runner_providers/git_worktree_access.py')"
actual="$(git -C "$target" diff --name-only)"
[[ "$actual" == "$expected" ]] ||
  { echo "PATCHED_ENGINE_FILES=UNEXPECTED" >&2; exit 1; }
git -C "$target" diff --check
echo "PATCHED_ENGINE_FILES=PASS"
echo "ORIGINAL_ENGINE_UNMODIFIED=YES"
echo "NAMESPACED_ENGINE_READY_FOR_NO_MODEL_PROBE=YES"
echo "PATCHED_ENGINE_PATH=$target"
