## Context

See `proposal.md` (Why). On `main` (`8f03228`), `.github/workflows/ci.yml` calls
`reusable-quality.yml@main` as job `quality`, and `agent-process.yml` calls `./quality.yml` as
job `agent-process`. Both run `ci_check.py` on every PR.
`.agent-process/scripts/check_branch_protection.py` declares `REQUIRED_CONTEXTS = (quality /
quality, agent-review / agent-review)`, and the pre-push guard compares that tuple with
**classic** protection. `review_gate.py` imports the same tuple for `evaluate`.
`install_branch_protection.py` and its tests also read it.

## Observations

All on 2026-09-24, with `gh` authenticated as the owner:

- `gh api repos/ekolvah/agent-process-distribution/branches/main/protection` prints
  `checks [{"app_id":15368,"context":"quality / quality"},{"app_id":15368,"context":"agent-review
  / agent-review"}]`, `strict true`, `enforce_admins true`.
- `gh api …/rulesets/23732345` prints the `required_status_checks` parameters
  `{"required_status_checks":[{"context":"agent-process / quality","integration_id":15368}],
  "strict_required_status_checks_policy":true,…}`.
- `gh pr view 167 --json statusCheckRollup` prints three `CheckRun` entries named
  `agent-review / agent-review`, `quality / quality` (workflow `CI`), and `agent-process /
  quality` (workflow `agent-process`), all `SUCCESS`. `review_gate.py` reads this field, and the
  composed name is the one it compares.

## Goals / Non-Goals

**Goals:** each PR runs quality once. The review gate judges every context that GitHub
requires. The pre-push guard keeps comparing only classic protection.

**Non-Goals:** writing protection, whether classic or ruleset. Removing `reusable-quality.yml`,
`install_branch_protection.py`, the v1 guard, the copier record, and the v1 installation docs
(issue 115). Review and state migration (issue 114). Consumer migration (issue 117).

## Decisions

### D1. Delete `ci.yml`

Delete `ci.yml` alone. `reusable-quality.yml` stays for v1 consumers, which call it `@main`
(issue 115). The tests that read `ci.yml` lose those reads:

- `test_reusable_workflows.py`: drop the `ci.yml` pairs in the caller/callee schema and
  permission tests. Drop the `ci.yml` line in
  `test_quality_executes_a_trusted_driver_against_the_pr_worktree`, and the two `ci.yml` lines in
  `test_quality_verifies_the_pr_links_its_issue_before_the_driver`. The callee assertions stay.
- `test_ci_check.py`: drop `TestStepParity::test_ci_yml_cannot_select_a_subset_of_checks` and
  `_quality_caller`. `test_publisher_caller_reaches_callee_by_same_commit_path` already pins
  `agent-process.yml`'s `test` to exactly `python .agent-process/scripts/ci_check.py`.

A new test, `test_quality_runs_once_per_pr`, collects every job of a `pull_request` workflow
whose `uses` names `quality.yml` or `reusable-quality.yml`. It asserts that the result is exactly
`agent-process.yml` / `agent-process`.

### D2. Two declared lists, one per protection mechanism

In `check_branch_protection.py`:

- `REQUIRED_CONTEXTS = ("agent-review / agent-review",)` is classic protection. The guard, its
  drift comparison, and `install_branch_protection.py` keep reading only this tuple.
- `RULESET_CONTEXTS = ("agent-process / quality",)` is new. It declares what ruleset `agent-process
  default branch` requires. No guard compares it with the live ruleset.
- `NOT_REQUIRED["agent-process"]` and its reason stay. The guard reads classic protection, where
  the context is not required, and the offline declaration check keys on the job.

`review_gate.evaluate` judges `(*REQUIRED_CONTEXTS, *RULESET_CONTEXTS)` for pending and red.
This resolves D5's "Accepted divergence" of `v2-2i-protection-activation`: a red or absent
`agent-process / quality` is `fix-blocking` or `review-pending`.

Alternative: the gate reads the live rules with `gh api repos/{o}/{r}/rules/branches/<b>`.
Rejected, because it adds a remote read and a parser to a script that issue 115 deletes. The
gate's other data is also declared in the repository.

Alternative: add the context to `REQUIRED_CONTEXTS`. Rejected, because the guard would then
report classic drift on every push.

### D3. The trust boundary after `quality / quality` leaves

D5 of `v2-2i-protection-activation` applies unchanged. The dropped guard is the trusted-driver
context.

- **Failure mode:** a PR edits `ci_check.py`, `quality.yml`, or the caller's `test` so that
  `agent-process / quality` passes a head the full checks would fail.
- **What stops proving:** no required context runs a driver the PR cannot change.
- **Catcher:** classic `agent-review / agent-review`, strict, from `app_id 15368`, with
  `enforce_admins true` (Observations). GitHub enforces it on the same head at merge. It is
  Codex's review, or the Claude fallback's, of the diff that edits the driver. The person
  accepted on 2026-09-23 that a weakening the reviewer misses merges. Issue 114 must name a
  successor before it removes that context.
- **Pin:** `test_publisher_driver_keeps_a_same_head_catcher` now asserts
  `"agent-review / agent-review" in REQUIRED_CONTEXTS`, which is the new scenario's exact
  outcome. The pre-push guard proves that live classic protection still carries it.

### D4. Documentation and comment edits

The header comment of `agent-process.yml` says that the ruleset requires the context (issue 154),
and it no longer names `ci.yml`. The `check_secrets` docstring of `ci_check.py` names
`agent-process.yml` in place of `ci.yml`. The installation guide, ADR 0019, and
`.agent-process/copier-answers.yml` describe the v1 consumer layout, and issue 115 owns them.

## Risks / Trade-offs

- [`RULESET_CONTEXTS` drifts from the live ruleset] → if the ruleset names a context the gate
  does not know, the merge box shows it to the person, who merges. If the gate names a context
  that never reports, the result is a visible `review-pending`. `activate_protection.py
  --dry-run` shows the live required context.
- [The installer tests index `REQUIRED_CONTEXTS[0]` and `[1:]`, which assumes two entries] →
  they are rewritten so that the fixture policy carries only a consumer context and the
  expectations use the whole tuple. They pass on `main` and after the change.
- [PR opened before classic `quality / quality` is removed] → the PR no longer reports `quality
  / quality`, so GitHub blocks its merge until the person runs the Migration Plan's `DELETE`.
  The pre-push guard treats the still-required context as a preserved extra, not as drift.

## Migration Plan

After `wait_for_pr` settles the head with `agent-process / quality` and `agent-review /
agent-review` green, show the person this command and let them run it. The process issues no
protection write.

```
gh api -X DELETE repos/ekolvah/agent-process-distribution/branches/main/protection/required_status_checks/contexts -f 'contexts[]=quality / quality'
```

Then read `gh api …/branches/main/protection --jq '.required_status_checks.checks'`. It must
list only `agent-review / agent-review` (`app_id 15368`). The PR report carries that read.

Rollback: restore the classic list with its app ids first, then revert the PR, which restores
`ci.yml`:

```
echo '{"strict":true,"checks":[{"context":"quality / quality","app_id":15368},{"context":"agent-review / agent-review","app_id":15368}]}' | gh api -X PATCH repos/ekolvah/agent-process-distribution/branches/main/protection/required_status_checks --input -
```
