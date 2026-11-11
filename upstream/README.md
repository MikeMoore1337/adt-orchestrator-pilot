# Original Issue-Orchestrator 0.10.0 - scoped Git ref namespace fix

Source: `issue-orchestrator/issue-orchestrator@d4a79824ccd806089cf3f70ec632d39b8ee255ea`.
Only the original worktree branch name generation and Git filesystem permission rules are changed. No forked scheduler, task selector, queue or lifecycle controller.

On host opt-in `ISSUE_ORCHESTRATOR_ISOLATED_GIT_REF_DIRS=1`, branch names become `7-task-slug/agent`, and the original Codex profile grants write to **only** the corresponding existing `refs/heads/7-task-slug` and `logs/refs/heads/7-task-slug` directories. The shared `.git/refs/heads` and `.git/logs/refs/heads` stay READ ONLY.

No exact regular-file `write` roots appear in the resulting profile. This avoids the 0.167.0 Codex ENOTDIR bootstrap bug, while permitting Git to atomically create `agent.lock` in the isolated issue directory. The original **unpatched** copied Codex 0.167.0 can therefore be used; a separate custom Rust binary may not be necessary.

Default upstream behavior remains unchanged when the opt-in environment variable is absent. If enabled, unnamespaced legacy Git refs or unexpected sibling refs cause an explicit fail-closed `SandboxUnsupportedError`. This means **do not retry the original Issue #7 worktree** until it has been safely archived and migrated by an owner-reviewed original-engine recovery action.

CI must independently validate `git apply --check` on the exact upstream SHA and prove a Git commit under a read-only common `refs/heads` using only the issue-specific directory. Native WSL2 no-model `codex sandbox` must still pass before any model is run. No secret, billing or branch-protection bypass.

**Status:** proposed source-level correction; native WSL2 NOT_VERIFIED, engine #570 OPEN.
