## Context

See proposal.md — Why for the observations. `manual.rows` prints `project-visibility`,
`project-workflows` and `project-areas` from one GraphQL read; the `WORKFLOWS` comment
(`skills/agent-process/scripts/manual.py:18`) says only that the API exposes a workflow's
name and whether it is enabled.

## Goals / Non-Goals

**Goals:** answer issue 486 per item, record the UI-only answer where the next reader of the
row looks, and leave one actionable follow-up for the items the API covers.

**Non-Goals:** any change to `init` or a spec; a live write to a Project (the follow-up's
RED proves the mutations against its fake and its first run against a scratch copy);
the visibility row.

## Decisions

**D1 — The UI-only record is the `WORKFLOWS` comment.** It is the line a reader of the
`project-workflows` row meets, so the reason and the link sit beside the read.
*Alternative:* a new ADR — rejected: a decision with nothing to choose; its deletion
condition ("an enable mutation appears") fits in the comment. *Alternative:* the archived
design of this change alone — rejected: not where the row's reader looks.

**D2 — ADR 0027 is not edited.** Its "Workflows are read-only in the API (… no mutation …)"
is a v2-2a observation dated by its change; `deleteProjectV2Workflow` does not alter what it
decided (the person enables workflows), and an ADR's observations stay as recorded.

**D3 — One follow-up issue for options and views.** Both are the one `project-areas` row,
read by one guard (Area options equal the template's), and each view's filter names an
option, so a views transition cannot run before the options one. Its body names
`updateProjectV2Field` (`singleSelectOptions` overwrite; an option's `id` keeps item values),
`createProjectV2View` (name, layout), `updateProjectV2View` (filter), `deleteProjectV2View`,
the REST "Create a view for a user-owned project", and the open question it must answer
first: `init` has no source for a consumer's areas today. Area `Distribution`.

**D4 — Visibility is not this spike's.** `updateProjectV2(public:)` exists, but the copy's
visibility is the person's choice and nothing in the process needs it public, so the row
is dropped rather than automated: issue 492. Issue 486 does not ask about it.

## Risks / Trade-offs

- Introspection shows a mutation exists, not that a user token may call it on a user-owned
  Project; the follow-up's first live run settles that.
