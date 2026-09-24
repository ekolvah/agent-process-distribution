## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-4a-review-protection --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 172. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 In `tests/publisher/test_activate_protection.py`, let `FakeGh` answer the preflight's GraphQL read with or without `.github/workflows/agent-review.yml`, and a check run per context (design D3). Add the following tests:
  - `test_review_caller_present`: both contexts are green, and the planned body requires both, each with its run's `app.id`.
  - `test_review_context_not_observed`: the caller is present and `agent-review / agent-review` is absent, failed, or from another app. The test expects exit 2, the observed runs named, and reads only.
  - A `test_read_back_mismatch` case where the read-back lacks or adds a context.
  - `test_read_back_reordered`: the read-back returns the two contexts reversed and the run passes; a rerun against that live ruleset prints `unchanged`.
- [x] 1.2 Move `TestPrePushHook` from `tests/agent_process/test_branch_protection.py` to the new `tests/agent_process/test_pre_push_hook.py`, dropping its three probe tests (design D6). Add `test_push_runs_ci_check_alone`: the recorded calls are exactly one, `ci_check.py`
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py` with the node ids of 1.1 and 1.2. Verify that it exits 0 with each new test RED, then commit as `test(review-and-merge): RED for one ruleset protection`

## 2. Activation requires both contexts

- [x] 2.1 Implement design D3 in `skills/agent-process/scripts/activate_protection.py`:
  - The preflight's GraphQL read also asks for `HEAD:.github/workflows/agent-review.yml`.
  - A pure `contexts(review_caller: bool)` returns the list.
  - The preflight checks each context's run and returns `(context, integration)` pairs.
  - `desired` builds `required_status_checks` from the pairs.
  - `read_back` and `owned_fields` compare the list sorted by context.
  - In `skills/agent-process/templates/ruleset.json`, `required_status_checks` becomes one `"__REQUIRED_CHECKS__"` placeholder that `desired` fills with the list.
  - Update the module docstring.

  Verify that `python -m pytest tests/publisher/test_activate_protection.py -q` is green
- [x] 2.2 In `skills/agent-process/SKILL.md` Install step 5, say that the run requires `agent-review / agent-review` too when the repository has that caller. Verify with `python -m pytest tests/publisher -q -k "skill or install"`, then commit Group 2 as `feat(distribution): activation requires the review context when its caller exists`

## 3. No classic protection

- [x] 3.1 Delete `.agent-process/scripts/check_branch_protection.py`, `.agent-process/scripts/install_branch_protection.py` and `tests/agent_process/test_branch_protection.py`. Remove the probe `if`/`else` from `.agent-process/.githooks/pre-push`, so the hook runs `ci_check.py` alone (design D4). Verify that `python -m pytest tests/agent_process/test_pre_push_hook.py -q` is green
- [x] 3.2 Rewrite `tests/publisher/test_reusable_workflows.py::test_publisher_driver_keeps_a_same_head_catcher` so that it no longer imports `REQUIRED_CONTEXTS`. It asserts that `.github/workflows/agent-review.yml` exists and that `activate_protection.contexts(True)` includes `agent-review / agent-review`. Verify that the test is green
- [x] 3.3 In `.agent-process/docs/architecture/agent-process-installation.md`, replace the `install_branch_protection.py` step with `activate_protection.py`. Verify that `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py -q` is green, then commit Group 3 as `refactor(review-and-merge): drop classic protection scripts and the pre-push probe`

## 4. No review gate, no Stop gate

- [x] 4.1 Delete `.agent-process/scripts/review_gate.py` and `tests/agent_process/test_review_gate.py` (design D1). Also remove:
  - the `.review_gate_stamp` line from `.gitignore`;
  - the review-gate verdict line from `.github/pull_request_template.md`;
  - the `review_gate.py` sentence from the `.agent-process/scripts/gh_io.py` docstring.

  Verify that `git grep -n review_gate -- ':!openspec/changes' ':!**/adr/**'` prints only `roles.yaml` and `test_agent_orchestrator.py`, which issue 115 owns
- [x] 4.2 Delete `.agent-process/scripts/delivery_state.py` and `tests/publisher/test_delivery_state.py`, and remove the Stop gate (design D2):
  - the `stop` subcommand, `stop_response` and the stamp and budget helpers in `hooks.py`;
  - the `stop` branch in `codex_hooks.py`;
  - the `Stop` entries in `.claude/settings.json` and `.codex/hooks.json`;
  - `.agent_stop_blocks` in `.gitignore`;
  - the Stop tests in `tests/publisher/test_hooks.py` and `tests/publisher/test_codex_hooks.py`, and the Stop assertions in `tests/agent_process/test_delivery_gate_wiring.py`.

  Verify that `git grep -n -i "delivery_state\|stop_response" -- ':!openspec/changes' ':!**/adr/**'` is empty and `python -m pytest tests -q` is green
- [x] 4.3 Remove `--request` from `.agent-process/scripts/request_codex_review.py` and its tests in `tests/publisher/test_request_codex_review.py` (design D5). In `skills/agent-process/SKILL.md` Delivery:
  - replace the `request_codex_review.py --request` command with `gh pr comment <PR> --body "@codex review"`;
  - replace "Run the repository review gate … `ready-for-human`" with stopping once `wait_for_pr.py` settles a head with no open `P0`/`P1` thread, or at the three-round escalation.

  In `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change`, assert `@codex review` in place of `request_codex_review.py`, and drop `ready-for-human`. Verify that `python -m pytest tests/publisher -q` is green
- [x] 4.4 In `.agent-process/docs/architecture/agent-process.md`:
  - replace `request_codex_review.py --request` with `gh pr comment <PR> --body "@codex review"`;
  - replace the `review_gate.py` step with `wait_for_pr.py`;
  - delete the terminal-state paragraph and `### Review-gate verdicts`.

  In `openspec/specs/implementation/spec.md`, drop the Purpose clause about ending a turn. Add one Observations bullet to ADR 0027 with the proposal's two observations (the branch predicate and the protection reads). Verify that `python -m pytest tests/agent_process -q` is green, then commit Group 4 as `refactor(implementation): drop the review gate and the Stop gate`

## 5. Verify

- [x] 5.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 5.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 6. Deliver

- [ ] 6.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py v2-4a-review-protection`. Verify that it applies the `review-and-merge`, `implementation` and `distribution` deltas, commits the archive, and pushes the branch
- [ ] 6.2 Run `gh pr create --title "v2-4a-review-protection" --body-file <report>`. The report references tracking issue 172 and issue 114 without `Closes`. It carries the scenario → test map and the design's Migration Plan, and names `v2-4b` and issue 115 as excluded ownership
- [ ] 6.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, hand the design's Migration Plan to the person, who runs steps 1–3. Paste the step-3 dry-run output (`unchanged`, `classic: none (not written)`) into the PR body, and report the PR ready

## Scenario → test map

- `distribution / Caller absent` → `tests/publisher/test_activate_protection.py::test_caller_absent`
- `distribution / Context not observed` → `tests/publisher/test_activate_protection.py::test_context_not_observed`
- `distribution / Review caller present` → `tests/publisher/test_activate_protection.py::test_review_caller_present`
- `distribution / Review context not observed` → `tests/publisher/test_activate_protection.py::test_review_context_not_observed`
- `distribution / Read-back mismatch` → `tests/publisher/test_activate_protection.py::test_read_back_mismatch`
- `distribution / Read-back reorders contexts` → `tests/publisher/test_activate_protection.py::test_read_back_reordered`
- `review-and-merge / Push reads no protection` → `tests/agent_process/test_pre_push_hook.py::TestPrePushHook::test_push_runs_ci_check_alone`
- `implementation / Push` → `tests/agent_process/test_pre_push_hook.py::TestPrePushHook::test_push_runs_ci_check_alone`
