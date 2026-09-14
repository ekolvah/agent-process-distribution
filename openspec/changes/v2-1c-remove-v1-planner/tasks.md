## 0. Delivery

- [x] 0.1 Tracking issue exists, priority set (#111); branch `v2-1c-remove-v1-planner` on top
  of `v2-1b-planning-schema`; provenance line already on the issue.

## 1. RED

- [x] 1.1 `tests/publisher/test_planning_workflow.py::test_label_change` (no v1 entry point
  exists); verify `python .agent-process/scripts/check_red.py --report .pytest-report.xml
  tests/publisher/test_planning_workflow.py::test_label_change` exits 0; commit.

## 2. Removal

- [x] 2.1 `git rm` the v1 entry points listed under **Impact**; `test_adr_records.py`
  parses MADR sections with `markdown-it`; verify `test_label_change` and
  `tests/agent_process` green; commit.
- [ ] 2.2 Docs: `agent-process.md` planning section (schema order tasks → architect review,
  the `tasks` rule as the delivery flow, roles table without discovery), `principles.md`,
  `workflow.md`, `AGENTS.md`, `roles.yaml` anchors; ADR 0009 superseded by ADR 0027, whose
  observations record the split; verify `test_doc_links`, `test_doc_narrative`,
  `test_adr_records`, `test_agent_orchestrator` green; commit.

## 3. Verify

- [ ] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` green.
- [ ] 3.2 `python .agent-process/scripts/ci_check.py` green.

## 4. Deliver

- [ ] 4.1 `git status --short` empty; push (output to a file);
  `gh pr create --base v2-1b-planning-schema --title v2-1c-remove-v1-planner --body-file <report>`
  (change name, part 3 of 3 of #111, the scenario → test map, deferrals);
  `python .agent-process/scripts/request_codex_review.py --request <PR>`; verify `gh pr view`
  shows the PR.
- [ ] 4.2 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread,
  push, re-request, at most three rounds; verify exit 0.
- [ ] 4.3 `git merge v2-1b-planning-schema` once part 2 is archived, then
  `python .agent-process/scripts/finish_change.py v2-1c-remove-v1-planner`; verify
  `openspec/specs/planning/spec.md` carries the requirement and no `.openspec-archive.lock`
  is tracked. The person merges.

## Scenario → test map

- Label change → `test_label_change`
