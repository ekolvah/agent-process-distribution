## 0. Delivery

- [ ] 0.1 Tracking issue exists (#111, priority set). `gh issue develop -c 111 --name v2-1-planning-workflow`
  from fresh `origin/main`; `python .agent-process/scripts/set_issue_status.py 111 in-progress`;
  verify `git branch --show-current` prints the change name.

## 1. RED

- [ ] 1.1 `tests/publisher/test_planning_workflow.py` with the six tests of the scenario → test
  map below (`test_roles_and_carriers`, `test_behavioural_change`, `test_tracking_issue_created`,
  `test_priority_field_drift`, `test_pending_review`, `test_archive_commit`) and the
  `schema validate agent-process` case in `tests/publisher/test_openspec_valid.py`; verify
  `python .agent-process/scripts/check_red.py tests/publisher/test_planning_workflow.py tests/publisher/test_openspec_valid.py`
  exits 0 (v1 mode); commit.

## 2. OpenSpec configuration

- [ ] 2.1 `npx -y @fission-ai/openspec@latest schema fork spec-driven agent-process`; insert
  `architect-review` between `design` and `tasks`; verify `openspec schema validate agent-process` green.
- [ ] 2.2 `openspec/config.yaml`: `schema: agent-process`; `rules:` — `proposal` (bug:
  reproduction + root cause before design), `tasks` (delivery template: tracking issue with
  priority → `gh issue develop -c` → `set_status "In progress"` → RED first with `check_red` →
  … → `ci_check` → `gh pr create` → `request_codex_review.py --request <PR>` (v1, until `v2-4`)
  → `wait_for_pr` → apply threads, at most three rounds → `finish_change <change>`; scenario →
  named test or `n/a: <reason>`), `architect-review` (principles §I–VII; an unmapped scenario is
  a finding); verify `openspec instructions tasks --change v2-1-planning-workflow --json` shows the rule.
- [ ] 2.3 Write `openspec/changes/v2-1-planning-workflow/architect-review.md` (self-review
  against principles §I–VII; unmapped scenarios as findings); verify
  `openspec status --change v2-1-planning-workflow` shows 5/5 artifacts and
  `openspec validate --strict --all` green.
- [ ] 2.4 Measure `openspec instructions proposal --change v2-1-planning-workflow --json` byte
  size with the current `context` and with principles §I–VII appended; verify both numbers are
  noted for task 5.3.

## 3. Scripts and agent

- [ ] 3.1 `.agent-process/scripts/set_status.py <N> "<Status>" [--priority "<name>"]` per
  `design.md` (project by item or by linked Project, names → ids, `item-add` when absent, exit 2
  on unknown option or several Projects, helpers duplicated on purpose — docstring); verify
  `test_tracking_issue_created` and `test_priority_field_drift` green.
- [ ] 3.2 `.agent-process/scripts/wait_for_pr.py <PR> [--timeout SECONDS]` per `design.md`
  (checks concluded → threads; exit 0/1/3, default 30 min); verify `test_pending_review` green.
- [ ] 3.3 `.agent-process/scripts/finish_change.py <change>`: lock check (exit 2) → mark its own
  task → `openspec archive <change> -y` → remove the leftover lock → commit → push →
  `request_codex_review.py --request <PR>` when present (say so when not) → `wait_for_pr`;
  verify `test_archive_commit` green.
- [ ] 3.4 `.agent-process/scripts/check_red.py --report <junit.xml> <node ids>`: parse the
  report, spawn nothing, v1 CLI unchanged; `AGENTS.md` declares the runner command and the
  report path; verify `test_behavioural_change` and `tests/agent_process/test_ci_check.py` green.
- [ ] 3.5 Rewrite `agents/architect-reviewer.md`: writes `architect-review.md` from
  `openspec instructions architect-review --change <name> --json`; no issue sections; verify
  `git grep -n "issue section\|validate_issue" agents/` is empty.

## 4. Remove v1 planning

- [ ] 4.1 `git rm -r commands/plan.md commands/implement.md agents/discovery.md
  .agents/skills/plan-issue .agents/skills/implement-issue .agents/orchestration/change-classes.yaml
  .agent-process/scripts/validate_issue_sections.py .agent-process/scripts/capture_external_fixture.py
  .agent-process/scripts/check_fixture_ratchet.py tests/agent_process/test_validate_issue_status.py`;
  give `tests/agent_process/test_adr_records.py` its own `## ` section parser; verify
  `python -m pytest tests/agent_process/test_adr_records.py -q` green and `test_roles_and_carriers` green.
- [ ] 4.2 `.agent-process/docs/architecture/agent-process.md`: delete §Discovery runbook,
  §Planner runbook, §Architect review contract, the evidence-capture table and the
  planner/implementer steps of §Deterministic delivery flow; one paragraph points at `openspec/`
  and the `tasks` rule. `principles.md` §V: "reproduction is a step of planning; the `proposal`
  rule in `openspec/config.yaml` says what it records"; retarget its links to the removed
  anchors. `AGENTS.md` (`$plan-issue`/`$implement-issue` → `$openspec-propose`/`$openspec-apply-change`),
  `.claude/rules/workflow.md` (`/plan` → `/opsx:propose`, `/implement` → `/opsx:apply`); verify
  `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py tests/agent_process/test_doc_headers.py -q` green.

## 5. ADRs

- [ ] 5.1 Lock root cause: `openspec init` in a scratch directory, one change, `archive -y`,
  inspect `openspec/changes/archive/`; verify the observation (lock after success, or only after
  an abort; upstream issue link if a bug) is written into task 5.3's text.
- [ ] 5.2 ADR 0009: `status: superseded by ADR-0027`; its `#discovery-runbook` link retargeted
  to ADR 0027; verify `python -m pytest tests/agent_process/test_adr_records.py tests/agent_process/test_doc_links.py -q` green.
- [ ] 5.3 ADR 0027 §More Information "Observations from v2-1": answers to the seven open
  questions of the tracking issue (#111; "not observable here" where so; private-repo auto-close → #117), the lock
  root cause (5.1), the instruction-size numbers (2.4), Claude ran with `wait_for_pr` as the
  only end guard (ADR 0021 superseded in practice); verify `test_adr_records.py` green.

## 6. Verify

- [ ] 6.1 `npx -y @fission-ai/openspec@latest validate --strict --all` green.
- [ ] 6.2 `python .agent-process/scripts/ci_check.py` green; verify
  `git grep -l "template/" -- $(git diff --name-only origin/main)` is empty.

## 7. Deliver

- [ ] 7.1 Push; `gh pr create --body-file <report>` (change name, `Closes #111`, the scenario →
  test map, deferrals: Codex end-to-end run → `v2-2`, private-repo auto-close → #117);
  `python .agent-process/scripts/request_codex_review.py --request <PR>`; verify `gh pr view` shows the PR.
- [ ] 7.2 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread,
  push, re-request the Codex review, repeat — at most three rounds; the fourth leaves the rest
  to the person with a reply; verify `wait_for_pr` exits 0.
- [ ] 7.3 `python .agent-process/scripts/finish_change.py v2-1-planning-workflow` — marks this
  task, `openspec archive v2-1-planning-workflow -y`, commit, push, `wait_for_pr` on that head;
  verify `openspec/specs/{roles,planning}/spec.md` exist and no `.openspec-archive.lock` is
  tracked. The person merges.

## Scenario → test map

- Procedure changes once, Label change → `test_roles_and_carriers`
- Behavioural change → `test_behavioural_change`
- Tracking issue created → `test_tracking_issue_created`
- Priority field drift → `test_priority_field_drift`
- Pending review → `test_pending_review`
- Archive commit, Stale archive lock, Behaviour change → `test_archive_commit`
- Codex plans a change, Reading provenance, Switching agents, New task, Ambiguous scope, Review
  finding, Validator scope, Bug change, Unmapped scenario → `n/a: person or agent behaviour, not a script`
- Merge → `n/a: observed on this PR, recorded in ADR 0027`
