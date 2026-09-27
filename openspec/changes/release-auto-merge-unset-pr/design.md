## Context

See proposal.md — Why for the observation and the root cause. The auto-merge step came with
ADR 0031 D4 (#212); the release-please action step (`id: release`) is unchanged.

## Goals / Non-Goals

**Goals:** no expression of the auto-merge step can fail when the action leaves `pr` unset.

**Non-Goals:** other `fromJSON` uses. `quality.yml` parses `needs.plan.outputs.checks`, which
the `plan` job always sets, so it is not the same defect.

## Decisions

- **D1 — raw output in `env`, parsed in `run`.** The step sets
  `PR_JSON: ${{ steps.release.outputs.pr }}` (an unset output becomes `''`, which evaluates
  without error), and `run` does `PR=$(jq -er .number <<<"$PR_JSON")` and then
  `gh pr merge --auto --squash "$PR"`. The jq manual defines `-e`: "exit status 4 if no valid
  result was ever produced", and 1 for `null`. The default `run` shell on Linux is `bash -e`,
  so if `pr` is empty or has no number while `prs_created` is `'true'`, the run fails. It does
  not call `gh pr merge ""`. The required `quality` gate already runs `jq -e ... <<< "$NEEDS"`
  on `ubuntu-latest` with no `shell:` key (`quality.yml:129`), so jq, its `-e` status and the
  errexit shell are observed in this repository. D1 follows that form.
  - Alternative: `fromJSON(steps.release.outputs.pr || '{}').number`. It also avoids the
    failure, but a missing PR then becomes an empty number without any diagnostic. Rejected.
  - Alternative: `prs_created == 'true' && fromJSON(...)` in `env`. This relies on
    short-circuit evaluation that has not been observed. Rejected.
- **D2 — the test states the class, not the line.** Run 36297738914 showed that the runner
  evaluates a step's `env` although its `if` is false. The test therefore asserts that no
  `env` value of a step guarded by a step output calls `fromJSON`. This also covers any later
  step guarded the same way.

## Risks / Trade-offs

- [The static test cannot show that the runner no longer fails] → the live check after merge
  (task 4.3): the next `Release Please` run is green, and the release PR merges itself (#208).

## Migration Plan

Merge only. The first push to `main` re-runs the workflow. Rollback is a revert of the
workflow edit, which brings back the red run.
