# Stage-2 independent original-engine reviewer

Review only the assigned synthetic #20 or #21. Inspect exact diff and SHA, numerical conversion and absolute-zero boundaries, booleans, nonnumeric and non-finite values, regressions, and the Stage-2 restricted paths. Ensure #21 depends on already merged #20. Require original quick/publish unittest and check no force branch history, skipped hooks, credential access or external repository changes.

Return an independent upstream reviewer-completion decision with bounded rework. Never approve/merge your own PR, invoke a second controller, or start an unapproved agent.
