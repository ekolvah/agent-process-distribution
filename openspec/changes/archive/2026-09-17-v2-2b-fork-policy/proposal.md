## Why

Round 4 of the second PR of `v2-2b-review-by-apps` (branch `issue-130-review-events`,
`26bc2da`) put a fork guard on the Claude step of the review job
(`github.event.pull_request.head.repo.full_name == github.repository`) and wrote it into
the spec as the scenario *Head from a fork*, because whether GitHub withholds secrets on a
`pull_request_review` run of a fork PR was taken as undocumented. Codex's fifth review then
showed the guard protects nothing: the caller YAML of such a run is read from the PR merge
ref, so a fork can rewrite it and no condition in callee or caller reaches the secret. The
platform reference, read at that point, settles the question the guard was written for:
the events page lists `pull_request_review` under the same fork restriction as
`pull_request` — every secret but `GITHUB_TOKEN` is withheld from a run of a fork PR, the
token is read-only (observed in the wild on aws-actions/configure-aws-credentials, issue
416). The guard is code for what the platform does; the control that adds something is
the repository setting "Require approval for all external contributors", set by the owner
on 2026-09-17. Root cause: the platform fact was not verified before the guard was
designed. Reproduction of the redundancy: the guard's condition can be true only when the
secret is present anyway, and false only when the secret is absent anyway.

## What Changes

- `review-and-merge`, "Codex reviews on the author's request, Claude is the fallback": the
  requirement text returns to what `main` says (the fallback runs when the wait ended
  absent; no "head in the repository itself" clause) and the scenario *Head from a fork*
  states the platform rule and the setting instead of the guard — the outcome is the same
  (a fork PR is reviewed by Codex or by a person, never by the fallback), the mechanism is
  the platform's. It stays as a scenario because OpenSpec 1.13.0 lets no MODIFIED delta
  drop one and refuses the same name under REMOVED and ADDED. The other scenarios are
  unchanged.
- `reusable-agent-review.yml`: the Claude step's `if` is `steps.codex.outputs.absent ==
  'true'` alone, with a comment naming the platform rule and the setting; the test asserts
  the exact condition.
- ADR 0027: the observation replaced — the platform rule with its source, the setting and
  its API call, the deletion condition.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `review-and-merge`: "Codex reviews on the author's request, Claude is the fallback".

## Impact

- Edited: `.github/workflows/reusable-agent-review.yml` (one `if`, one comment),
  `tests/publisher/test_reusable_workflows.py` (the assertion of that `if`), ADR 0027 (one
  bullet), `openspec/specs/review-and-merge/spec.md` (by the archive alone).
- Removed: nothing besides the guard.
- Delivered on the open PR of the tracking issue (the second PR of issue 130): no new
  issue, no new branch — the change is the delta of that PR's review fix, as the Deliver
  rule orders for a review fix that changes a spec.
