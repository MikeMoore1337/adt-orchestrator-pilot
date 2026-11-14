# Stage-2 synthetic original-engine worker

Work **only on the assigned #20 or #21** after the authorized guarded launch. Read AGENTS.md and the complete Issue; verify its active Stage-2 label and native dependency. Issue #20 adds `to_rankine(kelvin)`; #21 adds `from_rankine(rankine)` and round trips, **only after #20 is closed and merged**.

Edit only `converter.py` and `tests/test_converter.py` for the smallest correct change. Run original configured quick/publish unittest, retain native sandbox and standard hooks. Complete through the original upstream agent completion command, not a Toolkit queue or direct manual PR. If remote lease diverges, abort and preserve evidence. No extra APIs, force pushes or production.
