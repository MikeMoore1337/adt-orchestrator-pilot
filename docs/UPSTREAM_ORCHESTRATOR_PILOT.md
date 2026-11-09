# Original Issue-Orchestrator 0.10.0 - disposable pilot #570

**SOURCE ONLY / CLI APPROVED BY OWNER / HOST RUNTIME NOT VERIFIED / E2E NOT VERIFIED.**

- Authoritative engine: https://github.com/issue-orchestrator/issue-orchestrator
- Pinned upstream SHA: `d4a79824ccd806089cf3f70ec632d39b8ee255ea`; no auto-upgrade.
- Selected repository: `MikeMoore1337/adt-orchestrator-pilot`, target `main`.
- Only new synthetic Issues [#7](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/7) and [#8](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/8), label `adt-io570-pilot-20261109`. #8 has `Depends-on: #7`.
- Candidate upstream config: `.issue-orchestrator/config/modes/upstream-pilot/main.yaml`; pilot scope: `.issue-orchestrator/io570-scope.json`.
- A YAML config is not a running agent. No start, no OS-level credential isolation, no SDK provider adapter and no autonomous E2E are demonstrated.
- The original `codex` provider invokes Codex CLI, **now authorized by the owner with ChatGPT sign-in**. Windows `codex login status` reportedly returned `Logged in using ChatGPT`. Verify the same state in the actual host (WSL/Linux may use a separate login). OpenAI API-key billing stays forbidden.
- The original label filter cannot enforce an immutable `[7, 8]` list throughout runtime. Freeze and recheck membership before activation; do not assume a mutable label provides a permanent boundary.
- After host security, branch and issue-scope checks pass, use the original engine's documented `setup`, `setup-guardrails`, `init`, `doctor`, `start`, `status`, `pause`, `resume` and `restart` commands; never a Toolkit-owned scheduler. No such command has been executed.
- Independent review, exact-head CI, human merge, post-merge CI and restart recovery are mandatory before considering upstream E2E completed.

Tracking: [ADT #570](https://github.com/MikeMoore1337/ai-development-toolkit/issues/570). This repository must remain isolated from real user projects.
