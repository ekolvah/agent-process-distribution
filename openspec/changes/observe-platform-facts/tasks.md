## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/observe-platform-facts/architect-review.md` exits 0 (on `rework`: apply the findings, re-review, no delivery task runs) and `gh issue view 138 --json projectItems --jq '.projectItems[0].status.name'` prints `Planned`; otherwise print `propose run not finished: run its tail (the Architect review entry of this rule) first` and stop — nothing is asked and nothing is created here
- [x] 0.2 Branch: `git fetch origin && git checkout main && git pull` → `gh issue develop -c 138 --name observe-platform-facts`; verify `git branch --show-current` prints the change name
- [x] 0.3 `python .agent-process/scripts/set_status.py 138 "In Progress"` exits 0 (priority High is already set on the issue)
- [x] 0.4 Provenance: `gh issue comment 138 --body "planner: Claude; implementer: <this carrier>"` (Claude or Codex)

## 1. RED first

- [x] 1.1 `tests/publisher/test_planning_workflow.py`: add `test_design_on_a_platform_behaviour` (the `proposal` rule joined: `"platform behaviour"`, `"the observation, not the inference"`, `"reference page"`, `"run id"`, `"pointed at, not repeated"` in it, and `"before the proposal"`) and `test_asserted_platform_fact` (the `tasks` rule joined: `"asserted, not observed"` in it, after `"is a finding"`); run `python -m pytest --junitxml=.pytest-report.xml tests/publisher/test_planning_workflow.py -q`, verify `python .agent-process/scripts/check_red.py --report .pytest-report.xml tests/publisher/test_planning_workflow.py::test_design_on_a_platform_behaviour tests/publisher/test_planning_workflow.py::test_asserted_platform_fact` exits 0; commit `test(planning): RED for the observed-platform-fact rule and its finding`

## 2. The proposal rule names the observation (D1)

- [x] 2.1 `openspec/config.yaml`, `rules.proposal`: a fourth bullet — `A design that rests on a platform behaviour (an event, a permission, a merge rule, a token scope, a CLI flag) verifies it on the platform before the proposal is written and records the observation, not the inference, under **Why** or in design.md beside the decision: the reference page (URL and the sentence) or the run id / command and its output — a run of a standard checker counts; a listing, a name or an inference from another behaviour does not; an observation already on record (an ADR entry, an archived change) is pointed at, not repeated.` Verify `python -m pytest tests/publisher/test_planning_workflow.py -q -k design_on_a_platform_behaviour` green and `npx -y @fission-ai/openspec@1.13.0 instructions proposal --change observe-platform-facts --json` carries `platform behaviour`; commit `feat(planning): the proposal rule records the observation of a platform fact`

## 3. The architect review has the finding (D2)

- [ ] 3.1 `openspec/config.yaml`, `rules.tasks`, Architect review entry: after `and so is a Group 1 that names no test without a `no RED: <reason>` task` add `, and a platform behaviour a design rests on that is asserted, not observed (no reference page, run id or command output beside it)`. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` green (the new test and `test_review_finding`, `test_roles_and_carriers` with it); commit `feat(planning): the architect review finds an asserted platform fact`

## 4. The record (D3, D4)

- [ ] 4.1 `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`: one bullet after the "Re-run on a fallback head" entry — `Platform facts are observed before a design rests on them (issue 138, observe-platform-facts)`: the rule and the finding in one sentence each; the two worked examples point at the entries this ADR already carries (the `pull_request_review_thread` bullet with `397c54f`; the withdrawn-trigger bullet with head `a1d0bad` and run `35262221116`) and add one line each on what would have shown it in minutes — the events reference page; one throwaway run and `gh pr view --json mergeStateStatus,statusCheckRollup`; the exemption for a fact already on record (the `fix-rerun-fallback-head` bullet needed an owner's decision for it); D3 (no new script; the event-set check has nothing left to compare, the workflow-file check is `actionlint`, a separate issue); deletion condition: none, the rule is a sentence of `config.yaml`. Nothing of the two examples is re-narrated. `.agent-process/docs/architecture/agent-process.md`, Planning: the `proposal` rule's summary in parentheses gains `a design on a platform behaviour records its observation`. Verify `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py -q` green (the doc guards: no `#N` as a sentence member); commit `docs(planning): ADR 0027 entry and the Planning section for the observed-platform-fact rule`

## 5. Verify

- [ ] 5.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` valid and `python .agent-process/scripts/ci_check.py` green; `git status --short` shows nothing of this change uncommitted

## 6. Deliver

- [ ] 6.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py observe-platform-facts` (marks its own task, archives, commits, pushes)
- [ ] 6.2 `gh pr create --title "observe-platform-facts" --body-file <report>` — the change name, issue 138 as a plain reference (no `Closes`), Why / What, the scenario → test map below, the deferral: `actionlint` is a separate issue; ends with the Claude Code footer
- [ ] 6.3 `python .agent-process/scripts/request_codex_review.py --request <PR>` after the PR and after every push → `python .agent-process/scripts/wait_for_pr.py <PR>` → apply every unresolved thread, push, re-request, `wait_for_pr.py <PR>` again; a `P0`/`P1` thread the push addressed: `python .agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>` (one thread per rerun cycle, `wait_for_pr.py` between); a `P2`/`P3` thread is answered; a fix that changes a spec goes through a change of its own on the branch; at most three rounds, the fourth leaves the rest to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view observe-platform-facts`

## Scenario → test map

- planning / Design on a platform behaviour → `tests/publisher/test_planning_workflow.py::test_design_on_a_platform_behaviour` (task 1.1: the rule the propose run loads names the trigger, the step and what counts as an observation); the planner's compliance on a given change → n/a: judgement of the propose run, read by the architect review (next scenario)
- planning / Asserted platform fact → `tests/publisher/test_planning_workflow.py::test_asserted_platform_fact` (task 1.1: the Architect review entry names the finding); the reviewer's reading of a given change → n/a: the subagent's judgement, exercised on every propose run, not a script
