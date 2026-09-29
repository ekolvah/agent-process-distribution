## 0. Delivery start

- [x] 0.1 Run `agent-process start_change check-red-leaves-no-bytecode --planner Claude --implementer Claude` for tracking issue 250. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/check-red-leaves-no-bytecode`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `test_run_leaves_the_tree_clean` to `tests/publisher/test_check_red.py` per design D2: in `tmp_path`, `git init`, write `pkg/__init__.py`, a failing `tests/test_f.py` importing `pkg`, and `.github/agent-process-quality.json`, no `.gitignore`; commit them with a git identity on the command line, as `tests/agent_process/test_ci_check.py` does (an uncommitted `pkg/` would collapse to `?? pkg/` and hide the bytecode); `monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)`, `chdir` there, run `check_red.main(["tests/test_f.py::test_f"])` (RED: returns without `SystemExit`), then assert `git status --porcelain` is empty. Amend the module docstring: the fakes cover the configuration, one live test covers what the run leaves in the tree
- [x] 1.2 Run `agent-process check_red tests/publisher/test_check_red.py::test_run_leaves_the_tree_clean` and verify it fails on the porcelain assertion, naming `pkg/__pycache__/`. Commit as `test(implementation): check_red leaves the tree clean`

## 2. Gate

- [x] 2.1 `skills/agent-process/scripts/check_red.py` (D1): pass `env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}` to the pytest `subprocess.run`, with a comment naming issue 250 and why the variable rather than `-B`; add the bytecode switch to the module docstring's configuration sentence. Verify `python -m pytest tests/publisher/test_check_red.py -q` passes. Commit as `fix(implementation): check_red leaves no bytecode in the worktree`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change check-red-leaves-no-bytecode`. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: check-red-leaves-no-bytecode" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#250), carries the scenario → test map, the reproduction of proposal — Why, and the non-goal of design (the consumer's own `test` command)
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Run leaves the tree clean → `tests/publisher/test_check_red.py::test_run_leaves_the_tree_clean`
- `implementation` / Behavioural change, Runner given, Configuration that cuts the run, No quality command declared → unchanged: `tests/publisher/test_check_red.py::test_behavioural_change`, `::test_interrupted_run_is_no_verdict`, `::test_refuses_without_quality_declaration`
