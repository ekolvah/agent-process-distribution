## Context

See proposal.md — Why for the observations. `init` copies and links the template Project
(`project-copy`, `project-link`), then prints `manual` rows from `manual.rows`, whose guard
(`skills/agent-process/scripts/manual.py:282`) is true when the linked Project's `Area` options
equal the template's or it has no `Area` field — so also when the linked Project is the
template, as in this repository. A step whose state a `manual` row also reads takes it from a
public reader of `manual.py` (`manual.pre_push` → `_pre_push_step`, `manual.readings` →
`readings_setup.steps`).

## Goals / Non-Goals

**Goals:** one `init` transition replacing the copied `Area` options and area views from
`--area`, completed by a retry with the same flags.

**Non-Goals:** visibility (issue 492) and the built-in workflows (no API); keeping area views
in step with options a person later edits in the UI.

## Decisions

**D1 — The areas come from `--area`.** The agent running Install picks them from the
repository's content, as it picks an issue's area. The guard already shows when the work is
done, so the input is needed once and nothing persists it.
*Alternatives:* a declared list in a consumer file (e.g. the `openspec/config.yaml` block) —
rejected: a new managed input with its own validation for a one-time choice; areas derived
from `openspec/specs/` capabilities — rejected: a fresh install has none; keep the row manual —
rejected by the person.
Failure modes of the caller-supplied input: wrong or misspelt names reach the Project. Catcher:
the dry-run's `planned project-areas` line names the given and the dropped options, and
Install step 2 shows the whole dry-run before `--confirm`. No proof is lost: the row still
prints while the options are the template's.

**D2 — One read, three states.** `manual.QUERY` gains the Project id, the `Area` field id and
the views (`id name filter`); a public `manual.areas(t) -> Areas` returns them with a state:
`template` (options equal the template's, Project not the template), `own` (options differ,
or the linked Project is the template), `none` (no `Area` field). The row prints for
`template`, naming `--area`, and for `none`, naming only the UI; the step is `planned` for
`template`, `unchanged` for `own` and `none`. With no linked Project yet — `_run` already
holds `linked` — the step is `planned` against "the copy", its dropped options read from the
template half of `manual.QUERY`. An unreadable state gives no step, as in `_pre_push_step`; its row
says why. No state is a `conflict`, so the step can never stop the installation PR.

**D3 — GraphQL mutations, not REST or `gh project`.** `gh project` has `field-create` and
`field-delete` but no option edit and no view command (`gh project --help`, gh 2.87.3). The
GraphQL mutations work by node id for user- and org-owned Projects and were run live. REST
creates a view with its filter in one call, but by an owner-typed path and not run live; D4
makes GraphQL's create-then-filter safe to retry.

**D4 — Views by name, options last.** The apply re-reads `manual.areas`, raises `InstallError`
unless the state is still `template`, then for each given name in order: the view of that name
gets the filter; else an unused view named after a dropped template option is renamed with the
filter in one `updateProjectV2View`, keeping its fields; else one is created and then filtered. The views named
after a template option that remain are deleted. Last, one `updateProjectV2Field` sets exactly
the given names (`color: GRAY`, `description: ""`). Every write goes through
`target.gh_write`, its error prefixed with the step label as `readings_setup.gh_step` does.
Options last keeps the state `template` until every view write succeeded (§III), and views are
found by name, so the same command completes a failed run with no second view.
*Alternatives:* options first, as issue 493 suggests — rejected: a failed view write would
leave the state `own` and the views stranded; batching the view writes as aliased mutations —
rejected: a handful of calls once per install.

**D5 — The step sits in `init.py` after `pre-push`, before task-readings,** beside
`_pre_push_step`: as ADR 0048 D3, a failed Project write cannot stop the installation PR.

## Risks / Trade-offs

- [Options not given are dropped, and items holding them lose their `Area` value] → only while
  the options are still the template's; the dry-run line names the dropped options.
- [A given area named `Open`, `Bugs` or `Empty` takes over that view's filter] → accepted; the
  dry-run line names the views it changes.
- [A created view, needed only past the template's five areas, shows neither `Labels` nor
  `Area`] → accepted; renaming covers the common case (proposal Why).
- [A run under the agent identity cannot write the person's Project] → Install runs `init` as
  the person, before `agent-identity`.

## Migration Plan

None: an installed consumer still on the template's options gets the step on its next
`init --area`. Rollback: revert; the Project keeps what was written.
