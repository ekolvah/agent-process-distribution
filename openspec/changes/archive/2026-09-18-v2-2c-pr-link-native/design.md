## Context

See proposal.md — Why (the four observations). Three reusable workflows, three thin
callers, three required contexts; every caller pins its callee `@main` (ADR 0012: a PR
cannot rewrite what it is checked under), so a PR of this repository runs the callee main
carries, never its own. `reusable-quality.yml` checks out the trusted driver from the
default branch and runs `ci_check.py` in the PR worktree; `GITHUB_TOKEN` is the job's
`gh` credential. The pre-push hook runs `check_branch_protection.py`, which reports a
declared context missing from GitHub as drift and an extra context on GitHub as
preserved. `install_branch_protection.py` adds contexts (`POST
…/protection/required_status_checks/contexts`, body `{"contexts": […]}`) and never
removes one.

## Goals / Non-Goals

**Goals:**

- The link is GitHub's field, read once, enforced by the check that already exists.
- The PR of this change merges by one edit of the live protection, in a stated order.

**Non-Goals:**

- One reusable workflow for quality and review (owner's decision, 2026-09-18; issue 112).
- A bot exemption, a `Closes` line in the PR template, the v1 scripts that render the PR
  body (issue 114).
- Re-observing what the proposal records.

## Decisions

- **D1 — One `gh` line in the quality callee, no script, no poll.** The step reads
  `closingIssuesReferences` with `gh pr view --jq` and fails on `0`, before the driver
  runs: a PR that links nothing needs no quality run to say so. The proposal's second
  observation (link at +1–3 s, step at +14–15 s) retires the poll; a false red, should
  the field ever lag, is one `gh run rerun`, visible, never a silent pass. The step runs
  before any checkout, so the repository comes from `GH_REPO: ${{ github.repository }}`
  (`gh help environment`, 2026-09-18: "`GH_REPO`: specify the GitHub repository in the
  `[HOST/]OWNER/REPO` format for commands that otherwise operate on a local repository");
  the retired callee ran the same read inside a checkout and needed none. A failed read
  (token scope, API error) is red, not `ok`: the step declares no `shell:`, so `run` is
  `bash -e {0}` (workflow syntax reference, `jobs.<job_id>.steps[*].shell`, the row for an
  unspecified shell on non-Windows runners:
  https://docs.github.com/en/actions/writing-workflows/workflow-syntax#jobsjob_idstepsshell),
  and the assignment `linked="$(gh …)"` carries the substitution's exit status; the test
  of task 1.1 asserts the absence of `shell:` so an override cannot turn the failed read
  into a pass. *Alternative:*
  a `verify_pr_link.py` reduced to the read — rejected: a script needs a checkout, an
  install and a test of its own for one line the callee can hold. *Alternative:* a fourth
  callee step in `reusable-agent-review.yml` — rejected: the link is a fact about the PR,
  not about the review; `quality` runs on every PR and needs no secret.
- **D2 — Every PR, not "issue branches".** The branch-name test was the v1 way to know a
  PR belongs to an issue; in v2 a branch is named after its change and every change has a
  tracking issue, so the exemption exempted every PR. A PR without an issue is the case
  the check exists for. *Consequence:* a bot PR (Dependabot is not configured) would red
  `quality`; an `if:` on the author is added the day such a PR is observed (standard over
  bespoke).
- **D3 — The failure message is the fix.** `::error::` names the two ways to link
  (`Closes #N` in the body; a branch from `gh issue develop -c <N> --name <branch>`) and
  `gh run rerun $GITHUB_RUN_ID`: the caller runs on `pull_request` pushes alone, a body
  edit or a manual link raises no event the caller subscribes to, and the re-run is the
  deterministic step. *Alternative:* add `edited` to `ci.yml`'s event types — rejected:
  every title or body edit would run the full quality suite for a field that a `gh issue
  develop` branch settles before the PR exists.
- **D4 — Permissions are the retired workflow's.** `pull-requests: read` and
  `issues: read` on the callee and on `ci.yml` (`test_caller_permissions_are_a_superset…`):
  the set `reusable-pr-link.yml` ran the same `gh pr view --json closingIssuesReferences`
  under. Which of the two the field needs is not inferred; both are read-only.
- **D5 — Bootstrap order, three contexts to two.** (1) The PR deletes `pr-link.yml`, so
  `pr-link / pr-link` never reports on it and `mergeStateStatus` is `BLOCKED` while
  `quality` and `agent-review` are green; the pre-push hook passes (an extra context on
  GitHub is preserved, not drift). (2) After the review loop, the context is removed by
  the reference call — `DELETE
  /repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks/contexts`,
  body `{"contexts": ["pr-link / pr-link"]}` ("Remove status check contexts", REST
  reference, branch protection; the installer's `add_contexts` is the same endpoint with
  `POST`) — by the person, or by the implementer after the person's confirmation, and
  `python .agent-process/scripts/check_branch_protection.py` prints the two remaining
  contexts. (3) The person merges. Other PRs open at step (2) lose nothing: the two
  contexts they report are the two required. *Alternative:* remove the context before the
  PR — rejected: a window in which no PR has to link its issue.
- **D6 — The step is first exercised after the merge.** The caller pins `@main`; the PR
  runs today's callee. The first PR after the merge is the observation and goes into ADR
  0027 as the entry's confirmation line (as `fix-rerun-fallback-head` did): run id, the
  step's output. *Alternative:* a throwaway PR from a linked branch before the merge —
  rejected: it would exercise the same `@main` callee.
- **D7 — The `## Deferred scope` verification goes without a replacement.** Its consumer,
  the downgrade rule of the review contract, left in `v2-2b`
  (`test_review_contract_and_principles_stay_coupled…` asserts `deferred-scope` is not in
  the contract); the block `open_pr.py` renders is text nobody reads until issue 114
  deletes the renderer. ADR 0020 enters the superseded list of ADR 0027.

## Risks / Trade-offs

- [The field lags behind the run on some PR] → the step fails with the re-run command;
  one `gh run rerun`, and the lag goes into ADR 0027 as an observation before any poll
  returns.
- [The two-line `if`-free step admits a PR whose link is a `Closes` to an unrelated
  issue] → the same is true of the v1 keyword check; the link is the person's to read on
  merge, the check proves there is one.
- [The person removes the context before the PR's checks are green] → nothing breaks:
  `quality` and `agent-review` stay required; the order in D5 is for a review of the head
  under three contexts, not for safety.
- [`GITHUB_TOKEN` cannot read `closingIssuesReferences` with the two read scopes] → the
  retired workflow read it under the same scopes on every v1 PR (PR 137's `pr-link` runs);
  a failed read reds the step with `gh`'s own message (D1, `bash -e`), never passes; the
  first run after the merge confirms (D6).
