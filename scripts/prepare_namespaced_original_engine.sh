#!/usr/bin/env bash
# Prepare a disposable, separately checked-out PATCHED ORIGINAL engine.
# One source patch; NO second supervisor, daemon, model, git reset or merging.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$HOME/projects/issue-orchestrator"
root="$HOME/.local/state/adt-io570"
target="$root/original-engine-namespaced-callback"
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
  sandbox="src/issue_orchestrator/execution/agent_runner_providers/sandbox.py"
  [[ "$(git -C "$target" hash-object "$sandbox")" == "fca26cf3e6e88b984e2758005f3ce9e5019838ab" ]] ||
    { echo "CODEX_SANDBOX_SOURCE_PIN=FAIL" >&2; exit 1; }
  git -C "$target" apply --check "$repo/upstream/issue-orchestrator-0.10.0-io570-loopback-proxy.patch"
  git -C "$target" apply "$repo/upstream/issue-orchestrator-0.10.0-io570-loopback-proxy.patch"
  timings="src/issue_orchestrator/infra/validation_timings.py"
  [[ "$(git -C "$target" hash-object "$timings")" == "45c63ee3269ea343f297f07a62b0fb25164448d8" ]] ||
    { echo "VALIDATION_TIMINGS_SOURCE_PIN=FAIL" >&2; exit 1; }
  git -C "$target" apply --check "$repo/upstream/issue-orchestrator-0.10.0-io570-validation-timings.patch"
  git -C "$target" apply "$repo/upstream/issue-orchestrator-0.10.0-io570-validation-timings.patch"
  session_env="src/issue_orchestrator/control/session_env.py"
  callback="src/issue_orchestrator/entrypoints/cli_tools/agent_callback.py"
  [[ "$(git -C "$target" hash-object "$session_env")" == "041d27bc3947a66095a03b9aa7e6dbc3d0787538" ]] ||
    { echo "SESSION_ENV_SOURCE_PIN=FAIL" >&2; exit 1; }
  [[ "$(git -C "$target" hash-object "$callback")" == "36948fc6865db372da8712a1c421dd350e92ddcf" ]] ||
    { echo "AGENT_CALLBACK_SOURCE_PIN=FAIL" >&2; exit 1; }
  git -C "$target" apply --check "$repo/upstream/issue-orchestrator-0.10.0-io570-callback-env.patch"
  git -C "$target" apply "$repo/upstream/issue-orchestrator-0.10.0-io570-callback-env.patch"
fi

[[ "$(git -C "$target" rev-parse HEAD)" == "$pin" ]] ||
  { echo "PATCHED_ENGINE_SOURCE_PIN=FAIL" >&2; exit 1; }
expected="$(printf '%s\n' \
  'src/issue_orchestrator/adapters/worktree/_worktree.py' \
  'src/issue_orchestrator/control/session_env.py' \
  'src/issue_orchestrator/domain/branch_naming.py' \
  'src/issue_orchestrator/entrypoints/cli_tools/agent_callback.py' \
  'src/issue_orchestrator/execution/agent_runner_providers/git_worktree_access.py' \
  'src/issue_orchestrator/execution/agent_runner_providers/sandbox.py' \
  'src/issue_orchestrator/infra/validation_timings.py')"
actual="$(git -C "$target" diff --name-only)"
[[ "$actual" == "$expected" ]] ||
  { echo "PATCHED_ENGINE_FILES=UNEXPECTED" >&2; exit 1; }
git -C "$target" diff --check
echo "PATCHED_ENGINE_FILES=PASS"
echo "ORIGINAL_ENGINE_UNMODIFIED=YES"
echo "NAMESPACED_ENGINE_READY_FOR_NO_MODEL_PROBE=YES"
echo "PATCHED_ENGINE_PATH=$target"
