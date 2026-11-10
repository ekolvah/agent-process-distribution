## Context

See proposal.md — Why. Install steps 5–6 are prose in `skills/agent-process/SKILL.md`; Delivery
already waits on a PR with `wait_for_pr` and reads its exit 4 as "no longer open".

## Standard approach

- Waiting on checks: the repository's own `wait_for_pr`, the tool Delivery uses. Reading the
  merge: `gh pr view --json state` (https://cli.github.com/manual/gh_pr_view), whose
  values are GitHub's `PullRequestState` enum `OPEN`, `CLOSED`, `MERGED`
  (https://docs.github.com/en/graphql/reference/enums#pullrequeststate). Observed:
  `gh pr view 490 --json state` → `{"state":"MERGED"}`.

## Decisions

- **D1 — Prose in the skill, no new script.** The gap is a session ending at the PR, closed by
  the next instruction the agent reads; the merge is the person's act, so no script can carry
  it. Alternatives: a `finish_install` script polling for the merge — rejected (§VII), it wraps
  existing commands and still needs the person; a session-start marker for inactive protection,
  as for the identity — out of this issue's scope, the `manual protection` row already reports it.
- **D2 — `wait_for_pr` waits for the checks, `gh pr view` reads the merge.** Rerunning
  `wait_for_pr` would also report the merge (exit 4), but its exit-4 line ends `report to the
  person`, Delivery's stop, which the agent could follow instead of continuing; and on a PR still
  open it waits again and exits 0 or 1, which the agent must read as "not merged yet".
  `gh pr view <PR> --json state` answers at once. Exit 4 before the merge request (the person
  merged early) goes to the same read.
- **D2b — No Delivery fix loop on the installation PR, narrowed.** The PR carries
  installer-managed files; an edit there diverges from the templates and the next `init`
  reports a conflict or overwrites it. So review threads are shown to the person, and a P0/P1
  thread on such a file is proposed as an issue in `ekolvah/agent-process-distribution`, where
  the template is fixed. A failing `agent-process / quality` is fixed by the agent, as step 1
  told the person before `--confirm`; a first exit 3 (the first `agent-review` run outlasting the
  timeout) is rerun once, a second one is shown, so checks that never start (Actions disabled)
  end the wait; exit 2 is shown. A state other than `MERGED` is shown and install stops; the
  `manual` rows report the rest (D4).
- **D2a — Step 5 keeps its condition**, both process checks green and the PR merged: the
  base requires no checks at install time, so `wait_for_pr`'s exit 0 settles on the reported
  checks only and does not replace it. `activate_protection --pr <N> --dry-run` exits 2 unless
  the PR head has a `success` run of each check (`activate_protection.py:5-11`), so the
  condition is also enforced there.
- **D3 — The agent switches to the default branch and pulls** after the merge instead of telling
  the person to; a local, reversible step the session now reaches.
- **D4 — The `manual` rows stay** as the net for a session that ends before the merge; `init`
  is unchanged.

## Risks / Trade-offs

- [The person merges after the session ended] → D4.
- [A test on skill prose checks words, not behaviour] → it is the repository's existing level
  for the skill's procedures (`tests/publisher/test_planning_workflow.py`).

## Migration Plan

None; skill prose only.
