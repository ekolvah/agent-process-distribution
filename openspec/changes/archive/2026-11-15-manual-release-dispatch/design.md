## Context

`release-please.yml` triggers on `push` to `main` and on `schedule`; the action gets
`skip-github-pull-request: ${{ github.event_name == 'push' }}`, so every non-push run opens or
updates the release PR, and the approve and auto-merge steps gate on `prs_created` (ADR 0047).
Motivation and the HTTP 422 observation: proposal.md, Why.

## Standard approach

GitHub's manual trigger is the `workflow_dispatch` event
(https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch:
"To enable a workflow to be triggered manually, you need to configure the `workflow_dispatch`
event"), started by `gh workflow run <workflow> --ref main`.

## Goals / Non-Goals

**Non-Goals:** dispatch inputs (version override, release-as).

## Decisions

1. **Add `workflow_dispatch:` with no inputs; change nothing else.** The existing
   `github.event_name == 'push'` expression already treats a dispatched run as a PR run, so the
   approve and auto-merge steps and the guard "the run that produced the head approves it"
   apply unchanged. Rejected: running `release-please release-pr` locally with the person's
   token — no run of the workflow produced the head, so `github-actions` does not approve it
   and the person cannot approve their own PR; a second workflow — more code for the same steps.
2. **ADR 0047 gets a Consequences line**, not a new ADR: a dispatch is a person-chosen daytime
   release commit on `main`, the cost ADR 0047 removed by default; the default stays nightly.

## Risks / Trade-offs

- [`workflow_dispatch` is usable by anyone with write access] → write access can already push to
  `main` through a PR; the release PR still needs its required checks to merge.

## Migration Plan

Merge, then `gh workflow run release-please.yml --ref main`. Rollback: revert the trigger line.
