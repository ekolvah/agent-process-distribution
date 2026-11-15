## 0. Delivery start

- [x] 0.1 Run `agent-process start_change check-passes-seeded-format --planner Claude --implementer Claude` (tracking issue 521), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 In `tests/publisher/test_init_config.py` add `test_seeded_format_keeps_the_check`, parametrized `no-config` / `line-length-60`, per design D2
- [ ] 1.2 Run `agent-process check_red` on both cases, verify both fail with the hook reformatting `.claude/agent-process-check.py`, and commit RED with the group 1 ticks

## 2. Implementation

- [ ] 2.1 Insert `# fmt: off` as line 2 of `skills/agent-process/templates/skill_check.py` (D1); verify `python -m pytest tests/publisher/test_init_config.py tests/publisher/test_skill_check.py -q` is green. Commit with the tick

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change check-passes-seeded-format`, then `gh pr create --title "fix: check-passes-seeded-format" --body-file <report>`. The report names the tracking issue as a plain reference, carries the scenario-to-test map, states design **Risks**, names the principles it interacts with (§I, §VII), and carries the consumer note from proposal Impact
- [ ] 4.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Any consumer ruff configuration | `tests/publisher/test_init_config.py::test_seeded_format_keeps_the_check[no-config]`, `[line-length-60]` |
