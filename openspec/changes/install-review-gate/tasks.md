## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py install-review-gate --planner Claude --implementer Claude` for tracking issue 215. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `skills/agent-process/templates/agent-review.yml` as an empty stub, add it to the closed `TEMPLATES` set of `tests/publisher/test_plugin.py`, and `render_review_workflow(version: str) -> str` in `init.py` raising `NotImplementedError`. In `tests/publisher/test_init.py` add `test_review_caller_render`: the rendered text for `CURRENT` starts with the managed marker, parses as YAML, its trigger is exactly `pull_request` with types `[opened, synchronize]`, its one job `agent-review` uses `ekolvah/agent-process-distribution/.github/workflows/reusable-agent-review.yml@v<CURRENT>`, it has no `with` key, the callee declares no required input, its `secrets` keys equal the callee's `workflow_call` secrets in both directions, the secret value is `${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` verbatim, and its permissions are a superset of the callee's. In `tests/publisher/init_harness.py` add `review` to `LABELS` after `workflow` and `.github/workflows/agent-review.yml` to `CONSUMER_FILES`. In `tests/publisher/test_init_remote.py` add `test_review_prerequisites_are_printed` (exactly one `manual review-` row, `manual review-secret: `, naming `CLAUDE_CODE_OAUTH_TOKEN` and the repository's secrets URL, on a dry-run and a confirmed run). In `tests/publisher/test_init_conflicts.py` add the case `.github/workflows/agent-review.yml` = `name: mine\n` → `conflict` naming that path. In `tests/publisher/test_activate_protection.py` make `FakeGh`'s default callers both files and its default `runs` `[_run(), _review_run()]`, make `_rules` and `_served` cover both contexts, have `test_dry_run`, `test_no_ruleset_yet`, `test_live_ruleset_differs`, `test_rerun` and `test_ambiguous_rulesets` expect `[_pair(CONTEXT, 15368), _pair(REVIEW, REVIEW_APP)]`, and add `test_review_caller_absent` (callers `("agent-process",)` → `refused: caller absent on main: .github/workflows/agent-review.yml`, reads only, dry-run and confirm). Run `python skills/agent-process/scripts/check_red.py` with the new node ids plus `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed` and `tests/publisher/test_init.py::test_lifecycle`, and run `python -m pytest tests/publisher/test_plugin.py::test_package_contents_are_closed tests/publisher/test_activate_protection.py -q` and verify it passes except `test_review_caller_absent` (the inverted fixtures stay green on the current script, which returns both contexts when the review caller is present); verify each RED node fails in the test body; commit as `test(distribution): the installer ships the review caller and activation requires it`

## 2. Installer (D1, D2)

- [x] 2.1 Write `templates/agent-review.yml` per D1, each GitHub expression spelled `$${{ ... }}`, and `render_review_workflow` through the unchanged strict `_template`; generalise `_workflow_text` over path and renderer and add `_file_step(ctx, "review", REVIEW_WORKFLOW, ...)` after `workflow`; update the module docstring's step list. Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_conflicts.py tests/publisher/test_init_remote.py::test_installed_footprint_is_closed -q` passes
- [x] 2.2 Per D2, have `_project_steps` return the consumer's `owner/name` beside the URL and add the row to `_manual(url, repo)`. Verify `python -m pytest tests/publisher/test_init_remote.py tests/publisher/test_plugin.py -q` passes, including `test_only_project_writes_remote`. Commit Group 2 as `feat(distribution): install the review caller in every consumer`

## 3. Activation (D3)

- [x] 3.1 In `activate_protection.py` refuse on a null `review` object with the D3 message, drop the parameter of `contexts()`, and update the module docstring. Update `test_reusable_workflows.py::test_publisher_driver_keeps_a_same_head_catcher` to call `contexts()`. Verify `python -m pytest tests/publisher/test_activate_protection.py tests/publisher/test_reusable_workflows.py -q` passes. Commit as `feat(distribution): activation requires the review caller`

## 4. Procedure and record (D2, D3, D5)

- [ ] 4.1 In `skills/agent-process/SKILL.md` Install: step 4 names the review-secret `manual` row; step 5 drops "When the repository has `agent-review.yml`" and states that the PR must show `agent-process / quality` and `agent-review / agent-review` green. Verify `python -m pytest tests/publisher/test_plugin.py -q` passes
- [ ] 4.2 Add `.agent-process/docs/adr/0032-the-review-gate-is-installed-in-every-consumer.md` from `template.md` per D5, Confirmation naming the tests of 1.1. Verify `python .agent-process/scripts/ci_check.py` passes the document guard; commit Group 4 as `docs(distribution): the review gate is part of every install`

## 5. Verify

- [ ] 5.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 5.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 6. Deliver

- [ ] 6.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py install-review-gate`. Verify that it archives the delta into `openspec/specs/`, commits, and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: install-review-gate" --body-file <report>`. The report names tracking issue 215 as a plain reference (never `Closes`), carries the scenario → test map, marks the activation change as breaking, and lists the consumer migration of design.md
- [ ] 6.3 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>` (no `@codex review` request: Codex has left the process), and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Review caller render → `tests/publisher/test_init.py::test_review_caller_render`
- `distribution` / Review prerequisites → `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed`, `::test_only_project_writes_remote`
- `distribution` / Fresh repository → `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed`, `tests/publisher/test_init.py::test_lifecycle`
- `distribution` / Installation of another release → unchanged; `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed`
- `distribution` / Caller absent → `tests/publisher/test_activate_protection.py::test_caller_absent`, `::test_review_caller_absent`
- `distribution` / Context not observed → unchanged; `tests/publisher/test_activate_protection.py::test_context_not_observed`
- `distribution` / Review caller present → unchanged; `tests/publisher/test_activate_protection.py::test_review_caller_present`
- `distribution` / Review context not observed → unchanged; `tests/publisher/test_activate_protection.py::test_review_context_not_observed`
