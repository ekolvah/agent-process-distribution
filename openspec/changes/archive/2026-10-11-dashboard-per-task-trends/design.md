## Context

Dashboard `aqxk4q` is at version 8. It has three live rows keyed by `task_id`, and the
*Recorded readings* row from `record-task-readings` (its design D1). Every trend panel in
that row is an Infinity CSV query with points and `timeFrom: 180d`.

The setup document never named `aqxk4q`, although `record-task-readings` relied on it for a
rebuild. So nothing pointed ADR 0038 and ADR 0039 at the panels they made stale.

**Observed:** a `POST /api/ds/query` on that Infinity source, with the columns
`merged_at:timestamp`, `compactions:number` and `cost_usd:number`, returns `null` for the
empty cells of PRs 390, 392 and 397, and `4` and `16.7782` for PR 401. A missing reading is
a gap in the trend, not a 0.

## Goals / Non-Goals

**Goals:** every issue-99 reading of every new task can be read per task and as a trend
across tasks on `aqxk4q`. No panel shows a verdict that cannot be true.

**Non-Goals:**

- Live views of a task in flight. The setup document's *Per-task metrics* queries run in
  Explore.
- Cause analysis: cost by model, source or tool, and cache share. That is per-turn
  inspection in Langfuse (ADR 0036).
- Re-recording PRs 390, 392 and 397, whose gaps are true.
- Keeping the dashboard JSON in git.

## Decisions

### D1. *Recorded readings* is the per-task view

There are six trend panels, three per row, `w: 8`:

| Panel | Series |
|---|---|
| Recorded cost per task (exists) | `cost_usd` |
| Recorded hours to merge and lines changed (edited) | `hours` (unit `h`); `lines` on the right axis, unit `short` |
| Recorded plan review rounds (exists) | `plan_rounds` |
| Recorded code review rounds (exists) | `code_rounds` |
| Recorded failed and denied calls (new) | `failed`, `denied`, legend shown |
| Recorded compactions (new) | `compactions` |

Issue 99 reads hours *beside* size. Two series in one panel show that pairing. A derived
ratio would be empty whenever either reading is a gap.

The table's `organize` transform is removed. It repeats the CSV header order by hand, and
still lists the columns that ADR 0038 retired. Without it, the table follows the header.

### D2. The live rows are removed

The live rows are *Per-task telemetry*, *Rule 1*, *Rule 2*, *Over time* and *Causes*,
together with the variables `$task` and `$attempt`. They key on `task_id`, which no session
carries after ADR 0039, and ADR 0038 dropped rule 1.

Rule 2, the Grafana-versus-Langfuse token comparison, is read from the setup document's
*Per-session totals* query in Explore, for the ids of a change's `sessions` file.

Rejected: keying them by session through a `sessions` column in the CSV. Their data lasts
the 14 days of Prometheus retention, and they would repeat the recorded trends.

### D3. Pointers

- **Text panel.** It says that every panel reads the CSV and that a task appears after its
  merge. It links `#which-labels-carry-the-task` for a task's Langfuse traces and
  `#per-session-totals` for rule 2.
- **Description.** It links `#per-task-readings`.
- **Setup document.** Its *Recorded readings* paragraph, under the CSV column table, names
  `aqxk4q` and says that the dashboard reads those columns and nothing else. It does not list
  the panels, a copy of host state that would drift. A column change then meets the dashboard
  in the same section.

## Risks / Trade-offs

- [A CSV column is renamed and its panel shows `null`, which reads as a true gap] → D3 puts
  the dashboard next to the column table that a rename edits.
- [Removing panels loses their JSON] → Restore version 8 from Grafana's version history,
  within its retention. **Observed:** `GET /api/dashboards/uid/aqxk4q/versions` listed
  versions 1–8 on 2026-10-11. The PR report records the version number.
