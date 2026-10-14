---
status: "accepted"
date: 2026-10-14
decision-makers: ekolvah
---

# The per-task dashboard renders for a list of repositories

## Context and Problem Statement

Dashboard `aqxk4q` existed only in the owner's Grafana, with this repository's CSV URL in
every panel. An adopter recording its own readings
([ADR 0041](0041-adopters-record-task-readings-in-their-own-stack.md)) had no dashboard, and
a person with several repositories could not see all their tasks in one table. Both a
per-project and a combined dashboard must be possible, without a repository switcher. An
Infinity query fetches one URL.

## Considered Options

* A plugin script renders a template for a list of repositories
* A multi-value dashboard variable in the CSV URL
* Import for one repository, then duplicate each panel's query by hand per further repository
* The Grafana Foundation SDK

## Decision Outcome

Chosen: **a plugin script renders a template for a list of repositories**.
`agent-process dashboard <owner/name>...` reads `templates/per-task-dashboard.json`, whose
data panels each hold one prototype query, and prints the dashboard with one query per
repository, each adding a `repository` computed column, merged in the panel. The Infinity
datasource is the import input `DS_INFINITY`. In the table, `task_id` links to
`https://github.com/<repository>/issues/<N>`. `aqxk4q` is the render for this repository,
re-imported over its UID.

* A variable selects one repository per view: a switcher, which is ruled out.
* Hand duplication takes two edits per repository and panel, a URL and a literal, in step.
* The SDK adds a runtime dependency to the plugin environment to emit one JSON file.

### Consequences

* Good, because one template serves the per-project and the combined dashboard, for the owner
  and for an adopter.
* Bad, because `aqxk4q` is no longer edited in Grafana: an edit goes into the template and is
  re-imported, or the next import drops it.
* Bad, because only public repositories render rows: the raw CSV read carries no token, and a
  private repository's query fails with 404.
* Bad, because a combined dashboard's trends run over all its tasks, with no series per
  repository.

### Confirmation

`tests/publisher/test_dashboard.py` holds the render, and
`tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` the
`manual task-readings` row that names it. Live: `aqxk4q` re-imported from the render shows
this repository's rows; after the release, a render for an adopter and a combined render
show that adopter's rows with links to its issues.

### Deletion condition

Replace the script with a plain import if Infinity or Grafana gains one query over several
URLs that adds each URL's repository to its rows.
