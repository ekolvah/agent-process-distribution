## Why

The board is the most manual part of installing the process in a consumer: a Project built
by hand with the right `Status` and `Priority` options, a verification of those options,
and a script that moves every status. GitHub already provides two of the four transitions —
`gh project copy` reproduces a Project, and the built-in Project workflows set `Todo` on add
and `Done` on close or merge — so step 2a of #107 (#129) makes Project #4 the template a
consumer copies and leaves the process the two board writes it has no workflow for:
`Planned` when a plan passes its architect review, `In Progress` when the apply starts.
`init` (#112) then copies and links instead of verifying.

`Planned` is kept on the owner's decision (solution review of this plan, 2026-09-16): the
board is the person's view of the queue, and a plan that is written and reviewed but not yet
taken into implementation must be visible as such. That reverses the v2-1 observation in
ADR 0027 ("a marker is added only after a run is observed to apply an unapproved change") on
different grounds — visibility of the queue, not a gate.

Observed on Project #4 today (GraphQL `ProjectV2.workflows`, `fields`, `public`): private;
`Status` = `Todo`, `Planned`, `In Progress`, `Done` (one item in `Planned`: #22); enabled
workflows are *Item added to project*, *Item closed*, *Pull request merged*, *Auto-close
issue*, *Pull request linked to issue*, *Auto-add sub-issues to project*; *Auto-add to
project* and *Item reopened* are not enabled. `gh repo view --json projectsV2` lists the
Projects linked to the repository (id, number, title) without GraphQL.

## What Changes

- **Observation first, recorded in ADR 0027**: `gh project copy 4 --source-owner ekolvah
  --target-owner @me --title scratch`, then one GraphQL read of the copy — which of the
  fields, single-select options, views and built-in workflows arrive; the scratch Project is
  deleted in the same task. Both are remote writes under the person's account and run only
  after their confirmation.
- **Project #4 becomes the template.** Public (a consumer under another owner must be able
  to copy it); `Status` = `Todo`, `Planned`, `In Progress`, `Done` (as today); `Priority` =
  `High`, `Medium`, `Low`; built-in workflows enabled: *Auto-add to project* (open issues
  and PRs of this repository), *Item added → Todo*, *Item reopened → Todo*, *Item closed →
  Done*, *Pull request merged → Done*. The Project UI is the only writer of visibility and
  workflows (no API for workflows); the change verifies the result with one `gh api
  graphql` read and records it.
- **The propose run ends with the tracking issue in `Planned`.** The architect-review entry
  of the `tasks` rule in `openspec/config.yaml` gains its last step: on `approve`, the
  tracking issue exists (when the change has none: ask the person for the priority, `gh
  issue create --title "<change>" --body-file proposal.md`) and `set_status.py <N>
  "Planned" --priority <P>` runs. Group 0 of the apply loses the issue creation and the
  priority: the issue always exists, task 0.3 writes `In Progress` only. `config.yaml` is
  the extension point OpenSpec provides for project rules; no schema is forked and
  `openspec update` keeps it.
- **`set_status.py` keeps the two transitions GitHub has no workflow for.** The Project is
  the single one linked to the repository (`gh repo view --json owner,name,projectsV2`);
  several linked → exit 2 naming them; none → exit 2. The issue's own memberships are no
  longer consulted (`item-add` is idempotent, and *Auto-add* makes every issue an item), so
  the GraphQL lookup, `_project_for` and the two unlinked-Project tests go. The Status
  positional becomes optional: `set_status.py <N> ["<Status>"] [--priority <name>]`, at
  least one of the two — an issue created outside a change gets its `Todo` from the
  Project and only needs `--priority`.
- **Rules and docs follow.** `.claude/rules/workflow.md` and the governance list of
  `agent-process.md` stop writing `Todo`; the `state` spec says which Status the process
  writes and which the Project does; the `planning` and `implementation` specs move the
  issue creation into the propose run; ADR 0027 gets this step's observations appended
  (among them the owner's decision on `Planned`, and that the built-in *Pull request linked
  to issue* workflow is a native `In Progress` trigger — at PR time, not at delivery start).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `state`: `Todo` and `Done` are written by the Project's built-in workflows and the process
  writes `Planned` and `In Progress`; `Planned` is the one option the process adds; the
  Project of the process is the one linked to the repository; `set_status` takes Status or
  Priority or both; Project #4 is the template with the fields and workflows a consumer
  copies.
- `planning`: the propose run ends with the tracking issue created (priority asked) and in
  `Planned`.
- `implementation`: the delivery tasks start from an existing tracking issue; no delivery
  task prompts the person.

## Impact

Edited: `.agent-process/scripts/set_status.py`, `openspec/config.yaml` (`rules.tasks`:
Group 0 and the architect-review entry), `tests/publisher/test_delivery_scripts.py`
(`_Gh` answers `gh repo view`/`gh issue view`; `test_tracking_issue_created` adapted;
`test_priority_only`, `test_several_linked_projects` added; `test_issue_in_unlinked_project`,
`test_same_titled_unlinked_project` deleted), `tests/publisher/test_planning_workflow.py`
(`test_plan_approved` added), `openspec/specs/{state,planning,implementation}/spec.md`
(via archive), `.claude/rules/workflow.md`, `.agent-process/docs/architecture/agent-process.md`
(issue contract, governance items 4–5, the planning paragraph), `.agent-process/docs/adr/0027-…md`
(observations of this step, appended after the apply).

Remote (GitHub, not files): Project #4 visibility and built-in workflows; a scratch Project
created and deleted for the observation.

Removed: nothing on disk.

Dependencies: none new (`gh` 2.87 with the `project` scope, already required).

Out of scope: `init` copying and linking the Project and printing the workflow checklist
(#112); the v1 scripts `bootstrap_github_project.py`, `set_issue_status.py`,
`set_issue_priority.py`, `project_settings.py` and `agent-process-installation.md` (deleted
in #115); the consumer's own board (#117).
