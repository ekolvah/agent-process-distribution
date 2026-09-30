## 0. Delivery start

- [x] 0.1 Run `agent-process start_change commit-plan-and-ticks --planner Claude --implementer Claude` for tracking issue 252. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/commit-plan-and-ticks`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there
- [x] 0.2 The released `start_change` of 0.1 predates D1 and leaves the plan untracked: tick 0.1 and this task, then `git add openspec/changes/commit-plan-and-ticks` and `git commit -m "chore: plan commit-plan-and-ticks"` — the commit D1 makes the script's. Verify `git status --porcelain` is empty

## 1. RED first

- [x] 1.1 Fake (D1): `tests/publisher/delivery_fakes.py` `Gh` answers `git -C <path> add …` and `git -C <path> commit …` with `""` when no `git_runner` is given. Verify `python -m pytest tests/publisher/test_start_change.py -q` still passes
- [x] 1.2 `tests/publisher/test_start_change.py` (spec *A change is carried in its own worktree*, D1): `_clone` sets `user.name`/`user.email` in the clone's config, so every real-git test's worktree can commit; new `test_plan_committed` on `_clone` — after `start_change`, `git -C <worktree> status --porcelain` is empty, `git -C <worktree> show HEAD:openspec/changes/v2-9-example/tasks.md` has `- [x] 0.1`, and `git -C <worktree> rev-list --count origin/v2-9-example..HEAD` is `1`; `test_tasks_of_a_new_change_start` asserts the `git -C <worktree> commit` call sits between `git worktree add` and the Status edit; `test_worktree_step_fails_after_branch_exists` asserts the continuation names the commit between `then move` and `set_status.py`; a new case in `test_interrupted_start_names_the_continuation` fails on `git -C … commit` and asserts the continuation starts with the commit and still names `set_status.py` and `gh issue comment 7`
- [x] 1.3 `tests/publisher/test_pr_delivery.py` (spec *`archive_change` archives the change before its PR*, D2): new `test_ticks_left_for_the_archive` in a real `git init` repository whose change `tasks.md` is committed then ticked, with a `run` that uses `archive_change._runner` except for `npx` (moves the change dir under `openspec/changes/archive/`) and `git push` (no-op) — exit 0, `git status --porcelain` empty, the archived `tasks.md` at `HEAD` carries the tick; then with the tick uncommitted and `other.txt` modified, exit 2, stderr names `other.txt`, and no commit is added; then with that `tasks.md` deleted and nothing else changed, exit 2, stderr names it, and no commit is added
- [x] 1.4 `tests/publisher/test_planning_workflow.py` (spec *RED first for behavioural changes*, D3): new `test_group_commits_carry_their_ticks` — the Group 0 item names the script's tick and plan commit, the Group 1 item of `SKILL.md#tasks` names the plan commit and the Group 1 ticks in the RED commit, the implementation-groups item names the ticks in the group's commit, the Verify item names the archive commit, and `SKILL.md#delivery` names the change's own `tasks.md` as the one tolerated change
- [x] 1.5 Run `agent-process check_red tests/publisher/test_start_change.py::test_plan_committed tests/publisher/test_start_change.py::test_tasks_of_a_new_change_start tests/publisher/test_start_change.py::test_worktree_step_fails_after_branch_exists tests/publisher/test_start_change.py::test_interrupted_start_names_the_continuation tests/publisher/test_pr_delivery.py::test_ticks_left_for_the_archive tests/publisher/test_planning_workflow.py::test_group_commits_carry_their_ticks` and verify each fails in its body. Commit with the Group 1 ticks as `test(implementation): the process commits the plan and the ticks`

## 2. Scripts

- [x] 2.1 `skills/agent-process/scripts/archive_change.py` (D1, D2): `_mark_own_task` becomes public `mark_own_task(tasks, script, change)` matching `<script>(?:\.py)? <change>`; the clean check drops only a ` M`/`M `/`MM` line whose path is `openspec/changes/<change>/tasks.md` and prints the rest; the docstring states both. Verify `python -m pytest tests/publisher/test_pr_delivery.py -q` passes
- [x] 2.2 `skills/agent-process/scripts/start_change.py` (D1): after the move, `mark_own_task(target / "tasks.md", "start_change", change)`, then `git -C <worktree> add openspec/changes/<change>` and `git -C <worktree> commit -m "chore: plan <change>"`, a step of `left` between the move and `set_status` that names the tick, the add and the commit; the docstring and the `ok:` line name the plan commit. Verify `python -m pytest tests/publisher/test_start_change.py -q` passes. Commit with the group's ticks as `fix(implementation): start_change commits the plan, archive_change carries the ticks`

## 3. Skill

- [x] 3.1 `skills/agent-process/SKILL.md` (D3): Group 0 says the script ticks its task and commits the plan; Group 1 commits RED with the Group 1 ticks; implementation groups end with a commit that carries their ticks; Verify's ticks ride in the archive commit; Delivery starts from a worktree clean but for the change's own `tasks.md`. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` passes. Commit with the group's ticks as `docs(implementation): the skill names the commit of every tick`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [ ] 5.1 With the Verify ticks the only uncommitted change, run `python skills/agent-process/scripts/archive_change.py commit-plan-and-ticks` — this branch's script, which carries D2. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits the ticks with the archive, pushes, and leaves `git status --porcelain` empty
- [ ] 5.2 Run `gh pr create --title "fix: commit-plan-and-ticks" --body-file <report>`. The report references the tracking issue plainly (#252), never with `Closes`, and carries the scenario → test map and the observations of proposal — Why
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Behavioural change → `tests/publisher/test_check_red.py` (the failing test, unchanged); the plan commit and the Group 1 ticks → `tests/publisher/test_planning_workflow.py::test_group_commits_carry_their_ticks`
- `implementation` / Runner given, Configuration that cuts the run, No quality command declared, Run leaves the tree clean → `tests/publisher/test_check_red.py` (unchanged)
- `implementation` / Archive commit, Stale archive lock → `tests/publisher/test_pr_delivery.py::test_archive_commit` (unchanged)
- `implementation` / Ticks left for the archive → `tests/publisher/test_pr_delivery.py::test_ticks_left_for_the_archive`
- `implementation` / Plan committed → `tests/publisher/test_start_change.py::test_plan_committed`, `tests/publisher/test_start_change.py::test_tasks_of_a_new_change_start`
- `implementation` / Worktree step fails after the branch exists → `tests/publisher/test_start_change.py::test_worktree_step_fails_after_branch_exists`, `tests/publisher/test_start_change.py::test_interrupted_start_names_the_continuation`
- `implementation` / Merged change's worktree, Started from inside the previous change's worktree, Cleanup fails, Parallel changes, Worktree listing fails → `tests/publisher/test_start_change.py` (unchanged tests of the same names)
