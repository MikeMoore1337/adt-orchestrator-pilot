# Original Issue-Orchestrator v0.10.0 - strictly scoped synthetic Stage 2

**PREPARATION - NOT ACTIVATED.** Only Issues #20 then #21 may be processed by the original engine, after independent exact-head CI, an owner-approved merge, physical WSL2 no-model sandbox/credential-denial checks, staging the exact Stage-2 label, and a **separate explicit owner activation**. An Issue body, README, or source-only PR never authorizes agent execution.

- Execution owner: original upstream issue-orchestrator pinned to `d4a79824ccd806089cf3f70ec632d39b8ee255ea` with only reviewed opt-in pilot patches. Never use Toolkit's older supervisors, new schedulers, or extra queue state.
- Repository **only**: `MikeMoore1337/adt-orchestrator-pilot`, protected base `main`. Worktrees seed strictly from protected `origin/main` after the source PR is merged. No changes or paid calls to YFC, Hermes, ADT, other repos, or production.
- Current pilot issues: **#20 (to_rankine)** and **#21 (from_rankine + round-trip)**; #21 has `Depends-on: #20`. Earlier #7/#8 are CLOSED and excluded from this Stage-2 selection. Do not relabel, reopen or replay them.
- The current Stage-2 activation label is `adt-io570-stage2-20261114`. This label is deliberately **not** assigned during preparation. Apply it and `agent:dev` to exactly #20/#21 only after the new guarded launch source is protected-branch merged and approved; never apply to any third issue.
- **WIP=1**, one original engine, no replacement worker; use the native dependency/priority queue, quick and publish unittest, independent original reviewer, actual original-engine branch push and PR creation, exact-head CI, owner/human merge and post-merge verification before #21 may start.
- Codex CLI with **ChatGPT login only**; no `OPENAI_API_KEY`, `CODEX_API_KEY`, Claude CLI, billing, or additional model API. Strict native sandbox with denied GitHub credentials, shared main branch writes and external paths; no disabled hooks or `--no-verify`.
- Stage-2 opt-in Git exact lease verifies the remote branch SHA, ancestor relation and CAS for #20/#21 agent refs only; diverged or racing refs are hard failures. Never force-push or manually publish a PR to claim autonomous success.
- Preserve retained validated-work SQLite, pinned refs, escrow and operator approval history; old #7 terminal `operator_abandoned` is authoritative.
- Use `scripts/start_guarded_pilot.sh` **only after separate owner activation**. It is a narrow preflight plus `exec` of the original engine, not a scheduler; any unexpected open issue, label, dependency, protected ref, pre-push/permission failure or incomplete no-model preflight stops execution.
- The label is mutable during a run, so the static one-shot admission check is **not an immutable upstream scheduler allowlist**. Do not extrapolate this disposable repo setup to a multi-user/untrusted production repository.
- Source-only GitHub PRs/CI do not certify real WSL2 agent invocation, PR creation, review, restart recovery or end-to-end completion. Record observable run receipts.

Tracking: [AI Development Toolkit #570](https://github.com/MikeMoore1337/ai-development-toolkit/issues/570).
