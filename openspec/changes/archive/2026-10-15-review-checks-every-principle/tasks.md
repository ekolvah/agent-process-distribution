## 0. Delivery start

- [x] 0.1 Run `agent-process start_change review-checks-every-principle --planner Claude --implementer Claude` (tracking issue 430), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_reusable_workflows.py`, move `bullet_containing` out of `test_review_contract_and_principles_stay_coupled_on_narrow_simplicity_triggers` to a module-level `_bullet_containing` that both tests call. Add `test_review_contract_labels_each_principle`: the `Policy source` bullet names `trusted/skills/agent-process/principles.md`, and the bullet containing `` `P0`/`P1` mean `` names each of §I–VI (a regex so no section matches inside a longer one: `§I` in `§II`, `§V` or `§VI` in `§VII`)
- [x] 1.2 Run `agent-process check_red` with the node id of 1.1 and commit RED with these ticks

## 2. Contract

- [x] 2.1 In `.agent-process/REVIEW_CONTRACT.md`, add to the `Policy source` bullet a clause of its own, outside its default-branch list: principles §I–VII of `trusted/skills/agent-process/principles.md` bind the diff. In the `P0`/`P1` sentence, tag "a failing or missing behavioural test" `(§I)` and extend "a convention violation" with the breaches a diff shows: §II a test mocking the repository's own logic or an external client not behind an injected Protocol, §III user-visible data lost without a red run, §IV a swallowed error or fail-open branch, §V a retry, shim or broadened `except` whose cause the worktree does not name, §VI configuration checked after load; the signal labels the finding and names the section, and the full text settles a borderline case. Verify `tests/publisher/test_reusable_workflows.py`
- [x] 2.2 Commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [x] 4.1 Run `agent-process archive_change review-checks-every-principle`, then `gh pr create --title "feat: review-checks-every-principle" --body-file <report>`. The report names tracking issue 430 as a plain reference, the principles the change interacts with, and the scenario-to-test map
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| review-and-merge / Each principle has a severity | `tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle` |
