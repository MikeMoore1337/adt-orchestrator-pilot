# Original Issue-Orchestrator 0.10.0 - scoped Git ref namespace fix

Source: `issue-orchestrator/issue-orchestrator@d4a79824ccd806089cf3f70ec632d39b8ee255ea`.
Only the original worktree branch name generation and Git filesystem permission rules are changed. No forked scheduler, task selector, queue or lifecycle controller.

On host opt-in `ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS=1`, branch names become `7-task-slug/agent`, and the original Codex profile grants write to **only** the corresponding existing `refs/heads/7-task-slug` and `logs/refs/heads/7-task-slug` directories. The shared `.git/refs/heads` and `.git/logs/refs/heads` stay READ ONLY.

No exact regular-file `write` roots appear in the resulting profile. This avoids the 0.167.0 Codex ENOTDIR bootstrap bug, while permitting Git to atomically create `agent.lock` in the isolated issue directory. The original **unpatched** copied Codex 0.167.0 can therefore be used; a separate custom Rust binary may not be necessary.

Default upstream behavior remains unchanged when the opt-in environment variable is absent. If enabled, unnamespaced legacy Git refs or unexpected sibling refs cause an explicit fail-closed `SandboxUnsupportedError`. This means **do not retry the original Issue #7 worktree** until it has been safely archived and migrated by an owner-reviewed original-engine recovery action.

CI must independently validate `git apply --check` on the exact upstream SHA and prove a Git commit under a read-only common `refs/heads` using only the issue-specific directory. Native WSL2 no-model `codex sandbox` must still pass before any model is run. No secret, billing or branch-protection bypass.

**Status:** source patch CI PASS; native WSL2 Codex sandbox and E2E NOT_VERIFIED, engine #570 OPEN.

## Local one-off WSL2 check - no model

From the pilot repository checkout after pinning the PR head, extract the following files using `git archive`: `scripts/prepare_namespaced_original_engine.sh`, `scripts/apply_orchestrator_git_ref_fix.py`, `scripts/probe_namespaced_codex_sandbox.py`, and `upstream/issue-orchestrator-0.10.0-isolated-git-refs.patch`. Do **not** change the checked-out `main` branch and do not run `issue-orchestrator start`.

```bash
source "$HOME/projects/issue-orchestrator/.venv/bin/activate"
bash scripts/prepare_namespaced_original_engine.sh
export PYTHONPATH="$HOME/.local/state/adt-io570/original-engine-namespaced/src"
export ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS=1
export ISSUE_ORCHESTRATOR_CODEX_RUNTIME_ROOT="$HOME/.local/state/adt-io570/codex-runtime"
export PATH="$HOME/.local/share/adt-io570/codex-0.167.0/bin:$PATH"
unset CODEX_HOME OPENAI_API_KEY CODEX_API_KEY
python scripts/probe_namespaced_codex_sandbox.py
```

Expected native result: `ORIGINAL_CODEX_UNMODIFIED=YES`, `ORIGINAL_ENGINE_ISOLATED_REF_SOURCE=PASS`, `EXACT_GIT_FILE_WRITE_RULES=0`, `NAMESPACED_REF_WRITE=PASS`, `SANDBOX_EXIT=0`, `SHELL_BOOT=PASS`, `GIT_COMMIT=PASS`, `MAIN_REF_DENY=PASS`, `GH_CANARY_DENY=PASS`, `OUTSIDE_WRITE_DENY=PASS`, `LINKED_SANDBOX_GATE=PASS`.

**These are example commands for extracted files; do not run from the unmerged PR's `main` checkout where the new scripts do not yet exist.** Never activate the original engine until all PASS signals are physically verified and Issue #7 recovery is reviewed.
