## Context

See proposal.md — Why. Current state that shapes the approach:

- The `tasks` rule (`openspec/config.yaml`) carries Group 0 and the architect-review tail
  as shell steps; `test_planning_workflow.py` asserts their order by substring index
  (`test_tasks_of_a_new_change`, `test_plan_approved`); `agent-process.md` §Planning and
  step 3 of the delivery flow repeat them; every `tasks.md` copies Group 0.
- `set_status.py` exposes `set_status(number, status, *, gh, priority=None)` (per its
  `--help`: `[--priority PRIORITY] issue [status]`) and `run_gh`, so the new scripts import
  them instead of spawning; `set_status.main` maps `ValueError`/`KeyError` to a message and
  exit 2.
- The change's own `tasks.md` must follow the rule as it reads today (the new scripts do not
  exist until this change lands): its Group 0 is the current shell sequence.

## Goals / Non-Goals

**Goals:**
- One place for each condition of the delivery order: a script with an exit code, named
  once in the rule.
- Seams for tests stay injected callables (`gh`), never network.

**Non-Goals:**
- `check_red` (`v2-2d-check-red-test`), `wait_for_pr` (`v2-2e-wait-for-pr-checks`).
- Changing `resolve_review_thread.py`, `archive_change.py`, `request_codex_review.py`.
- Migrating the Group 0 text of open `tasks.md` files.

## Decisions

### D1 `start_change.py <change> --planner <Claude|Codex> --implementer <Claude|Codex>`

Order and exit codes:

1. `openspec/changes/<change>/architect-review.md` — the first non-empty line under
   `## Verdict` does not start with `approve` → print `verdict: <line> — apply the findings,
   re-review` and exit 2. Missing file → exit 2 with the path.
2. `tasks.md` is read through the D3 token alone: `tracking issue <N>` present → print
   `propose run not finished: run its tail (create_tracking_issue.py <change> --priority …)
   first`, exit 2; else the number is the first match of `tracking issue (\d+)`; neither →
   exit 2 naming the convention. The literal outside the token (a test description, a
   quoted rule line) is text and decides nothing.
3. `gh issue view N --json projectItems` → an empty `projectItems` list (the issue is no
   Project item: the state a propose run that never reached `set_status` leaves) or a
   Status name ≠ `Planned` → the same `propose run not finished` line with `Status: none`
   or the Status seen, exit 2.
4. `gh issue develop -c N --name <change>`; `set_status(N, "In Progress", gh=…)`;
   `gh issue comment N --body "planner: <p>; implementer: <i>"`. Any `gh` failure
   (`RuntimeError`) → its stderr, exit 1; `ValueError`/`KeyError` from `set_status` (unknown
   option, zero or several linked Projects) → the message, exit 2, mirroring
   `set_status.main`; a `None` capture is an error (as in every delivery script).

Resume: `start_change` is run once per change. A run interrupted before the archive
resumes with `git switch <change>`, after the archive from `gh pr view <change>` (the
rule's existing text) — never with a second `start_change`. What a second run does at
`gh issue develop` on an existing branch is not on record and the design does not rest on
it.

*Alternatives.* Keep the steps in the rule — the copies the proposal counts. Check the
verdict only, leave the branch to the rule — the conditions would still be prose. A `--dry-run`
gate — two commands where one exit code suffices.

*Observations.* `projectItems` shape and the `gh issue develop` base sentence: proposal.md
— Why.

### D2 `create_tracking_issue.py <change> [--priority <High|Medium|Low>]`

- `tasks.md` carries the D3 token `tracking issue <N>` (the same read as D1 step 2: the
  token, not the literal anywhere): `--priority` is required (missing → exit 2 asking
  for it); `gh issue create --title "<change>" --body-file
  openspec/changes/<change>/proposal.md` → the number is the last path segment of the
  printed URL; the number is written into `tasks.md` at once — only the `tracking issue
  <N>` token of D3 (`re.sub`), never every occurrence of the literal, which a test
  description or a rule quotation may carry — and only then `set_status(N, "Planned",
  priority=P)`; print the URL. Order matters: a `set_status` failure after the create
  leaves the number in `tasks.md`, so a re-run lands on the existing-number branch instead
  of creating a second issue; its message ends with the resume, `set_status.py <number>
  Planned --priority <P>`, because that branch refuses `--priority`.
- `tasks.md` carries `tracking issue (\d+)`: `--priority` given → exit 2 (the priority was
  set at creation, state spec "Priority is set at creation"); else `set_status(N, "Planned")`.
- Neither → exit 2 naming the convention. Errors map as in D1: `gh` failure → 1,
  `ValueError`/`KeyError` from `set_status` → the message, 2.

The proposal as the body keeps today's behaviour (`--body-file …proposal.md` in the rule).

*Alternatives.* Two scripts (create / plan) — the branch is one `if`. `gh issue create
--json` — does not exist (`gh issue create --help`); the URL is the output.

### D3 The `tasks` rule names the calls; the person's parts stay prose

Group 0 becomes: `python .agent-process/scripts/start_change.py <change> --planner <…>
--implementer <…>` (tracking issue <N>; on `rework` no delivery task runs: apply the
findings, re-review; ask when the planner is unknown). The architect-review entry ends
with: ask the priority when the change has no issue, `python
.agent-process/scripts/create_tracking_issue.py <change> [--priority <answer>]`, only then
report ready. `grep -q`, `gh issue view --json projectItems`, `gh issue develop`,
`set_status "In Progress"`, `gh issue comment`, `gh issue create`, `sed -i` leave the rule.
Group 1 and the Deliver group are unchanged (Group 1 is `v2-2d-check-red-test`'s; PR body,
three rounds, the merge are the person's or already scripts).

`tasks.md` convention: the Group 0 task text carries `tracking issue <N>` (the propose run
replaces it), which is where both scripts read the number.

### D4 Tests follow the seams

- `test_start_change_*`: rework verdict → 2 and no `gh issue develop` call; `<N>` → 2 with
  `propose run not finished`; Status `Todo` and an empty `projectItems` → 2; happy path →
  the three `gh` calls in order.
- `test_create_tracking_issue_*`: placeholder without priority → 2; placeholder → create,
  `Planned` with priority, `<N>` replaced; existing number → `Planned` alone, `--priority`
  refused. The `_FIELDS` fixture gains the `Planned` Status option.
- The new scripts import `run_gh` from `set_status`, whose entry in
  `test_none_capture_is_an_error` already covers them.
- `test_tasks_of_a_new_change` / `test_plan_approved` / `test_rework_verdict`: assert the
  new substrings (`start_change.py`, `create_tracking_issue.py`) and the absence of
  `sed -i`, `gh issue develop -c` and `grep -q` in the rule.

## Risks / Trade-offs

- [The old Group 0 text remains in every open `tasks.md` at merge time] → the shell steps
  still work; only new changes get `start_change`. No migration of open changes.
- [`start_change` re-run after a partial success] → the resume path is the rule's
  (`git switch` / `gh pr view`), see D1; the script is not made idempotent, since no
  observation of `gh issue develop` on an existing branch is on record.
- [Two scripts share the `tracking issue (\d+)` convention] → one regex, named in the rule
  text; a `tasks.md` without it is exit 2 with the convention named, never a guess.
- [The literal placeholder appears in a `tasks.md` outside Group 0 — a test description,
  a quoted rule line] → today's rule (`sed -i` over the whole file) would rewrite it; this
  change's own `tasks.md` keeps the literal in Group 0 only, and `create_tracking_issue`
  replaces the D3 token alone.

## Migration Plan

One PR. The `tasks.md` of this change follows today's rule: Group 0 as shell steps.
Rollback is the revert of the PR: no data, no platform state.
