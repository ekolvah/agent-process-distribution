## 0. Delivery

- [ ] 0.1 Tracking issue for this change (ask the person for the priority, set the Project field); `gh issue develop -c <N>`; `set_status <N> "In progress"`

## 1. Coverage check

- [ ] 1.1 `scripts/check_coverage.py`: locate the change under `openspec/changes/<change>/` or `openspec/changes/archive/*-<change>/` (the archive commit is the head that must be mergeable); scenarios parsed from its `specs/**/spec.md`, mapping from its `tasks.md`, results from the JUnit report; exit 1 naming uncovered scenarios
- [ ] 1.2 Add it as a required check in the reusable workflow and `ruleset.json`
- [ ] 1.3 Test named after `Missing test`

## 2. Requirement coverage

- [ ] 2.1 `tests/test_spec_coverage.py`: every requirement title under `openspec/specs/` appears in a test name or docstring
- [ ] 2.2 Test named after `Test deleted`
- [ ] 2.3 Verify: a PR with an uncovered scenario is not mergeable

## 3. Deliver

- [ ] 3.1 `ci_check` green; open the PR (body: change name, tracked deferrals as issue links)
- [ ] 3.2 `wait_for_pr`; apply every unresolved thread or reply on the one left to the person; repeat until nothing is unresolved
- [ ] 3.3 `finish_change v2-3-coverage-gate` — marks this task, `openspec archive v2-3-coverage-gate -y`, commit, push, `wait_for_pr` on that head
