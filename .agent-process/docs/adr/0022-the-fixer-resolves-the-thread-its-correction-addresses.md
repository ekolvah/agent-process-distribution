---
status: "accepted"
date: 2026-09-03
decision-makers: ekolvah
---

# The fixer resolves the thread its correction addresses

## Context and Problem Statement

`check_blocking_review_threads.py` fails the required check on every open
BLOCKING conversation, and nothing in this repository ever resolved one after
its finding was fixed. `resolvedBy.login` on the two BLOCKING threads
captured from PR #76 is the human maintainer's own out-of-band
`resolveReviewThread`, not a fixer commit and not CI — every prior delivery
carried this manual step or left the required check red on an addressed
finding.

The evidence captured against PR #76 (`evidence/issue-77/pr76-review-threads.json`)
rules out inferring "was this finding addressed?" from anything the reviews
themselves carry: a later Codex review never re-posts an earlier finding it
already reported, so absence of a re-post is not evidence the finding is
fixed — it is true both for a genuinely-fixed P1 thread and for a P2 thread
whose finding a later review still had no reason to repeat. The one field
that does distinguish, `isOutdated`, tracks line movement, not whether the
underlying finding was corrected — a commit that only reformats the anchored
lines would flip it with the finding intact.

## Considered Options

* CI resolves threads itself from inside `check_blocking_review_threads.py`,
  run by `reusable-agent-review.yml`. Rejected: the capture shows CI has no
  signal separating a closed finding from an open one — the only
  CI-observable fact is "a newer review ran", true for both an addressed and
  an unaddressed thread. Because `resolveReviewThread` is a mutation, this
  would durably resolve an unaddressed BLOCKING finding, not just misread it
  once.
* CI stays a classifier and skips a thread whose `isOutdated` is `true`,
  reusing an existing GitHub field. Rejected: correct on all four captured
  records but read-only in name only — `isOutdated` is set by line movement,
  so a commit that reformats an anchored line without touching the finding
  would silently flip it, with nobody attesting to the correction.
* CI decides nothing about closure; a new local
  `.agent-process/scripts/resolve_review_thread.py`, run by the `fixer` role
  through the authenticated PR-author session, lists open BLOCKING threads
  and resolves one named node id, refusing any thread whose top-level
  comment `originalCommit.oid` equals the PR's current head SHA.

## Decision Outcome

Chosen: **CI never infers whether a review thread's finding was addressed;
the role that made the correction resolves the thread, and may not resolve a
finding reported against the PR's current head.**

1. `check_blocking_review_threads.py`'s `_QUERY` gains `originalCommit { oid }`
   on each comment node; `ReviewThread` carries it as a trailing, defaulted
   field. `blocking_threads()`'s `(thread_id, priority, url)` projection is
   unchanged — the required check's verdict does not change.
2. `resolve_review_thread.py` is a separate entry point, not a wrapper over
   the required check: different actor (the fixer, not a workflow token),
   different credential (the maintainer's authenticated `gh` session, not
   `github.token`), different trigger (a local run after a push, not
   `pull_request`). `--list` prints every open BLOCKING thread's node id,
   priority, and URL; `--thread <node-id>` issues the `resolveReviewThread`
   mutation.
3. **Fail-closed guard.** The mutation is refused when the thread's top-level
   comment's `originalCommit.oid` equals the PR's live head SHA — nothing has
   been pushed past the reviewed commit yet — and refused just as loudly when
   that field is absent or `null`, rather than letting `None != head` admit
   it silently.
4. **The mutation's own report is the proof.** `run_gh` exiting `0` is not
   evidence the thread resolved; the script re-reads the mutation's
   `isResolved` field and fails loudly unless it is `true`. This is the
   repository's first GraphQL mutation on any transport.
5. **Ordering.** `agent-review` triggers only on `pull_request: [opened,
   synchronize]`, and its enforcement step is the last step of
   `reusable-agent-review.yml`. The resolve must be issued after the push and
   before that run reaches its last step; issued later, it changes nothing
   until the next push. `review_gate.py`'s `fix-blocking` next action and
   `_red_reason` name this window and its recovery — re-running the completed
   `agent-review` run on the unchanged head, at no fixer-budget cost.
6. `.agents/orchestration/roles.yaml` `fixer.authority` gains resolving the
   thread its correction addresses; `fixer.completion_evidence` no longer
   states that only a new head SHA completes a round, since a resolve with no
   new head is now a legitimate completion.

### Consequences

* Good, because an addressed BLOCKING finding no longer requires a manual,
  out-of-band `resolveReviewThread` from the maintainer to unblock merge —
  the loop that already exists routes through it.
* Good, because CI's classification logic is untouched: `blocking_threads()`
  keeps deciding "may this PR merge?" from the same fields it always read,
  so this change cannot alter a merge verdict CI already computes correctly.
* Bad, because this is self-attestation by the fixer with no automatic
  backstop: a later Codex review does not re-raise a finding it already
  reported, so a thread resolved in error stays resolved. The fail-closed
  guard narrows the failure mode — a fixer cannot resolve without pushing
  past the reviewed commit — without removing it. Not weaker than today's
  manual human resolve, but not stronger either.
* Bad — residual risk, stated plainly. Whether a local `gh` session may
  issue `resolveReviewThread` under `pull-requests` scope is confirmed by the
  first live run, not verified up front; the capture cannot distinguish a
  local `gh` call from the web UI that produced `resolvedBy.login = ekolvah`
  on PR #76's two BLOCKING threads. A permission failure surfaces as a loud
  `isResolved` mismatch (§IV), not a silent no-op.

**Assumption and rollback.** Assumes a `pull-requests`-scoped local `gh`
session may call `resolveReviewThread` the same way it already reads review
threads. If the first live run shows otherwise, the rollback is to stop
routing the fixer through `resolve_review_thread.py` and return to the
manual human resolve this ADR replaces; `check_blocking_review_threads.py`'s
classification logic needs no change either way.

### Confirmation

`tests/publisher/test_resolve_review_thread.py` covers `--list`, the
mutation call, both guard refusals, and the loud failure on an unresolved
mutation response; `tests/publisher/test_blocking_review_threads.py::test_the_required_check_never_resolves_a_thread`
and `tests/publisher/test_reusable_workflows.py::test_no_workflow_step_resolves_a_review_thread`
pin that CI never gains this capability; `tests/agent_process/test_review_gate.py`
(+ `template/` twin) covers the `fix-blocking` next action and reason naming
the resolve step and its missed-window recovery. Relates to
[ADR 0020](0020-a-tracked-deferral-downgrades-a-matching-review-finding.md)
(the closest prior precedent for stating residual self-attestation risk
plainly rather than implying a gate is airtight).
