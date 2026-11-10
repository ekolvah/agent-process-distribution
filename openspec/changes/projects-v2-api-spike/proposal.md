## Why

Tracking issue 486 asks whether the GitHub Projects v2 API now enables a built-in workflow,
replaces a single-select field's options, and creates or edits views — the work of the
`manual project-workflows` and `manual project-areas` rows
(`skills/agent-process/scripts/manual.py:107`, `:110`), which `init` prints because the code assumes
these are UI-only. If an API exists, a row can become an `init` transition.

Observations (gh 2.87.3, 2026-11-10):

- `gh api graphql -f query='{__schema{mutationType{fields{name}}}}'` lists, among the
  `ProjectV2` mutations, `updateProjectV2Field`, `createProjectV2View`,
  `updateProjectV2View`, `deleteProjectV2View` and `deleteProjectV2Workflow`, and no
  mutation that creates, enables or updates a workflow.
- `__type(name:"ProjectV2Workflow")` has the fields `createdAt enabled fullDatabaseId id
  name number project updatedAt`; nothing configures it.
- `UpdateProjectV2FieldInput.singleSelectOptions`: "provided values overwrite existing
  options, and existing options should be…" included to keep them;
  `ProjectV2SingleSelectFieldOptionInput.id`: "Include this to preserve the option's identity
  during updates, preventing item field values from" being lost.
- `CreateProjectV2ViewInput` takes `projectId name layout configuration`
  (`configuration` is `visibleFieldIds` only); `UpdateProjectV2ViewInput` adds `filter`.
  Project 4's area views (`user(login:"ekolvah"){projectV2(number:4){views(first:20){nodes{name
  layout filter groupByFields(first:3){…}}}}}`) are `BOARD_LAYOUT` with a filter such as
  `-status:Done area:"Observability"` and no `groupByFields`, so name, layout and filter
  reproduce them.
- `UpdateProjectV2Input` has `public: Boolean`, "Set the project to public or private".
- Using the built-in automations
  (https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations):
  "To save your changes and enable the workflow, click **Save and turn on workflow**." — UI
  steps only; the page names no API. The REST Projects reference
  (https://docs.github.com/en/rest/projects) has groups for drafts, fields, items, projects
  and views — "Create a view for a user-owned project" — and no workflow endpoint and no
  field-option update.

Answer: built-in workflows — no API; `Area` options — GraphQL `updateProjectV2Field`;
views — GraphQL `createProjectV2View` / `updateProjectV2View` / `deleteProjectV2View` and
REST create.

## What Changes

- The `WORKFLOWS` comment of `manual.py` records that enabling a built-in workflow is UI
  only, with the documentation link: the read the row rests on states the reason it stays a
  row. Issue 486 names "the row's design" and "no code"; a comment is the row's design
  closest to its reader (design D1), and nothing executes differently.
- One follow-up issue: `init` replaces the `Area` options and the area views, turning the
  `project-areas` row into a transition; its body carries the mutations above.
- No behaviour change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (`skip_specs: true`): the `distribution` requirement "Project UI actions are printed,
not performed" changes in the follow-up, not here.

## Standard approach

GitHub's schema introspection and the GraphQL Projects reference
(https://docs.github.com/en/graphql/reference/projects), with the two pages under Why.

## Impact

- Edited: `skills/agent-process/scripts/manual.py` (comment only).
- Remote: one new issue in this repository, added to the linked Project with its `Area`.
- Not edited: ADR 0027 (design D2).
