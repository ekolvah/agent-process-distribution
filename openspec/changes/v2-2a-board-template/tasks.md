## 0. Delivery start

- [x] 0.1 `grep -q "^approve" openspec/changes/v2-2a-board-template/architect-review.md` exits 0 (on `rework`: apply the findings, re-review, no delivery task runs)
- [x] 0.2 The tracking issue exists (#129, priority High — no prompt): `git fetch origin && git checkout main && git pull` → `gh issue develop -c 129 --name v2-2a-board-template`; verify `git branch --show-current` prints the change name
- [x] 0.3 `python .agent-process/scripts/set_status.py 129 "In Progress"` exits 0 (priority High is already set on #129)
- [x] 0.4 Provenance: `gh issue comment 129 --body "planner: Claude; implementer: <this carrier>"`

## 1. RED first

- [x] 1.1 `tests/publisher/test_delivery_scripts.py`: `_Gh` answers `["gh", "repo", "view"]` with `{"owner": {"login": "owner"}, "name": "repo", "projectsV2": {"Nodes": self.projects}}` (the observed capital `Nodes`), `["gh", "issue", "view"]` with `{"url": "https://github.com/owner/repo/issues/7"}`, and raises on `["gh", "api", "graphql"]`; drop its `items` parameter. `test_tracking_issue_created` stays as is (two edits, ids as before) and additionally asserts no call starts with `gh api`. New `test_priority_only` — `set_status.main(["7", "--priority", "High"], gh=gh)` makes exactly one `item-edit` with `F_PRIO`/`P_HIGH`, and `set_status.main(["7"], gh=gh)` exits 2 with no edit. New `test_several_linked_projects` — `_Gh(projects=[_PROJECT, {"id": "PVT_2", "number": 5, "title": "Other"}])` → `main(["7", "In Progress"])` exits 2, no edit, stderr names `#4 Board` and `#5 Other`; the same with `projects=[]` exits 2. Delete `test_issue_in_unlinked_project` and `test_same_titled_unlinked_project` (design decision 1). Run `python -m pytest --junitxml=.pytest-report.xml tests/publisher/test_delivery_scripts.py`; verify `python .agent-process/scripts/check_red.py --report .pytest-report.xml tests/publisher/test_delivery_scripts.py::test_tracking_issue_created tests/publisher/test_delivery_scripts.py::test_priority_only tests/publisher/test_delivery_scripts.py::test_several_linked_projects` exits 0
- [x] 1.2 `tests/publisher/test_planning_workflow.py`: new `test_plan_approved` — in `rules.tasks` of `openspec/config.yaml` the entry containing `architect-review.md` (the review entry) has `approve` before `"Planned"`, contains `gh issue create` and `--priority`; the entry containing `Group 0` contains neither `gh issue create` nor `priority`; `test_tasks_of_a_new_change` keeps its assertions (they hold on the new text). Run `python -m pytest --junitxml=.pytest-report.xml tests/publisher/test_planning_workflow.py`; verify `check_red --report .pytest-report.xml tests/publisher/test_planning_workflow.py::test_plan_approved` exits 0
- [x] 1.3 Commit `test(v2-2a): RED for set_status on the linked Project and Planned at approve` before any implementation

## 2. set_status keeps two transitions

- [ ] 2.1 `.agent-process/scripts/set_status.py`: delete `_LOOKUP_QUERY`, `_lookup`, `_project_for`; `_repo(gh)` returns `(owner, name, projects)` from `gh repo view --json owner,name,projectsV2` reading `Nodes` or `nodes`; `_linked_project(owner, name, projects)` returns the single Project or raises `ValueError` listing `#<number> <title>` of each (or `none linked`); `_issue_url(gh, number)` from `gh issue view <N> --json url`; `set_status(number, status=None, *, priority=None, gh)` builds `writes` from the given fields only and raises `ValueError` when both are `None`; `main`: `status` positional with `nargs="?"`, the usage line and docstring show `<N> ["<Status>"] [--priority "<Priority>"]` and name the two statuses the process writes, the ok line prints only what was set. Verify `python -m pytest tests/publisher/test_delivery_scripts.py -q` green; commit `feat(v2-2a): set_status writes on the linked Project, Status optional`

## 3. Planned at the end of the propose run

- [ ] 3.1 `openspec/config.yaml` `rules.tasks` (design decision 6): Group 0 becomes `the verdict … → gh issue develop -c <N> --name <change> from fresh origin/main (the tracking issue is the one the propose run left in Planned) → python .agent-process/scripts/set_status.py <N> "In Progress" → provenance …` (no `gh issue create`, no priority); the architect-review entry gains, after `the propose run ends on \`approve\``: `— then the tracking issue: when the change has none, ask the person for its priority (High/Medium/Low) and gh issue create --title "<change>" --body-file openspec/changes/<change>/proposal.md; python .agent-process/scripts/set_status.py <N> "Planned" --priority "<the answer>" (Todo → Planned on the board), and only then report the artifacts ready.` `context` line 24–26 says the run ends with the review and the issue in `Planned`. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` green and `npx -y @fission-ai/openspec@1.13.0 instructions tasks --change v2-2a-board-template --json` carries the new text; commit `feat(v2-2a): the propose run ends with the tracking issue in Planned`

## 4. Project #4 is the template

- [ ] 4.1 Observation (design decision 4), after the person confirms each remote write: `gh auth status` shows the `project` scope (else print `gh auth refresh -s project` and stop); `gh project copy 4 --source-owner ekolvah --target-owner @me --title scratch --format json` → note `number`; `gh api graphql` on the copy's id: `public`, `fields(first:30){nodes{... on ProjectV2SingleSelectField{name options{name}} ... on ProjectV2Field{name}}}`, `views(first:10){nodes{name layout}}`, `workflows(first:20){nodes{name enabled}}`; `gh project delete <number> --owner @me`; verify `gh project list --owner @me` no longer lists `scratch`. Keep the query output for 5.1
- [ ] 4.2 Before the person's edits, read Project #4 with the same query (`node(id:"PVT_kwHOApeba84Bhf2x")`) and keep the output. The person, in the Project UI (design decision 5): set visibility public; enable *Auto-add to project* for `ekolvah/agent-process-distribution` with the filter `is:issue,pr is:open`; enable *Item reopened → Todo*; confirm *Item added → Todo*, *Item closed → Done*, *Pull request merged → Done* are on. Then re-read and verify: `public` true; `Status` options exactly `Todo`, `Planned`, `In Progress`, `Done`; `Priority` options `High`, `Medium`, `Low`; `workflows` lists `Auto-add to project`, `Item added to project`, `Item reopened`, `Item closed`, `Pull request merged` all `enabled: true`

## 5. Rules and docs follow

- [ ] 5.1 `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md` (append only, design decision 7): a paragraph `Observations from v2-2a (\`v2-2a-board-template\`, #129):` with bullets — what the copy of 4.1 carried (fields, options, views, workflows) and what it lacked, the before/after of Project #4 from 4.2 (visibility and enabled workflows), `gh repo view --json projectsV2` returning `Nodes`, `markProjectV2AsTemplate` being organization-only, the *Pull request linked to issue* workflow as a native `In Progress` at PR time, not at delivery start (the `set_status` deletion condition is not met), and the owner's decision to keep `Planned` as the queue column written at the end of the propose run (reversing the v2-1 "marker only after an incident" note on the ground of visibility, not gating). `.claude/rules/workflow.md`: the issue-creation line becomes `python .agent-process/scripts/set_status.py <N> --priority <High|Medium|Low>` (Todo comes from the Project) and one sentence: the propose run creates the tracking issue of a change and leaves it in `Planned`. `agent-process.md`: the issue contract shows `<N> ["<Status>"] [--priority <name>]`; the planning paragraph says the propose run ends with the issue in `Planned`; governance item 4 writes `--priority` only, item 5 says the process writes `Planned` and `In Progress`, the Project's workflows `Todo` and `Done`. Verify `python -m pytest tests/agent_process -q` green; commit `docs(v2-2a): the Project writes Todo and Done, the process Planned and In Progress`

## 6. Verify

- [ ] 6.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py` exit 0

## 7. Deliver

- [ ] 7.1 `git status --short` empty (commit what is left) → `python .agent-process/scripts/archive_change.py v2-2a-board-template` exits 0: the archive commit is pushed and is the head the PR opens on
- [ ] 7.2 `gh pr create --title "v2-2a-board-template" --body-file <report>` — the report names the tracking issue as a plain reference (#129, no `Closes`), Why / What, the scenario → test map below, the deferred scope (`init` copy/link and checklist → #112; v1 board scripts and the installation guide → #115); ends with the Claude Code footer
- [ ] 7.3 `python .agent-process/scripts/request_codex_review.py --request <PR>` (re-run after every push)
- [ ] 7.4 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread, push, re-request, at most three rounds; the fourth leaves the rest to the person with a reply. The person merges — the merge is the first observation of *Pull request merged → Done* on #129 (`gh issue view 129 --json projectItems`). No tick after 7.1 (the PR is the record); a run interrupted here resumes with `gh pr view v2-2a-board-template`

## Scenario → test map

- state / Template read → n/a: GitHub state, read by the query of task 4.2 and recorded in ADR 0027 (tests run offline)
- state / Linking an existing Project → n/a: unchanged behaviour (kept in the MODIFIED block); the options are read in task 4.2
- state / Issue closed → n/a: GitHub's workflow; observed on #129 at the merge of this PR (task 7.4)
- state / Tracking issue created → `tests/publisher/test_delivery_scripts.py::test_tracking_issue_created`
- state / Priority asked once → n/a: a step of the `tasks` rule's review entry, asserted by `tests/publisher/test_planning_workflow.py::test_plan_approved` (`--priority` in the review entry, none in Group 0)
- state / Priority field drift → `tests/publisher/test_delivery_scripts.py::test_priority_field_drift` (existing)
- state / Priority only → `tests/publisher/test_delivery_scripts.py::test_priority_only`
- state / Several linked Projects → `tests/publisher/test_delivery_scripts.py::test_several_linked_projects`
- planning / Review finding → `tests/publisher/test_planning_workflow.py::test_review_finding` (existing)
- planning / Rework verdict → `tests/publisher/test_planning_workflow.py::test_rework_verdict` (existing)
- planning / Plan approved → `tests/publisher/test_planning_workflow.py::test_plan_approved`
- planning / Review archives with the change → `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change` (existing)
- implementation / Tasks of a new change → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (existing; `test_plan_approved` adds the Group 0 assertion)
