## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py quality-checks-per-job --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 204. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `tests/agent_process/test_ci_check.py::test_list_prints_the_registry`: monkeypatch `CHECKS` with two recording fakes, set `sys.argv` to `["ci_check.py", "--list"]`, call `main()`; assert `json.loads` of the captured stdout equals the two names in order and no fake was called. Run `python skills/agent-process/scripts/check_red.py tests/agent_process/test_ci_check.py::test_list_prints_the_registry` and verify it fails in the test body (argparse rejects `--list`)
- [x] 1.2 In `tests/publisher/test_reusable_workflows.py` rewrite `test_quality_callee_runs_the_callers_commands` for D1: inputs `setup` (optional, default `""`), `test` (required), `checks` (optional, default `""`); the permissions are unchanged; jobs are exactly `link`, `plan`, `check`, `quality`; `link`'s only step equals the `reusable-quality.yml` link step; `plan` runs `${{ inputs.checks }}` only when it is set, validates with `jq -e` for a non-empty array of names matching `^[A-Za-z0-9._-]+$`, and writes `[""]` without it; `check` needs `plan`, takes its matrix from `fromJSON(needs.plan.outputs.checks)`, is named `${{ matrix.check || 'test' }}`, passes `CHECK: ${{ matrix.check }}` through `env`, and runs `setup` under `if: inputs.setup != ''`, then `${{ inputs.test }} ${CHECK:+--only "$CHECK"}`. No step has `continue-on-error`. Add `test_quality_gate_requires_every_job` (D3): `check` has `strategy.fail-fast` `false`; `quality` needs exactly `[link, plan, check]`, has `if: always()`, and has one step whose `env` passes `${{ toJSON(needs) }}` and whose `run` is a `jq -e` requiring every `.result == "success"`. In `test_publisher_caller_reaches_callee_by_same_commit_path` expect `checks: python .agent-process/scripts/ci_check.py --list` in `with`. Run `python skills/agent-process/scripts/check_red.py` on the three node ids and verify each fails in the test body; commit 1.1 and 1.2 as `test: quality checks run as jobs behind a gate`

## 2. Listing (D4)

- [x] 2.1 Add `--list` to `ci_check.py`'s parser (mutually exclusive with `--only`), which prints `json.dumps(list(CHECKS))` and returns before `run_selected`. Update the module docstring's usage lines. Verify `python -m pytest tests/agent_process/test_ci_check.py -q` passes and `python .agent-process/scripts/ci_check.py --list` prints the nine names; commit as `feat(ci_check): list the check registry`

## 3. Callee and caller (D1–D3)

- [x] 3.1 Rewrite `.github/workflows/quality.yml` per D1–D3 and add `checks: python .agent-process/scripts/ci_check.py --list` to `.github/workflows/agent-process.yml`. Keep the header comments true, including the one saying `run:` interpolates only the caller's literal commands. Verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes; commit as `feat(quality): run each check as its own job behind the quality gate`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py`, and verify both pass
- [x] 4.2 After the PR is created (task 5.2) and before requesting review, observe the live run. Run `gh pr checks <PR>` and verify it lists `agent-process / link`, `agent-process / plan`, one `agent-process / <name>` per name of `ci_check.py --list`, and `agent-process / quality`, all passing. If the legs report under another name (for example `agent-process / check (lint)`), stop and report the observed names to the person: the goal of the change rests on that name. Then push a temporary commit that fails only `format` (one unformatted line in a test file). Verify with `gh run view <run> --json jobs` that `format` failed, every other check job concluded `success`, and `quality` failed, and that its log shows `needs.check.result` as `failure`. Revert that commit with a new commit and verify all checks pass again. Keep both run URLs for the PR report. If `quality` passed on the failing leg, stop and report to the person: D3's reading of the matrix aggregate is wrong

## 5. Deliver

- [x] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py quality-checks-per-job`. Verify that it archives the two deltas into `openspec/specs/`, commits, and pushes the branch
- [x] 5.2 Run `gh pr create --title "feat: quality-checks-per-job" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`) and carries the scenario → test map and the two run URLs of task 4.2. Then do task 4.2
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Consumer test fails → `tests/publisher/test_reusable_workflows.py::test_quality_callee_runs_the_callers_commands` (without `checks`, one job runs `test`, with no `continue-on-error`) and `::test_quality_gate_requires_every_job` (the gate fails unless every job succeeded)
- `distribution` / One check fails → `tests/publisher/test_reusable_workflows.py::test_quality_gate_requires_every_job` (`fail-fast: false`, success-only gate); the matrix aggregate is platform behaviour, observed by task 4.2
- `distribution` / Listing fails → `tests/publisher/test_reusable_workflows.py::test_quality_callee_runs_the_callers_commands` (`jq -e` non-empty validation in `plan`) and `::test_quality_gate_requires_every_job` (`if: always()`, so a failed `plan` fails the gate)
- `distribution` / PR weakens its own driver → `tests/publisher/test_reusable_workflows.py::test_publisher_driver_keeps_a_same_head_catcher` (unchanged)
- `distribution` / Quality runs once per PR → `tests/publisher/test_reusable_workflows.py::test_quality_runs_once_per_pr` (unchanged: only `agent-process` calls the callee) and `::test_quality_callee_runs_the_callers_commands` (the matrix comes only from `plan`'s listing, and there is one leg per name)
- `implementation` / List → `tests/agent_process/test_ci_check.py::test_list_prints_the_registry`
