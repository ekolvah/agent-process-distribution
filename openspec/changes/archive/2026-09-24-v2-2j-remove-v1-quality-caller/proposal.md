## Why

Every PR of this repository runs the quality driver twice. PR 167 (issue 154) switched ruleset
`23732345` to require `agent-process / quality`. Classic protection still requires `quality /
quality`, which the v1 caller `.github/workflows/ci.yml` reports
([issue 166](https://github.com/ekolvah/agent-process-distribution/issues/166), parent 112).
Design D5 of `v2-2i-protection-activation` kept that context only as the trusted-driver
catcher until this step. It names classic `agent-review / agent-review` on the same head as
the catcher that follows.

Observations on 2026-09-24 (commands and output in `design.md`, Observations):

- Ruleset `23732345` requires strict `agent-process / quality` from integration `15368`.
- Classic protection requires strict `quality / quality` and `agent-review / agent-review`,
  both from `app_id 15368`, with `enforce_admins true`.
- On PR 167's head, `statusCheckRollup` lists the check runs `agent-review / agent-review`,
  `quality / quality`, and `agent-process / quality`, all `SUCCESS`.

`review_gate.py` judges only `REQUIRED_CONTEXTS`, the classic set (D5, "Accepted
divergence"). Once `quality / quality` leaves that set, no context of the gate runs the quality
driver. The gate would then report `ready-for-human` on a head whose `agent-process / quality`
is red.

## What Changes

- Delete `.github/workflows/ci.yml`. Each PR runs quality once, as `agent-process / quality`.
- `check_branch_protection.py`: `REQUIRED_CONTEXTS` becomes `("agent-review / agent-review",)`.
  A new `RULESET_CONTEXTS = ("agent-process / quality",)` declares what the ruleset requires.
  The pre-push guard still compares only `REQUIRED_CONTEXTS` with classic protection, and
  `NOT_REQUIRED["agent-process"]` stays.
- `review_gate.py` judges `REQUIRED_CONTEXTS` plus `RULESET_CONTEXTS`. A red or pending
  `agent-process / quality` is `fix-blocking` or `review-pending`, not `ready-for-human`.
- Before merge, the person removes `quality / quality` from classic protection with the
  reference `DELETE …/protection/required_status_checks/contexts` call. The process writes no
  protection.
- `distribution`: the same-head catcher is `agent-review / agent-review` alone. The quality
  driver runs once per PR. `review-and-merge`: the default branch requires `agent-process /
  quality` through the ruleset and `agent-review / agent-review` through classic protection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: remove `CI runs the trusted driver, not the PR's copy`, together with its
  scenario `Quality check on a PR`. Add `A context the PR cannot change gates every head`,
  which keeps `PR weakens its own driver` and adds `Quality runs once per PR`.
- `review-and-merge`: modify `Required checks protect the default branch`, and add the scenario
  `Ruleset context red`.

## Impact

- Removed: `.github/workflows/ci.yml`.
- Edited: `.agent-process/scripts/check_branch_protection.py` (`REQUIRED_CONTEXTS`,
  `RULESET_CONTEXTS`), `.agent-process/scripts/review_gate.py` (the judged contexts),
  `.agent-process/scripts/ci_check.py` (a docstring that names `ci.yml`),
  `.github/workflows/agent-process.yml` (a header comment),
  `tests/publisher/test_reusable_workflows.py`, `tests/agent_process/test_review_gate.py`,
  `tests/agent_process/test_branch_protection.py`, `tests/agent_process/test_ci_check.py`.
- Docs: the installation guide and ADR 0019 describe the v1 consumer layout, and
  `.agent-process/copier-answers.yml` is the dead copier record. All three stay until issue
  115.
- External systems: the person removes `quality / quality` from classic protection of `main`.
  The ruleset is not changed.
