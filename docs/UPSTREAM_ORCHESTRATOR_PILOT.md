# Original Issue-Orchestrator 0.10.0 - disposable pilot #570

**HOST RUNTIME PREFLIGHT PASS (OWNER-REPORTED) / ORIGINAL GUARDRAILS IN PR #9 WITH CI PASS / NO AUTONOMOUS E2E YET.**

- Authoritative engine: https://github.com/issue-orchestrator/issue-orchestrator
- Pinned upstream SHA: `d4a79824ccd806089cf3f70ec632d39b8ee255ea`; no auto-upgrade.
- Selected repository: `MikeMoore1337/adt-orchestrator-pilot`, target `main`.
- Only new synthetic Issues [#7](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/7) and [#8](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/8), label `adt-io570-pilot-20261109`. #8 has `Depends-on: #7`.
- Candidate upstream config: `.issue-orchestrator/config/modes/upstream-pilot/main.yaml`; pilot metadata: `.issue-orchestrator/io570-scope.json` (informational, not an interlock). The agent worktree seed is protected `origin/main`. Merge PR #9 as a reviewed source-only baseline before authorizing Issue #7; before merge, the source prompts are intentionally absent from this seed.
- Owner installed the pinned upstream engine in WSL2, verified CLI/GitHub ChatGPT login, and ran `doctor` with zero critical failures. The original generated Codex hooks and Git pre-push guardrail are **published in draft PR #9**, with offline contracts and exact-HEAD Python 3.13/3.14 CI PASS. `doctor` is not a live coding/review/merge E2E.
- The original `codex` provider invokes Codex CLI, **authorized by the owner only with ChatGPT sign-in**. WSL2 `codex-cli 0.167.0` and `codex login status` = `Logged in using ChatGPT` are owner-reported PASS. OpenAI API-key billing remains forbidden; no automatic credit spending authorized.
- The synthetic pilot now uses **one original-engine queue**: exclusive `filtering.label: adt-io570-pilot-20261109`, `max_to_start: 2`, `max_concurrent_sessions: 1`, and #8's native `Depends-on: #7`. Do **not** use `--issue 7` in an eventual authorized launch; that would block automatic #8. The label is owner-controlled but **mutable**, not an immutable multi-Issue allowlist. Do not use label-only admission in untrusted production repositories without an additional reviewed policy. `io570-scope.json` is informational and cannot enforce limits.
- Owner ran original `setup-guardrails` and `doctor`. Native `codex sandbox` independently booted; a no-model permission-profile probe using a relocated same-version Codex executable and separate runtime passed both workspace write and denial of a synthetic 0600 canary under `~/.config/gh`. This does **not** prove a real agent session or every subprocess boundary. Do **not** run non-dry-run `start` until permanent-runtime policy verification, branch safeguards, exact #7 admission and operator activation pass. Never run a Toolkit-owned scheduler.
- Independent review, exact-head CI, human merge, post-merge CI and restart recovery are mandatory before considering upstream E2E completed.

## Portable pre-push guardrails (published in draft PR #9)

The original upstream `setup-guardrails` generates `scripts/verify-pr.sh` and, for an external repository, may embed the absolute path of the local interpreter used at install time. Do **not** commit an owner-specific `/home/.../.venv/bin/python` fallback to this public pilot.

For the reviewed pilot copy only, remove **just** the generated two-line absolute-path `elif [ -x ... ]; then` / `PYTHON_BIN=...` fallback after verifying it matches that generator's template exactly. Preserve the authoritative `issue-orchestrator-selection: modes/upstream-pilot/main.yaml`, the optional `ISSUE_ORCHESTRATOR_PYTHON` environment override, the `.venv` / `python3` fallback, and the mandatory `import issue_orchestrator` fail-closed test. Supply `ISSUE_ORCHESTRATOR_PYTHON` as a locally configured absolute path at runtime; do **not** commit that value or the user home directory into the repository.

Regenerating guardrails using original `setup-guardrails` may recreate the host-specific interpreter fallback: repeat the review and portability correction after regeneration. This documents a manual pilot portability adjustment; it is **not** a fork of the upstream engine and does not weaken mandatory pre-push tests. Never suppress the checks merely to make a push pass.

Independent GitHub blob-SHA comparisons show exact upstream matches for `.codex/rules/orchestrator.rules`, `.codex/hooks/block-no-verify.sh`, `.codex/hooks/block_no_verify.py`; `.codex/hooks.json` has a synchronous Bash PreToolUse registration. Pattern-based token scan reported no matches, which is not a complete secret audit. Synthetic native shell canary access denial is **PASS**, but real agent-session credential isolation is **NOT_VERIFIED**.

## Pinned host runtime (local environment only; never commit credentials)

- The owner reported `CODEX_COPY=PASS`, `BINARY_SHA256=PASS`, `codex-cli 0.167.0`, and `Logged in using ChatGPT` using a separate release at `$HOME/.local/share/adt-io570/codex-0.167.0/bin`, leaving the original `~/.codex` installation unchanged.
- `ISSUE_ORCHESTRATOR_CODEX_RUNTIME_ROOT` is set in the operator shell to `$HOME/.local/state/adt-io570/codex-runtime`, outside the denied `~/.issue-orchestrator`. Original `prepare_codex_runtime_home()` / `verify_codex_runtime_home()` both passed with a managed authentication symlink.
- Never set parent `CODEX_HOME` or expose authentication details. Original `CodexProvider.executable` resolves the name `codex` via `PATH`, so **each real launch process** must verify the correct binary and runtime root. Local exports do not persist automatically into other shells or services.
- The `io570-scope.json` field `constraints.allowed_runtime: false` is **metadata only**, not a runtime kill switch.

### One sequential queue - blocked on native linked-worktree sandbox

Goal: a single upstream Issue-Orchestrator instance claims #7, performs coding, quick/publish validation and independent review, opens a PR and **waits for the owner's merge and exact post-merge CI**. After #7 is CLOSED, native `Depends-on: #7` lets the **same running process** begin #8, without manual `--issue` or a second scheduler. Concurrency is one. Failed security/validation gates must block; no auto-merge.

The first actual Codex coding session in WSL2 **did not implement #7**. A `bubblewrap` "Not a directory" sandbox bootstrap failure occurred before commands ran; the original engine recorded `TIMED_OUT` after 45 minutes and marked #7 `blocked-failed`. Do **not** remove the blocked label or rerun the model yet; preserve the original failed worktree and its session evidence.

The earlier no-model positive/negative profile proof used an isolated `git init` checkout; real work used a **linked Git worktree**, with additional per-file writable Git admin rules. In pinned upstream `execution/agent_runner_providers/git_worktree_access.py`, `git_worktree_filesystem_rules()` grants `write` on individual ref/reflog paths and `*.lock` names. Open Codex Linux bugs [#40433](https://github.com/openai/codex/issues/40433) and [#52651](https://github.com/openai/codex/issues/52651) demonstrate that exact-file writable roots can cause the sandbox to synthesize `.git` / `.aws` descendants under a regular file and crash. That is a **source-grounded leading hypothesis**, not yet confirmed for the exact failed mount path on this host.

### Fail-closed operator launcher

The operator-facing `scripts/start_guarded_pilot.sh` is a **one-time preflight + exec**, NOT a second supervisor or queue. It checks the isolated ChatGPT Codex environment, exact remote base, the two designated synthetic issues, original engine configuration, runs the **no-model linked-worktree sandbox probe**, then invokes original `issue-orchestrator doctor` and finally `exec issue-orchestrator ... start` without `--issue 7` (WIP=1, one queue). A failure exits before any model request. The launcher does not clear `blocked-failed`, reset a worktree, auto-merge or change project code.

The owner must preserve the failed #7 session and arrange its upstream-supported retry only after a proven sandbox fix. **No model or start is authorized while the linked probe fails.** CI only verifies script syntax; it does not validate WSL2 sandbox operation.

The included `scripts/probe_linked_codex_sandbox.py` constructs a **new, disposable, synthetic linked worktree** and uses the unmodified pinned upstream permission profile with the copied Codex 0.167.0 executable and original managed runtime. It does not invoke a model or GitHub API, and does not change the failed Issue #7 worktree. It checks native sandbox initialization, worktree file writes, Git stage/commit, outside-workspace denial and a harmless GitHub-directory canary. Temporary test files and branches are removed on exit. It is opt-in and not executed by CI; CI merely checks its Python syntax. A failure is an actual blocker, not a suggestion to grant broad Git metadata write permissions.

**Do not solve the Linux crash** by switching to `danger-full-access`, `bypassPermissions`, or broader write access to the base checkout's `.git/refs` or `.git/config`. Prefer an upstream Codex fix that preserves exact-file Git metadata confinement. Only after a native linked-worktree OS test PASS and a real provider-launch preflight may the `blocked-failed` state be reconsidered.

One verified result is **not** complete E2E. #570 stays open until #7 -> PR -> exact-head CI -> human merge -> post-merge CI -> CLOSED automatically unlocks #8, and both issues complete with restart/reconciliation evidence.

Tracking: [ADT #570](https://github.com/MikeMoore1337/ai-development-toolkit/issues/570). This repository must remain isolated from real user projects.
