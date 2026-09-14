## 0. Delivery

- [x] 0.1 Tracking issue exists, priority set (#111); branch `v2-1b-planning-schema` on top
  of `v2-1a-delivery-scripts`; provenance line already on the issue.

## 1. RED

- [x] 1.1 (RED history in PR 121) `tests/publisher/test_planning_workflow.py::test_roles_and_carriers` (schema
  artifact order, `config.yaml` schema and rule keys) and
  `tests/publisher/test_openspec_valid.py::test_forked_schema_validates`; verify
  `python .agent-process/scripts/check_red.py --report .pytest-report.xml <both ids>` exits 0;
  commit.

## 2. OpenSpec configuration

- [x] 2.1 `openspec/schemas/agent-process/` (fork of `spec-driven` plus `architect-review`),
  `openspec/config.yaml` (`schema: agent-process`, `rules:` proposal / architect-review /
  tasks, the tracking issue as a plain reference in the PR body), this change's
  `architect-review.md`; dry-run the `tasks` rule against every scenario of the deltas —
  this file is the result; verify the two tests green and
  `openspec instructions tasks --change v2-1b-planning-schema --json` shows the rule; commit.
- [x] 2.2 Rewrite `agents/architect-reviewer.md`: writes `architect-review.md` from
  `openspec instructions architect-review --change <name> --json`; no issue sections; verify
  `git grep -n "issue section\|validate_issue" agents/architect-reviewer.md` is empty; commit.

## 2a. Review round 1 (PR 123)

- [x] 2a.1 `architect-review` after `tasks`, `apply` requires both; the review instruction
  and `agents/architect-reviewer.md` read the task list; verify `test_review_finding`.
- [x] 2a.2 Group 1 rule: `no RED: <reason>` when the map names no test; verify
  `test_review_finding`.
- [x] 2a.3 `@fission-ai/openspec@1.13.0` in `config.yaml` and `agents/architect-reviewer.md`;
  verify `test_pinned_openspec`.

## 2b. Review round 2 (PR 123)

- [x] 2b.1 `apply` instruction and Group 0 stop on a `rework` verdict; the `architect-review`
  rule names the re-review loop; verify `test_review_finding`.
- [x] 2b.2 `agents/architect-reviewer.md` passes `--store <id>`; verify
  `test_reviewer_keeps_the_store`.
- [x] 2b.3 Part 1 merged into this branch; `test_pinned_openspec` covers `finish_change.py`.

## 2c. Review round 3 (PR 123)

- [x] 2c.1 One planning home: the `context` of `config.yaml` rules registered stores out and
  `agents/architect-reviewer.md` drops `--store` (the Group 0 check and `finish_change.py`
  read the repository of the PR); verify `test_one_planning_home`.

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` green.
- [x] 3.2 `python .agent-process/scripts/ci_check.py` green.

## 4. Deliver

- [x] 4.1 `git status --short` empty; push (output to a file);
  `gh pr create --base v2-1a-delivery-scripts --title v2-1b-planning-schema --body-file <report>`
  (change name, part 2 of 3 of #111, the scenario → test map, deferrals);
  `python .agent-process/scripts/request_codex_review.py --request <PR>`; verify `gh pr view`
  shows the PR.
- [x] 4.2 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread,
  push, re-request, at most three rounds; verify exit 0 (three rounds applied; the round-4
  thread — ticks of the Deliver group left uncommitted before `finish_change` — is left to
  the person with a reply).
- [ ] 4.3 `python .agent-process/scripts/finish_change.py v2-1b-planning-schema`; verify
  `openspec/specs/{roles,planning}/spec.md` exist and no `.openspec-archive.lock` is tracked.
  The person merges.

## Scenario → test map

- Procedure changes once, Tasks of a new change → `test_roles_and_carriers`
- Review finding, Rework verdict → `test_review_finding`
- Tracking issue created, Priority field drift → `test_tracking_issue_created`,
  `test_priority_field_drift` (part 1)
- Priority asked once → `n/a: person and planner behaviour; the rule text`
- Codex plans a change, Reading provenance, Switching agents, New task, Ambiguous scope,
  Validator scope, Bug change, Unmapped scenario → `n/a: person or agent
  behaviour, not a script`
- Behaviour change → `n/a: finish_change (part 1); observed on this PR`
