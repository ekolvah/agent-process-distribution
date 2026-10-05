## 0. Delivery start

- [x] 0.1 Run `agent-process start_change bare-openspec-runs-pin --planner Claude --implementer Claude` for tracking issue 343. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/bare-openspec-runs-pin`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [ ] 1.1 In `tests/publisher/test_plugin.py`, add `test_bare_openspec_runs_the_pin` (design D5): inside the test body (not a fixture, so a missing file is a failure, not an error), copy `bin/openspec` into a temporary plugin `bin/`, put a fake `npx` printing `[%s]` per argument and exiting 3 first on `PATH`, run `sh -c "openspec a 'b c'"`; assert rc 3 and output `[-y][@fission-ai/openspec@<init.OPENSPEC>][a][b c]`
- [ ] 1.2 In the same file, add `test_openspec_pin_has_one_copy` (design D5): over `git ls-files` outside `openspec/changes/`, every match of the version regex is in `bin/openspec` and equals `init.OPENSPEC`, and `bin/openspec` has one; the failure names each offending file
- [ ] 1.3 Run `agent-process check_red "tests/publisher/test_plugin.py::test_bare_openspec_runs_the_pin" "tests/publisher/test_plugin.py::test_openspec_pin_has_one_copy"`. Verify that both fail in their bodies (no `bin/openspec`; `SKILL.md`, `archive_change.py`, `openspec_cli.py` named). Commit as `test(distribution): bare openspec runs the pin`

## 2. Launcher and one pin

- [ ] 2.1 Add `bin/openspec` (D1) with a header comment like `bin/agent-process`'s, and run `git update-index --add --chmod=+x bin/openspec`; extend `test_launcher_is_executable_in_git` to both launchers. Verify that `python -m pytest tests/publisher/test_plugin.py -q -k "bare_openspec or executable"` passes
- [ ] 2.2 In `archive_change.py`, import `OPENSPEC` from `init` and run `npx -y @fission-ai/openspec@{OPENSPEC} archive` (D2, D3); in `tests/publisher/openspec_cli.py` and `test_init_config.py`, take the pin from `load_init().OPENSPEC`. Verify that `python -m pytest tests/publisher/test_pr_delivery.py tests/publisher/test_init_config.py tests/publisher/test_openspec_valid.py -q` passes
- [ ] 2.3 In `skills/agent-process/SKILL.md`, print `openspec validate --strict --all` (Tasks, Verify) and `openspec new change <name>` (Delivery), and fold `openspec` into the existing launcher sentence (lines 10–12), e.g. "`agent-process` … and `openspec`, at the pinned version, are the plugin's launchers on the Bash tool's `PATH`" — no new sentence (D4). Verify that `python -m pytest tests/publisher/test_plugin.py -q` passes. Commit as `fix(distribution): bare openspec runs the pin`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change bare-openspec-runs-pin`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: bare-openspec-runs-pin" --body-file <report>`. The report references the tracking issue plainly (#343), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Bare command → `tests/publisher/test_plugin.py::test_bare_openspec_runs_the_pin`
- `distribution` / One pin → `tests/publisher/test_plugin.py::test_openspec_pin_has_one_copy`
