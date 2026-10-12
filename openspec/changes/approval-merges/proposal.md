## Why

Since ADR 0040 the agent's PR needs the person's approval, and the person then still clicks
Merge: two actions where one carries the decision. ADR 0040 D2 already lets auto-merge carry
out the approval and the release PRs use it, but delivery never enables it on the agent's PRs.

Observed on 2026-10-12, PR 408: green, `reviewDecision` `REVIEW_REQUIRED`, `BLOCKED`; the person
then approved and enabled auto-merge by hand (`autoMergeRequest.enabledBy` `ekolvah`, merge
method `SQUASH`, merged by `ekolvah`). The agent's own `gh pr merge 408 --auto --squash` had been
refused by the git guard of plugin 3.14.0, which ADR 0040 D5 removes from 3.15.0 on.

## What Changes

- New script `agent-process enable_auto_merge <PR>`: enables auto-merge with squash on the PR
  only when GitHub reports that it needs an approval (`reviewDecision` `REVIEW_REQUIRED`);
  otherwise it enables nothing and says the person merges.
- The delivery procedure runs it right after `gh pr create`, and the delivered-change
  explanation states its outcome. "The person merges" becomes "the person's approval merges".
- `agent_identity` gains one transition: the repository allows auto-merge (off by default on
  GitHub), so the gate and the setting arrive together in a consumer.
- `wait_for_pr` reads the PR's state with its head and exits 4 when the PR is no longer open,
  so a PR the approval merged during the review loop stops the loop visibly instead of
  taking a push that reaches no PR.
- ADR 0040 gains D7: the agent enables auto-merge; the approval ruleset is unchanged.

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: the agent's PR gets auto-merge when it needs the person's approval.
- `distribution`: `Agent identity converges` adds the `allow_auto_merge` transition.
- `implementation`: `wait_for_pr` ends with exit 4 on a PR that is no longer open.

## Impact

- Added: `skills/agent-process/scripts/enable_auto_merge.py`,
  `tests/publisher/test_enable_auto_merge.py`.
- Edited: `skills/agent-process/scripts/agent_identity.py` (one transition),
  `skills/agent-process/scripts/wait_for_pr.py` (state read, exit 4),
  `tests/publisher/test_pr_delivery.py`,
  `tests/publisher/test_agent_identity.py`,
  `skills/agent-process/SKILL.md` (Tasks step 5, Delivery, Install step 6),
  `tests/publisher/test_planning_workflow.py` (delivery order),
  `tests/publisher/test_plugin.py` (script inventory),
  `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` (D7, Confirmation).
- Removed: none. No change to the approval ruleset.
