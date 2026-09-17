## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/v2-2b-resolve-thread-rule/architect-review.md` exits 0 (on `rework`: apply the findings, re-review, no delivery task runs) and `gh issue view 134 --json projectItems --jq '.projectItems[0].status.name'` prints `Planned`; otherwise print `propose run not finished: run its tail (the Architect review entry of this rule) first` and stop — nothing is asked and nothing is created here
- [x] 0.2 Branch: `git fetch origin && git checkout main && git pull` → `gh issue develop -c 134 --name v2-2b-resolve-thread-rule`; verify `git branch --show-current` prints the change name
- [x] 0.3 `python .agent-process/scripts/set_status.py 134 "In Progress"` exits 0 (priority High is already set on the issue)
- [x] 0.4 Provenance: `gh issue comment 134 --body "planner: Claude; implementer: <this carrier>"` (Claude or Codex)

## 1. RED first

- [x] 1.1 `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (scenario "Blocking thread addressed"): add `assert rule.index("request_codex_review.py") < rule.index("resolve_review_thread.py")` and `assert "BLOCKING" in rule`; run `python -m pytest tests/publisher/test_planning_workflow.py -q --junitxml=reports/junit.xml` (delete `reports/` afterwards — it is not tracked), verify `python .agent-process/scripts/check_red.py --report reports/junit.xml tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` exits 0; commit `test(v2-2b): RED for the resolve step of the Deliver group`

## 2. The Deliver group names the resolve step

- [x] 2.1 `openspec/config.yaml`, `rules.tasks`, Deliver group: after `apply every unresolved thread, push, re-request` insert `— a BLOCKING thread the push addressed is resolved with python .agent-process/scripts/resolve_review_thread.py --repo <owner/repo> --pr <PR> --thread <id> (--list prints the open ones) before the agent-review run on that head reaches its last step; a thread that is not BLOCKING is answered, never resolved by the process —` keeping `repeat at most three rounds` after it. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` green and `npx -y @fission-ai/openspec@1.13.0 instructions tasks --change v2-2b-resolve-thread-rule --json` carries `resolve_review_thread.py`; commit `feat(v2-2b): the Deliver group names resolve_review_thread.py for addressed BLOCKING threads`

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` reports only the pre-existing failure of the untracked `v2-2-delivery` (a change of #112, not of this PR; when it is absent, no failure at all) and `python .agent-process/scripts/ci_check.py` green with that directory set aside; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [ ] 4.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py v2-2b-resolve-thread-rule` (marks its own task, archives, commits, pushes)
- [ ] 4.2 `gh pr create --title "v2-2b-resolve-thread-rule" --body-file <report>` — the report names the tracking issue as a plain reference (#134, no `Closes`), Why / What, the scenario → test map below; ends with the Claude Code footer
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request <PR>` after the PR and after every push → `python .agent-process/scripts/wait_for_pr.py <PR>` → apply every unresolved thread, push, re-request; a BLOCKING thread the push addressed: `python .agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id>`; at most three rounds, the fourth leaves the rest to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view v2-2b-resolve-thread-rule`

## Scenario → test map

- implementation / Tasks of a new change → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (existing)
- implementation / Propose run stopped before its tail → `tests/publisher/test_planning_workflow.py::test_plan_approved` (existing)
- implementation / Blocking thread addressed → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (task 1.1)
