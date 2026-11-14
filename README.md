# Original Issue-Orchestrator - synthetic pilot for ADT #570

**Current status: Stage 2 prepared, execution NOT authorized.** The first two original-engine Issues #7/#8 were closed; the retained #7 work was released by a verified maintainer-approved proposal #19, `recovery-pending` was removed by the original engine, and restart preservation was physically checked in WSL2. The first cycle was **not fully autonomous**: #8 required operator Git publication after an exact-lease `stale info` failure.

## Stage 2

- [Issue #20](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/20): `to_rankine(kelvin)`.
- [Issue #21](https://github.com/MikeMoore1337/adt-orchestrator-pilot/issues/21): `from_rankine(rankine)` and roundtrip tests, `Depends-on: #20`.
- Protected base: `main`. **Neither Issue has an agent or scope-selection label yet**. Preparation never triggers model work.
- Original engine pin: `d4a79824ccd806089cf3f70ec632d39b8ee255ea` (0.10.0); Codex CLI by ChatGPT login, no paid API keys.
- One queue, `WIP=1`, original quick/publish unit tests, independent review, engine-created PR, exact-head CI, human merge, post-merge CI, then automatically advance to #21.
- Exact remote SHA and ancestry verification opt-in: `upstream/issue-orchestrator-0.10.0-io570-exact-lease-push.patch`; only #20/#21 agent branches, no tracking-ref heuristic, no force rewrite of unrelated history.
- The sole runtime launcher is the reviewed `scripts/start_guarded_pilot.sh` using `.issue-orchestrator/config/modes/upstream-pilot/main.yaml`. **Do not execute it yet**. First check source-PR CI, merge approval, physical no-model gates and separate owner activation, then add the exact Stage-2 label `adt-io570-stage2-20261114` and `agent:dev` to both Issues. The label alone is mutable; the guarded launcher performs strict one-shot membership checks and rejects other open Issues.
- Inspect the versioned [AGENTS.md](AGENTS.md), [pilot docs](docs/UPSTREAM_ORCHESTRATOR_PILOT.md) and [metadata](.issue-orchestrator/io570-scope.json). No second supervisor, extra model or production deployment.

## Existing synthetic converter

```python
from converter import from_kelvin, to_celsius, to_fahrenheit, to_kelvin
assert to_kelvin(0) == 273.15
assert from_kelvin(0) == -273.15
```

Before Stage-2 activation, the existing converter deliberately **does not** implement the requested Rankine functions. Tests: `python -m unittest discover -s tests -v`; GitHub CI covers Python 3.13 and 3.14. Earlier pilot history remains in GitHub PRs #9-#19 and prior documentation revisions.
