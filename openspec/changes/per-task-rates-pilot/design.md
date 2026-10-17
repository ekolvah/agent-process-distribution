## Context

Panels 22 (`failed + denied calls`) and 23 (`compactions`) of
`skills/agent-process/templates/per-task-dashboard.json` read their columns from
`task-readings.csv`, merge the per-repository queries, drop rows with an empty count, sort by
`merged_at` and add `trend` (trailing mean of 3). `api_requests` is already a CSV column.

## Goals / Non-Goals

**Goals:** a rate per task beside the count, in the same panel, for every row already in the
CSV that has `api_requests`.

**Non-Goals:** a rate trend; rates for other panels; a CSV column.

## Decisions

### D1: The rate is computed by the panel's transformations

The null filter also excludes rows with an empty `api_requests`. After it (and, in panel 22,
the existing `failed + denied` sum), one `calculateField` binary step adds
`per 100 requests` = count ÷ `api_requests`, shown with unit `percentunit` (0.0146 shows as
1.46%, the count per 100 requests). An `organize` step excludes `api_requests` (panel 22 extends its existing one). `trend` stays on the count.

Grafana documents the step: "Binary operation - Apply basic binary operations ... on values
in a single row from two selected fields"
([Transform data, Add field from calculation](https://grafana.com/docs/grafana/latest/panels-visualizations/query-transform-data/transform-data/)).
It does not skip empty operands: `getBinaryCreator` assigns `operator.operation(left[i], right[i])`
for every row, and Divide is `(a: number, b: number) => a / b`
([`calculateField.ts`](https://github.com/grafana/grafana/blob/main/packages/grafana-data/src/transformations/transformers/calculateField.ts),
[`binaryOperators.ts`](https://github.com/grafana/grafana/blob/main/packages/grafana-data/src/utils/binaryOperators.ts),
`main`, read 2026-10-17), so a null `api_requests` yields `Infinity` or `NaN`, not a gap.
Such a row is possible: `task_readings.py` writes `compactions = "0"` from the compaction
lookback while `api_requests` stays empty under `no api_request event`. Hence the filter.

Alternatives: a `× 100` step before the division, shown as a bare number — rejected: an
intermediate field to compute and hide, for the same figure. A `*_per_100` column written by
`task_readings.py` — rejected: a derived value would change the CSV header, the *Merged task
records its readings* requirement and its tests, and old rows would stay without it.

### D2: The rate draws on a right axis of the same panel

A field override on `per 100 requests` sets the unit, a display name, a fixed colour distinct
from the green count and orange trend, and `custom.axisPlacement: right`. Auto would also
place it right, since "When there are two or more series with different units, Grafana
assigns the left axis to the first unit and the right axis to the units that follow"
([Time series, Placement](https://grafana.com/docs/grafana/latest/panels-visualizations/visualizations/time-series/));
the explicit value does not depend on field order.

Alternative: two separate rate panels. Rejected: it changes the panel count and layout, and
separates the two numbers the reader compares.

No ADR: the decision is local to two panels. No doc edit: the `aqxk4q` paragraph of
`.agent-process/docs/telemetry-measurement-setup.md` describes no individual panel, and the
rate reads only columns it already lists.

## Risks / Trade-offs

- A row with a count and an empty `api_requests` is no longer drawn in these two panels; it
  stays in the table with its `gap`. In `task-readings.csv` (2026-10-17, 27 rows) the 5 rows
  with an empty `api_requests` (issues 383, 384, 387, 389, 395) have empty counts too, so no
  point drawn today disappears.
- Unit tests check the template structure, not Grafana's evaluation; the live check is the
  re-import of `aqxk4q` reading 1.46% for PR 401 (task 3.3).
- Rollback: revert the template and re-import `aqxk4q`; no data changes.
