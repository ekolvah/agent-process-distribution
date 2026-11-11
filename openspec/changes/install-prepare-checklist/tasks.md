## 0. Delivery start

- [x] 0.1 Run `agent-process start_change install-prepare-checklist --planner Claude --implementer Claude` (tracking issue 488), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: docs-only (`skip_specs: true`); no scenario changes

## 2. Prepare checklist

- [x] 2.1 Per design D1–D4, open `## Install` of `skills/agent-process/SKILL.md` with the unnumbered Prepare list the proposal names; trim steps 1, 3 and 6 to point back to Prepare when `init` still prints the row, keeping the step numbers and the texts the Install tests assert; step 4 stays. Verify with `wc -w` that the numbered steps plus Prepare grow by no more than Prepare's items net of what steps 1 (114 words), 3 (64) and 6 (81) lose, and that `python -m pytest tests/publisher/test_planning_workflow.py -q` is green
- [x] 2.2 Per design D5, point `README.md`'s `Requires:` line to Install's Prepare, keeping the plugin commands; verify `grep -n "Prepare" README.md` hits it, then commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change install-prepare-checklist`, then `gh pr create --title "docs: install-prepare-checklist" --body-file <report>`. The report names tracking issue 488 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 3, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| none | n/a: docs-only, `skip_specs: true`; existing `tests/publisher/test_planning_workflow.py` Install tests guard the asserted texts |
