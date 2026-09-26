## Context

`agent-process.yml` calls `quality.yml` by a same-commit `./` path. The one job `quality`
verifies the PR → issue link, runs `setup`, then runs `test`
(`python .agent-process/scripts/ci_check.py`). `ci_check` runs the nine checks of its
`CHECKS` registry in one process and exits at the first failure. The ruleset
`agent-process default branch` requires `agent-process / quality` and
`agent-review / agent-review`, each bound to integration 15368. Consumers render the same
caller with their own `setup` and `test`. That `test` is any command, not necessarily
`ci_check`.

Platform behaviour this design rests on (GitHub docs source, `github/docs`):

- `data/reusables/actions/workflows/skipped-job-status-checks-passing.md`: "A job that is
  skipped will report its status as "Success". It will not prevent a pull request from
  merging, even if it is a required check."
- `data/reusables/actions/jobs/section-using-jobs-in-a-workflow-needs.md`: "If a job fails or
  is skipped, all jobs that need it are skipped unless the jobs use a conditional expression
  that causes the job to continue. … use the `always()` conditional expression in
  `jobs.<job_id>.if`."
- `data/reusables/actions/jobs/section-using-a-build-matrix-for-your-jobs-failfast.md`:
  "`jobs.<job_id>.strategy.fail-fast` … will cancel all in-progress and queued jobs in the
  matrix if any job in the matrix fails. This property defaults to `true`."
- `content/actions/reference/workflows-and-actions/contexts.md`: `needs.<job_id>.result` is
  one of `success`, `failure`, `cancelled`, `skipped`. The docs do not say how a matrix job's
  legs aggregate into that one value, so a task observes it on a live run (tasks 4.2).
- Same page, context availability table: "`jobs.<job_id>.name` | `github, needs, strategy,
  matrix, vars, inputs`", so a job name may read `matrix.check`.
- `content/actions/reference/workflows-and-actions/expressions.md`: "This workflow sets a
  JSON matrix in one job, and passes it to the next job using an output and `fromJSON`",
  with `matrix: ${{ fromJSON(needs.job1.outputs.matrix) }}`.
- Observed on this repository: the ruleset requires `agent-process / quality`, which is
  caller job `agent-process` / callee job `quality`. That a callee matrix leg with a `name:`
  reports as `agent-process / <name>` is not stated by the docs, so task 4.2 observes it too.

## Goals / Non-Goals

**Goals:** every quality check is its own line in the PR's check list; one failing check
does not hide the others; `CHECKS` stays the only list of checks; the required context and
the ruleset stay unchanged.

**Non-Goals:** consumer opt-in through `init.py`; changing `reusable-quality.yml`; caching
dependencies across jobs; a table in the job summary.

## Alternatives

| # | Option | Pros | Cons |
|---|---|---|---|
| A | Keep one step, fail-fast (today) | Cheapest: one runner, one setup. No change. | The merge box shows one line. The first failure hides the rest. The list of checks is visible only in the log. |
| B | Table in `$GITHUB_STEP_SUMMARY`, run all checks without fail-fast | About 20 lines in one script. The required context is unchanged. Still one runner. | The merge box still shows one line, and the table is one click away. It is a bespoke report where the platform already has a native per-job status. |
| C | One check run per check through the Checks API | Native lines in the merge box. Still one runner. | Needs `checks: write` in the caller and the callee. Check runs created by the `GITHUB_TOKEN` attach to an arbitrary check suite. It is bespoke API code to maintain and test. It widens the token of a job that runs PR code. |
| D | Static jobs in YAML (`lint`, `test`, …) plus a gate (`re-actors/alls-green`) | The industry standard shape: native lines, parallel, independent. | The YAML becomes a second list of checks beside `CHECKS`, which breaks `ci_check is the one command every gate runs` ("no second list"). A check added to `CHECKS` runs nowhere until the YAML follows. It adds a third-party action. |
| **E** | **Dynamic matrix from `CHECKS` plus a gate `quality` (chosen)** | Native lines, parallel, independent, like D. `CHECKS` stays the only list. The required context and the ruleset do not change. No new permission and no third-party action. | Runner minutes grow with the number of checks: each job repeats checkout, Python, and `setup`. There are three more jobs to read (link, list, gate). |

E is chosen because it is the only option that meets all four goals. D is the same standard
with the check list hard-coded. B and C keep one line or add a token scope. The cost of E is
runner minutes, not wall-clock time and not trust.

## Decisions

**D1 — Jobs of `quality.yml`.** `link` runs the existing issue-link step unchanged. `plan`
checks out the repository, sets up Python, and runs `checks`. It validates the output with
`jq -e`: a non-empty array of strings matching `^[A-Za-z0-9._-]+$`. It writes the output as
`checks=<json>`. Without `checks`, it writes `[""]`. `check` needs `plan`, uses
`strategy: {fail-fast: false, matrix: {check: <plan output>}}`, and is named
`${{ matrix.check || 'test' }}`. It runs checkout, Python, `setup`, then
`${{ inputs.test }} ${CHECK:+--only "$CHECK"}` with `CHECK` passed through `env`, so a name
is never interpolated into the script. `quality` needs `[link, plan, check]`, runs
`if: always()`, and exits non-zero unless every `needs.*.result` is `success`. The expected
check list reads `agent-process / link`, `agent-process / lint`, …, `agent-process / quality`.
Task 4.2 observes it.

**D2 — The gate is written inline, not `alls-green`.** It is one `jq` line over
`toJSON(needs)`. The third-party action would add a pinned dependency to the one required
context, and it would do the same thing.

**D3 — A skipped or cancelled job fails the gate.** A skipped job reports "Success" (docs
above). Without `always()` the gate itself would be skipped when `plan` fails, and so would
pass. The gate therefore accepts only `success`. It also runs when `plan` fails, which the
Listing fails scenario covers. An empty list fails `plan`, so zero checks can never pass
(§IV).

**D4 — `ci_check --list`.** It prints `json.dumps(list(CHECKS))` and returns before the
stamp logic. It is stdlib-only, so `plan` runs it without `setup`. It keeps `--only` as the
per-check entry point, which the tests already cover.

**D5 — Consumers do not change.** `checks` is optional. The rendered consumer caller does not
pass it, so a consumer gets `link`, `test`, and `quality`: the same required context, and the
same commands in the same order, but in three jobs instead of one. Opting consumers in
(an `init.py --checks` flag) is a follow-up once E has run on this repository.

**D6 — `reusable-quality.yml` is left as is.** No workflow of this repository calls it. It
exists for v1 consumers pinned to `@main`, and no spec covers it. Changing it would change
those consumers' check list without a spec or a release.

## What stops proving, and the catcher that is reached

The single process exited at the first failure, and the one job carried the verdict. The
verdict now comes from the gate `quality`. The trap is a gate that passes on skipped work.
The catchers:

- D3 fails a skipped or cancelled `plan` or `check`: `test_quality_gate_requires_every_job`
  asserts `if: always()` and the success-only expression, on every PR.
- `fail-fast: false` keeps the other legs alive: asserted by the same test.
- How matrix legs aggregate into `needs.check.result` is platform behaviour the docs do not
  state. Task 4.2 observes it on the delivery PR's head, with one deliberately failing check,
  before the PR leaves draft.

## Risks / Trade-offs

- Runner minutes ×~9 per PR → accepted. A pip cache is a later, separate change, if minutes
  become a problem.
- A check named `quality`, `link`, or `plan` would shadow a job name in the list → such a
  check does not exist today. The regex does not reject these names, and the collision is only
  cosmetic because the gate reads `needs`, not names.
- The job names in the PR's check list change (`agent-process / lint`, …). Nothing requires
  them: the ruleset reads only `agent-process / quality`.

## Migration / Rollback

No migration: the ruleset and consumers are untouched. Rollback is a revert of the PR. The
required context keeps its name through both directions.
