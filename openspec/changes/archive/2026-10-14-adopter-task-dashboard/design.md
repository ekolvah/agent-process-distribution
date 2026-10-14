## Context

`aqxk4q` is at version 23 in folder `ffuyoy5etplvkd` (2026-10-14). It has a text panel and 7
data panels: six trends and a table. Each data panel holds one Infinity query with the URL
hard-coded. The Infinity observations are in proposal.md, Why.

## Goals / Non-Goals

**Goals:** one mechanism covers all four setups of the issue. A list of one repository gives
1a and 2a, and a longer list gives 1b and 2b. `aqxk4q` becomes the owner's 1a instance for
this repository.

**Non-Goals:**

- Private repositories, and other owners' repositories. Raw CSV reads without a token answer
  404 for a private repository. Nothing checks the owner.
- A repository switcher, or one trend series per repository. The trends of a combined
  dashboard run over all its tasks by `merged_at`.
- Keeping each instance's JSON in git. The template is the only copy here.

## Decisions

### D1 — A plugin script renders the template for a list of repositories

`agent-process dashboard <owner/name>...` reads `templates/per-task-dashboard.json` and
prints the dashboard. The person saves the output and imports it. Grafana's *Import
dashboards* page, step 4: "(Optional) Change the dashboard name, folder, or UID"; step 5:
"Select a data source, if required".

The standard is a Grafana import with `__inputs`. It is used for the datasource (D2), but it
cannot list repositories: an input substitutes a string and cannot add queries.

- Alternative: a multi-value dashboard variable in the URL. Rejected. An Infinity query
  fetches one URL, so the variable selects one repository and acts as a switcher, which the
  issue rules out.
- Alternative: import for one repository, then duplicate the query by hand for each further
  one. Rejected: it takes two edits per repository, a URL and a literal, kept in step.
- Alternative: the Grafana Foundation SDK. Rejected. It adds a runtime dependency to the
  plugin environment to emit one JSON file.

The arguments are checked against `^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$`, and a mismatch exits 2
(§VI). The script defines its own templates path rather than importing `init.py`.
`init.py`'s `_template` cannot render this file: `string.Template` rejects
`${__data.fields.repository}`, and it would replace `${DS_INFINITY}`.

### D2 — The template is `aqxk4q`, with prototype queries and an input

The template is the live JSON of `aqxk4q` version 23, with these changes:

- `__inputs` declares `DS_INFINITY` (type `datasource`, plugin
  `yesoreyeram-infinity-datasource`), and every datasource reference is `${DS_INFINITY}`.
- `uid`, `id` and `version` are removed, so an import creates a dashboard unless the person
  sets a UID.
- Each data panel keeps its one query as the prototype, copied whole. The query's URL and its
  `repository` literal carry the token `__REPOSITORY__`. A query without `filters` and
  `url_options` failed in the panel while `/api/ds/query` answered it.
- Each data panel starts its transformations with `merge`. The table's `organize` places
  `repository` after `task_id`.
- The description names the listed repositories' CSVs, and its link to the setup document is
  an absolute URL like the text panel's: an adopter has no `.agent-process/`, so
  `test_package_paths_resolve_in_a_consumer` flags only paths that are not URLs.

The script replaces each prototype with one copy per repository, with refIds `A`, `B` and so
on and the token replaced. It sets the title to `Per-task delivery: <a>, <b>`, so two
instances in one folder differ in title.

- Alternative: only the table queries Infinity, and the trend panels read its results through
  the `-- Dashboard --` datasource, so a refresh fetches each CSV once instead of 7 times.
  Rejected. The issue does not ask for it, its reads are not observed, and each CSV column a
  trend uses would have to be typed in the table's query.

### D3 — `repository` and the issue link are Infinity computed columns

Each query gets the computed column `'<owner/name>'` as `repository`; the table's query also
gets `replace(task_id, 'issue-', '')` as `issue`. A field override on `task_id` links to
`https://github.com/${__data.fields.repository}/issues/${__data.fields.issue}`, and `issue` is
hidden.

Observed on 2026-10-14 in a scratch import of this design (deleted afterwards). It used two
queries on this repository's CSV, with `repository` `ekolvah/agent-process-distribution` and
`ekolvah/second-probe`:

- `merge` on two queries showed every row twice, once per `repository` value.
- `merge` on one query showed the rows as before.
- The trend panel with `merge` before its transforms rendered its series and trend.
- A link whose title repeats its URL resolved to `https://github.com/ekolvah/second-probe/issues/101`
  while `issue` was hidden.

- Alternative: `task_readings.py` writes `repository` and `issue` into the CSV. Rejected. It
  changes the measurement row and the recording workflow, and the rows already recorded would
  need a backfill.

A misspelled repository, a private one, or one with no `task-readings` branch yet answers 404.
Only that query fails (observed through `/api/ds/query`), so the panel shows its error beside
the other repositories' rows (§IV).

### D4 — The `manual task-readings` row names the render and the import

The row appends: `then agent-process dashboard <owner/repo> > per-task.json (list further
repositories for one combined dashboard) and import it in that stack's Grafana (Dashboards →
New → Import), choosing its Infinity datasource`. `init` cannot read the person's Grafana. A
row of its own would have no observable done state, which *Manual rows follow observed state*
needs, so the import rides with the credentials of the same stack.

- Alternative: a `manual dashboard` row that is always printed. Rejected, because it would
  break *Observed done*.
- Alternative: the row only points at the setup document. Rejected: scope item 2 of the issue
  wants the rows themselves to say how.
- Consequence: an adopter whose credentials are already set does not see the row. The setup
  document's *Adopters* section carries the same steps.

### D5 — `aqxk4q` is re-imported from the render

The re-import renders for `ekolvah/agent-process-distribution` and sets `uid` to `aqxk4q`.
It then sends `POST /api/dashboards/import` with `overwrite: true`, `folderUid`
`ffuyoy5etplvkd`, and the input `DS_INFINITY` = `grafanacloud-infinity`. In the scratch
import, this call substituted `grafanacloud-infinity` into every reference. Its response
carried `uid` and `imported` but no version, and the overwrite saved version 2 into the
history.

## Risks / Trade-offs

- [Someone edits the live dashboard, and the template drifts from `aqxk4q`] → `aqxk4q` is now
  a render. An edit goes into the template and is re-imported, and the setup document says so.
  The re-import runs after the last change to the template or `dashboard.py`.
- Rollback: revert the PR, and restore `aqxk4q` from its version history to the version that
  task 6.1 records.

## Confirmation

These steps happen after the release, once ekolvah/kinozal_scraper has recorded its first
task. The owner imports the render for `ekolvah/kinozal_scraper`. Its table must show
kinozal's rows, with `task_id` opening the kinozal issue, and `aqxk4q` must still show only
this repository's rows. The owner then imports the render for both repositories, and its
table must hold the rows of both. The delivery PR cannot prove them, and its merge closes the
tracking issue. So task 7.1 opens an issue in ekolvah/kinozal_scraper that holds these steps
together with its first recorded task. The gap that ekolvah/kinozal_scraper#642 accepted ends
when they pass.
