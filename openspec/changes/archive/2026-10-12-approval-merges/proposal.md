## Why

Since ADR 0040 the agent's PR needs the person's approval, and the person then still clicks
Merge: two actions where one carries the decision. ADR 0040 D2 already lets auto-merge carry
out the approval and the release PRs use it, but delivery never enables it on the agent's PRs.

Observed on 2026-10-12, PR 408: green, `reviewDecision` `REVIEW_REQUIRED`, `BLOCKED`; the person
then approved and enabled auto-merge by hand (`autoMergeRequest.enabledBy` `ekolvah`, merge
method `SQUASH`, merged by `ekolvah`). The agent's own `gh pr merge 408 --auto --squash` had been
refused by the git guard of plugin 3.14.0, which ADR 0040 D5 removes from 3.15.0 on.

## What Changes

- The delivery procedure runs `gh pr merge <PR> --auto --squash` right after `gh pr create`;
  the approval ruleset holds the PR for the person. "The person merges" becomes "the person's
  approval merges".
- Install step 6 has the person run `gh repo edit --enable-auto-merge` (off by default on
  GitHub).
- `wait_for_pr` reads the PR's state with its head and exits 4 when the PR is no longer open,
  so a PR the approval merged during the review loop stops the loop visibly instead of
  taking a push that reaches no PR.
- ADR 0040 gains D7: the agent enables auto-merge; the approval ruleset is unchanged and is
  the only barrier.

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: the agent's PR gets auto-merge right after it is created.
- `implementation`: `wait_for_pr` ends with exit 4 on a PR that is no longer open.

## Impact

- Edited: `skills/agent-process/scripts/wait_for_pr.py` (state read, exit 4),
  `tests/publisher/test_pr_delivery.py`,
  `skills/agent-process/SKILL.md` (Tasks step 5, Delivery, Install step 6),
  `tests/publisher/test_planning_workflow.py` (delivery order),
  `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` (D7, Confirmation).
- Removed: none. No change to the approval ruleset.
