## 1. Coverage check

- [ ] 1.1 `scripts/check_coverage.py`: scenarios from `openspec show <change> --json --deltas-only`, mapping from `tasks.md`, results from the JUnit report; exit 1 naming uncovered scenarios
- [ ] 1.2 Add it as a required check in the reusable workflow and `ruleset.json`
- [ ] 1.3 Test named after `Missing test`

## 2. Requirement coverage

- [ ] 2.1 `tests/test_spec_coverage.py`: every requirement title under `openspec/specs/` appears in a test name or docstring
- [ ] 2.2 Test named after `Test deleted`
- [ ] 2.3 Verify: a PR with an uncovered scenario is not mergeable; `openspec archive v2-3-coverage-gate` as the last commit of the PR
