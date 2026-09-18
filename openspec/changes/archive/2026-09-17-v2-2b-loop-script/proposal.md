## Why

The order of the step after a push of the review loop — wait for the head's concluded
check, resolve the addressed thread, re-run that run, reply — was a sentence copied to the
Deliver rule, step 4 of `agent-process.md`, the `implementation` spec, ADR 0027 and the
`fix-blocking` action of `review_gate.py`. Three of the seven reworks of the second PR of
`v2-2b-review-by-apps` were a copy that lagged or a clause written for one path (the
window clause, "the reply re-runs the check", "the Codex review of the new head"), and the
open `P1` of the sixth Codex review (`review_gate.py` still printing the v1 window) is the
same defect once more. Prose has no test but string order; a script has an exit code.
Retrospective with the owner (2026-09-17): the order goes into the script (scripts >
instructions), the prose names the call.

## What Changes

- `resolve_review_thread.py`: `--thread <id> --reply-file <path>` is the whole step —
  `close_round`: refuses while the head's `agent-review` run (`gh run list --commit
  <head> --workflow agent-review.yml --event pull_request`) is not `completed`, resolves
  (the existing checks), `gh run rerun <id>`, posts the reply on the thread last; an empty
  reply is refused; `--reply-file` is required with `--thread`. Transports injected.
- `review_gate.py`: the `fix-blocking` next action and `_red_reason` name `wait_for_pr.py`
  and the script; the v1 window clause goes.
- `openspec/config.yaml`, Deliver group, and `agent-process.md` step 4: the call, one
  parenthesis on what the script refuses and does; no `gh run rerun`, no reply step of
  the rule's own.
- `implementation`, "Delivery steps are tasks of every change": the loop sentence names
  the command and its order as the script's; scenario *Blocking thread addressed* states
  the order.
- ADR 0027: the retrospective entry.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `implementation`: "Delivery steps are tasks of every change".
- `review-and-merge`: "Unresolved P0/P1 threads fail the review check" — the scenario
  *Review event re-runs the check* names the script as what re-runs the run.

## Impact

- Edited: `.agent-process/scripts/resolve_review_thread.py`,
  `.agent-process/scripts/review_gate.py`, `openspec/config.yaml` (one entry of
  `rules.tasks`), `.agent-process/docs/architecture/agent-process.md` (step 4),
  `tests/publisher/test_resolve_review_thread.py`,
  `tests/publisher/test_planning_workflow.py`, `tests/agent_process/test_review_gate.py`,
  ADR 0027, `openspec/specs/` (by the archive alone).
- Delivered on the open PR of the tracking issue (the second PR of issue 130), as the delta
  of that PR's review fix; no new issue, no new branch.
