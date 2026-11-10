# Original Issue-Orchestrator 0.10.0 - disposable pilot #570

**HOST RUNTIME PREFLIGHT PASS (OWNER-REPORTED) / ORIGINAL GUARDRAILS IN PR #9 WITH CI PASS / NO AUTONOMOUS E2E YET.**

- Authoritative engine: https://github.com/issue-orchestrator/issue-orchestrator
- Pinned upstream SHA: `d4a79824ccd806089cf3f70ec632d39b8ee255ea`; no auto-upgrade.
- Selected repository: `MikeMoore1337/adt-orchestrator-pilot`, target `main`.
- Only new synthetic Issues [#7](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/7) and [#8](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/8), label `adt-io570-pilot-20261109`. #8 has `Depends-on: #7`.
- Candidate upstream config: `.issue-orchestrator/config/modes/upstream-pilot/main.yaml`; pilot scope: `.issue-orchestrator/io570-scope.json`.
- Owner installed the pinned upstream engine in WSL2, verified CLI/GitHub ChatGPT login, and ran `doctor` with zero critical failures. The original generated Codex hooks and Git pre-push guardrail are **published in draft PR #9**, with offline contracts and exact-HEAD Python 3.13/3.14 CI PASS. `doctor` is not a live coding/review/merge E2E.
- The original `codex` provider invokes Codex CLI, **authorized by the owner only with ChatGPT sign-in**. WSL2 `codex-cli 0.167.0` and `codex login status` = `Logged in using ChatGPT` are owner-reported PASS. OpenAI API-key billing remains forbidden; no automatic credit spending authorized.
- In phase 1, the original engine enforces `filtering.issue: 7` and `max_to_start: 1`, in addition to the mutable label and WIP=1. The pinned queue-cache and PR review-scope checks implement this single-Issue filter. Select `--issue 8` only after #7 has passed exact-head CI, human merge, post-merge checks and is CLOSED. The original engine has **no native immutable two-Issue allowlist**; the `[7,8]` JSON is informational, not an enforcement boundary.
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

### Phase 1 only: Issue #7 (not yet authorized to start)

Upstream supports `filtering.issue: 7`, `max_to_start: 1`, `max_concurrent_sessions: 1`; this first phase cannot admit #8 or a third Issue solely by copying the label. An upstream `start --dry-run --issue 7 --max-issues 1` may still *display* all label-matching issues because the dry-run fetches by label before presenting a table; do not interpret that table alone as proof of admission. Independently check the original `QueueCache.evaluate_issue` and the exact GitHub Issue snapshots.

Only after human merge and CLOSED #7 should a separate phase explicitly override to `--issue 8`. This two-phase pilot is bounded but does not by itself demonstrate unattended multi-Issue selection. E2E requires actual model coding, independent review, exact PR-head CI, human merge, post-merge CI and restart/reconciliation. The Draft PR and Issue #570 must remain open until those gates are verified.

Tracking: [ADT #570](https://github.com/MikeMoore1337/ai-development-toolkit/issues/570). This repository must remain isolated from real user projects.
