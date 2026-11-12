#!/usr/bin/env bash
# One-shot fail-closed launch for the original Issue-Orchestrator.
# No scheduler, daemon, API key, CI bypass, automatic retry, or auto-merge.
set -euo pipefail

fail() {
  printf 'ORIGINAL_ENGINE_START=BLOCKED: %s\n' "$*" >&2
  exit 1
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ "$(git rev-parse --show-toplevel)" == "$ROOT" ]] ||
  fail "Unexpected repository root"
[[ "$(git branch --show-current)" == "main" ]] ||
  fail "Only the protected main checkout may run this pilot"
git diff --quiet && git diff --cached --quiet ||
  fail "Tracked files are dirty; preserve them, do not reset"

export GIT_TERMINAL_PROMPT=0
REMOTE_HEAD="$(timeout 30 git ls-remote --exit-code origin refs/heads/main | cut -f1)"
LOCAL_HEAD="$(git rev-parse HEAD)"
[[ -n "$REMOTE_HEAD" && "$REMOTE_HEAD" == "$LOCAL_HEAD" ]] ||
  fail "Local main differs from the current remote main"

ORIGINAL_ROOT="$HOME/projects/issue-orchestrator"
[[ -x "$ORIGINAL_ROOT/.venv/bin/python" ]] ||
  fail "Original engine Python virtual environment not found"
export ISSUE_ORCHESTRATOR_PYTHON="$ORIGINAL_ROOT/.venv/bin/python"
export PATH="$HOME/.local/share/adt-io570/codex-0.167.0/bin:$ORIGINAL_ROOT/.venv/bin:$PATH"
export ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS=1
PATCHED_ENGINE="$HOME/.local/state/adt-io570/original-engine-namespaced-timings"
[[ "$(git -C "$PATCHED_ENGINE" rev-parse HEAD 2>/dev/null)" == \
  "d4a79824ccd806089cf3f70ec632d39b8ee255ea" ]] ||
  fail "Pinned original engine patch worktree missing or wrong source SHA"
EXPECTED_FILES="$(printf '%s\n' \
  'src/issue_orchestrator/adapters/worktree/_worktree.py' \
  'src/issue_orchestrator/domain/branch_naming.py' \
  'src/issue_orchestrator/execution/agent_runner_providers/git_worktree_access.py' \
  'src/issue_orchestrator/execution/agent_runner_providers/sandbox.py' \
  'src/issue_orchestrator/infra/validation_timings.py')"
[[ "$(git -C "$PATCHED_ENGINE" diff --name-only)" == "$EXPECTED_FILES" ]] ||
  fail "Patched original engine contains unknown or missing source modifications"
git -C "$PATCHED_ENGINE" diff --check ||
  fail "Original engine patch has whitespace errors"
export PYTHONPATH="$PATCHED_ENGINE/src"
echo "ORIGINAL_ENGINE_NAMESPACED_SOURCE=PASS"
export ISSUE_ORCHESTRATOR_CODEX_RUNTIME_ROOT="$HOME/.local/state/adt-io570/codex-runtime"
unset CODEX_HOME
hash -r

[[ -z "${OPENAI_API_KEY:-}" && -z "${CODEX_API_KEY:-}" ]] ||
  fail "Metered API key detected; only ChatGPT login is allowed"
[[ "$(git -C "$ORIGINAL_ROOT" rev-parse HEAD)" == \
  "d4a79824ccd806089cf3f70ec632d39b8ee255ea" ]] ||
  fail "Original Issue-Orchestrator source pin changed"
"$ISSUE_ORCHESTRATOR_PYTHON" -c \
  'import issue_orchestrator; print("ORIGINAL_ENGINE_IMPORT=PASS")' ||
  fail "Original Issue-Orchestrator cannot import"

CODEX_EXECUTABLE="$(command -v codex)"
[[ "$(readlink -f "$CODEX_EXECUTABLE")" == \
  "$HOME/.local/share/adt-io570/codex-0.167.0/bin/codex" ]] ||
  fail "Expected unchanged Codex CLI executable"
codex --version
LOGIN="$(codex login status 2>&1)" ||
  fail "Codex login status failed"
[[ "$LOGIN" == *"Logged in using ChatGPT"* ]] ||
  fail "Codex is not authenticated through ChatGPT"
echo "CODEX_CHATGPT_LOGIN=PASS"

CONFIG=".issue-orchestrator/config/modes/upstream-pilot/main.yaml"
if ! "$ISSUE_ORCHESTRATOR_PYTHON" - "$CONFIG" <<'PY'
import sys
from pathlib import Path
from issue_orchestrator.infra.config import Config
config = Config.load(Path(sys.argv[1]).resolve())
checks = {
    "repository": config.repo == "MikeMoore1337/adt-orchestrator-pilot",
    "seed_ref": config.worktree_seed_ref == "origin/main",
    "wip": config.max_concurrent_sessions == 1,
    "pilot_label": config.filtering.label == "adt-io570-pilot-20261109",
    "no_single_issue_filter": config.filtering.issue is None,
    "two_issue_limit": config.filtering.max_to_start == 2,
    "review_enabled": config.review_enabled,
    "human_merge": not config.merge_queue.enabled,
    "agents_sandboxed": bool(config.agents) and all(a.sandbox for a in config.agents.values()),
    "codex_one_shot": config.agents["agent:dev"].provider_args.get("execution_mode") == "exec",
    "no_interrupted_retries": config.retry.interrupted_sessions.enabled is False,
}
failures = sorted(name for name, valid in checks.items() if not valid)
if failures:
    raise SystemExit("SEQUENTIAL_QUEUE_CONFIG=FAIL: " + ", ".join(failures))
print("SEQUENTIAL_QUEUE_CONFIG=PASS")
PY
then
  fail "Original queue configuration failed validation"
fi

# Owner-controlled synthetic pilot scope only, no unexpected labeled issues.
SELECTED_RAW="$(
  gh issue list --repo MikeMoore1337/adt-orchestrator-pilot \
    --state all --limit 100 --label adt-io570-pilot-20261109 \
    --json number --jq '.[].number' | sort -n
)" || fail "Cannot retrieve exact synthetic pilot label membership"
[[ -n "$SELECTED_RAW" ]] ||
  fail "No pilot-labeled issues"
mapfile -t SELECTED <<< "$SELECTED_RAW"
for issue in "${SELECTED[@]}"; do
  [[ "$issue" == "7" || "$issue" == "8" ]] ||
    fail "Unexpected pilot-labeled Issue #$issue"
done
GH7="$(gh issue view 7 --repo MikeMoore1337/adt-orchestrator-pilot \
  --json state,labels --jq '.state + " " + ([.labels[].name] | join(","))')" ||
  fail "Cannot read #7 status"
if [[ "$GH7" == *"blocked-failed"* ]]; then
  fail "Issue #7 is blocked-failed. Preserve artifacts and fix the sandbox first"
fi
if [[ "$GH7" == *"io:auto-retried-interrupted-coding"* ]]; then
  fail "Issue #7 has an interrupted-session retry marker; inspect the previous run before retrying"
fi
if [[ "$GH7" == *"needs-human"* ]]; then
  fail "Issue #7 is needs-human; preserve the backed-up commit and resolve the human gate before restarting"
fi
GH8_BODY="$(gh issue view 8 --repo MikeMoore1337/adt-orchestrator-pilot \
  --json body --jq '.body')" ||
  fail "Cannot inspect Issue #8 dependency"
grep -q '^Depends-on: #7' <<< "$GH8_BODY" ||
  fail "Issue #8 is missing its original Depends-on: #7 directive"
echo "PILOT_GITHUB_SCOPE=PASS"

# Never inherit a potentially wider caller-supplied opt-in.
[[ -z "${ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY:-}" ]] ||
  fail "Caller supplied an unreviewed loopback proxy override"

# No model invocation. If linked Git sandbox cannot start, fail in seconds.
"$ISSUE_ORCHESTRATOR_PYTHON" "$ROOT/scripts/probe_namespaced_codex_sandbox.py" ||
  fail "Namespaced Git ref sandbox failed: no model started"

issue-orchestrator doctor --config "$CONFIG" ||
  fail "Original Issue-Orchestrator doctor failed"

# Only after all repo/agent/label checks: permit 127.0.0.1 through the
# native managed network proxy. The patch refuses other workspace roots.
export ISSUE_ORCHESTRATOR_IO570_LOOPBACK_PROXY=1
"$ISSUE_ORCHESTRATOR_PYTHON" "$ROOT/scripts/probe_io570_loopback_proxy.py" ||
  fail "Managed loopback proxy did not pass the no-model security gate"

echo "ORIGINAL_ENGINE_START=ORIGINAL_ENGINE_ONLY"
echo "Continuous WIP=1 queue: wait for PR/merge/CI, no per-Issue relaunch."
exec issue-orchestrator --config "$CONFIG" start \
  --no-dashboard --max-issues 2 --queue-refresh 120
