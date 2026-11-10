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

codex --version
LOGIN="$(codex login status 2>&1)" ||
  fail "Codex login status failed"
[[ "$LOGIN" == *"Logged in using ChatGPT"* ]] ||
  fail "Codex is not authenticated through ChatGPT"
echo "CODEX_CHATGPT_LOGIN=PASS"

CONFIG=".issue-orchestrator/config/modes/upstream-pilot/main.yaml"
"$ISSUE_ORCHESTRATOR_PYTHON" - "$CONFIG" <<'PY' ||
  fail "Original queue configuration failed validation"
import sys
from pathlib import Path
from issue_orchestrator.infra.config import Config
config = Config.load(Path(sys.argv[1]).resolve())
assert config.repo == "MikeMoore1337/adt-orchestrator-pilot"
assert config.worktree_seed_ref == "origin/main"
assert config.max_concurrent_sessions == 1
assert config.filtering.label == "adt-io570-pilot-20261109"
assert config.filtering.issue is None
assert config.filtering.max_to_start == 2
assert config.review_enabled
assert not config.merge_queue.enabled
assert all(a.sandbox for a in config.agents.values())
print("SEQUENTIAL_QUEUE_CONFIG=PASS")
PY

# Owner-controlled synthetic pilot scope only, no unexpected labeled issues.
mapfile -t SELECTED < <(
  gh issue list --repo MikeMoore1337/adt-orchestrator-pilot \
    --state all --limit 100 --label adt-io570-pilot-20261109 \
    --json number --jq '.[].number' | sort -n
)
[[ "${#SELECTED[@]}" -gt 0 ]] ||
  fail "No pilot-labeled issues"
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
GH8_BODY="$(gh issue view 8 --repo MikeMoore1337/adt-orchestrator-pilot \
  --json body --jq '.body')" ||
  fail "Cannot inspect Issue #8 dependency"
grep -q '^Depends-on: #7' <<< "$GH8_BODY" ||
  fail "Issue #8 is missing its original Depends-on: #7 directive"
echo "PILOT_GITHUB_SCOPE=PASS"

# No model invocation. If linked Git sandbox cannot start, fail in seconds.
"$ISSUE_ORCHESTRATOR_PYTHON" "$ROOT/scripts/probe_linked_codex_sandbox.py" ||
  fail "Linked-worktree native sandbox test failed; NO model started"

issue-orchestrator doctor --config "$CONFIG" ||
  fail "Original Issue-Orchestrator doctor failed"
echo "ORIGINAL_ENGINE_START=ORIGINAL_ENGINE_ONLY"
echo "Continuous WIP=1 queue: wait for PR/merge/CI, no per-Issue relaunch."
exec issue-orchestrator --config "$CONFIG" start \
  --no-dashboard --max-issues 2 --queue-refresh 120
