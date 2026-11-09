# Original Issue-Orchestrator 0.10.0 - disposable pilot #570

**OWNER-REPORTED WSL2 PREFLIGHT PASS / GUARDRAILS INSTALLED LOCALLY / E2E NOT VERIFIED.**

- Authoritative engine: https://github.com/issue-orchestrator/issue-orchestrator
- Pinned upstream SHA: `d4a79824ccd806089cf3f70ec632d39b8ee255ea`; no auto-upgrade.
- Selected repository: `MikeMoore1337/adt-orchestrator-pilot`, target `main`.
- Only new synthetic Issues [#7](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/7) and [#8](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/8), label `adt-io570-pilot-20261109`. #8 has `Depends-on: #7`.
- Candidate upstream config: `.issue-orchestrator/config/modes/upstream-pilot/main.yaml`; pilot scope: `.issue-orchestrator/io570-scope.json`.
- Owner installed the pinned upstream engine in WSL2, verified CLI/GitHub ChatGPT login, and ran `doctor` with zero critical failures. The local repo's generated Codex hooks and Git pre-push guardrail are still **untracked and not part of this PR**. `doctor` is not a live coding/review/merge E2E; OS-level credential isolation is not proven.
- The original `codex` provider invokes Codex CLI, **authorized by the owner only with ChatGPT sign-in**. WSL2 `codex-cli 0.167.0` and `codex login status` = `Logged in using ChatGPT` are owner-reported PASS. OpenAI API-key billing remains forbidden; no automatic credit spending authorized.
- The original label filter cannot enforce an immutable `[7, 8]` list throughout runtime. Freeze and recheck membership before activation; do not assume a mutable label provides a permanent boundary.
- In the pilot only, the owner executed the original `setup-guardrails` and `doctor` commands. Do **not** run `start`, `init` or publish generated changes before an independent review, immutable two-Issue admission check, credential-denial test and approval. Never run a Toolkit-owned scheduler.
- Independent review, exact-head CI, human merge, post-merge CI and restart recovery are mandatory before considering upstream E2E completed.

## Portable pre-push guardrails (before publishing generated files)

The original upstream `setup-guardrails` generates `scripts/verify-pr.sh` and, for an external repository, may embed the absolute path of the local interpreter used at install time. Do **not** commit an owner-specific `/home/.../.venv/bin/python` fallback to this public pilot.

For the reviewed pilot copy only, remove **just** the generated two-line absolute-path `elif [ -x ... ]; then` / `PYTHON_BIN=...` fallback after verifying it matches that generator's template exactly. Preserve the authoritative `issue-orchestrator-selection: modes/upstream-pilot/main.yaml`, the optional `ISSUE_ORCHESTRATOR_PYTHON` environment override, the `.venv` / `python3` fallback, and the mandatory `import issue_orchestrator` fail-closed test. Supply `ISSUE_ORCHESTRATOR_PYTHON` as a locally configured absolute path at runtime; do **not** commit that value or the user home directory into the repository.

Regenerating guardrails using original `setup-guardrails` may recreate the host-specific interpreter fallback: repeat the review and portability correction after regeneration. This documents a manual pilot portability adjustment; it is **not** a fork of the upstream engine and does not weaken mandatory pre-push tests. Never suppress the checks merely to make a push pass.

Source matches reported by owner: `.codex/rules/orchestrator.rules`, `.codex/hooks/block-no-verify.sh`, `.codex/hooks/block_no_verify.py` matched upstream templates; `.codex/hooks.json` has a synchronous Bash PreToolUse registration. Pattern-based token scan reported no matches, which is not a complete secret audit. Real agent denial of reading `~/.config/gh` remains NOT_VERIFIED.

Tracking: [ADT #570](https://github.com/MikeMoore1337/ai-development-toolkit/issues/570). This repository must remain isolated from real user projects.
