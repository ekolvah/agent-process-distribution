## Context

For motivation, see proposal.md (Why). Issue 114's brief predates `v2-2b` … `v2-2j`, and these
are the answers already on record:

- **Review credential**: the caller passes `secrets.CLAUDE_CODE_OAUTH_TOKEN` explicitly
  (`.github/workflows/agent-review.yml:21`) into the callee's required secret
  `claude_code_oauth_token` (`reusable-agent-review.yml:19-21`). Nothing is left for this
  change.
- **Deferred scope on change branches**: ADR 0027 (More Information) says "the downgrade left
  the contract in `v2-2b`, the verification leaves with `verify_pr_link` (`v2-2c`)". Neither
  half exists, so the either/or is closed.
- **Does Codex review on open without a trigger?** Closed by the owner's decision in `v2-2b`
  (ADR 0027, Observations: "Codex's automatic reviews: closed"). Automatic reviews stay off,
  and the author requests every review.
- **Does the Claude review run on every push?** The caller runs on `pull_request` alone, and
  the review-event trigger was withdrawn (ADR 0027, Observations, 2026-09-17). The fallback
  runs on a push whose head Codex left silent.
- **"Advisory review"** in the brief: `v2-2b` decided that `P0`/`P1` threads block through the
  required check, and on 2026-09-24 the owner confirmed that the check stays required and
  moves into the ruleset.

## Goals / Non-Goals

**Goals:** after this change, no v1 script takes part in a v2 delivery's review or protection,
and the default branch has a single protection mechanism.

**Non-Goals:** the v1 issue and state scripts (`v2-4b`); `agent_orchestrator.py`,
`roles.yaml` and `copier-answers.yml` (issue 115); moving `request_codex_review.py` or
`check_blocking_review_threads.py` under `skills/`. The review check's behaviour is not changed.

## Decisions

**D1. `review_gate.py` is deleted; `wait_for_pr.py` is the last Deliver step.**
- The gate answered three questions, and each has another catcher:
  - Red or pending contexts on the head: `wait_for_pr.py` exits 1 and names the failed check
    (`tests/publisher/test_delivery_scripts.py`, `failed: agent-review`), or exits 3 on its
    timeout, on the same head.
  - The fixer budget (distinct reviewed heads): the three-round cap is already prose in the
    `tasks` rule (ADR 0027, "Review budget"), and the person, who merges, sees each round.
  - `.review_gate_stamp`: only the Stop gate read it (D2).
- What stops being proven: that the agent stops after three rounds. No script reads the round
  count. The person is the catcher at merge. This is the ADR 0027 decision "the person is the
  only gate".
- Alternative, keeping the gate and reading only the ruleset list: rejected, because it would
  add a stamp and a verdict table on top of a wait whose exit code already says the same.

**D2. The Stop turn gate is deleted.**
- `delivery_state.decide` returns `allow` for any branch that `is_valid_branch_name` rejects.
  That is every v2 branch (proposal, observation 2026-09-24), so on v2 the gate proves nothing
  today.
- On a v1 `issue-*` branch it would still block. That flow ends with `v2-4b`, and the last
  `issue-*` branch on the remote is `issue-101-…`. Between this change and `v2-4b`, a v1
  delivery loses its turn gate. Its catcher is the same as for v2: `wait_for_pr.py`, and the
  person.
- Alternative, keeping the hook and teaching it v2 branch names: rejected. It would need the
  deleted gate's stamp, or a new one, which is a new bespoke check that ADR 0027 replaces with
  the person.

**D3. `activate_protection` derives the contexts from the callers on the default branch.**
- The preflight's one GraphQL read also asks for `HEAD:.github/workflows/agent-review.yml`.
  The context list is `agent-process / quality` plus `agent-review / agent-review` when that
  object exists.
- Each context goes through the existing check-run preflight: a GitHub Actions `success` on
  the PR head. Each context binds the `app.id` of its own run. Observed on 2026-09-24: the
  check runs of PR 171's head `f800f15a` include `agent-review / agent-review`,
  `github-actions`, app id `15368`, `success`.
- The template's `required_status_checks` array is built from that list instead of one
  placeholder entry. `read_back` and `plan`'s `owned_fields` compare it as a set of
  (context, integration) pairs, sorted by context. GitHub's returned order has not been
  observed with two entries (the live ruleset has one), so the comparison does not depend on
  it.
- A consumer without the review caller gets exactly what it gets today.
- Failure modes of the new input, the caller's presence:
  - A caller that exists but never ran green → refusal with reads only. This is the PR 151
    lesson, and the reason the preflight exists.
  - A caller whose secret is missing → its run is red → refusal.
  - A caller added after activation → the ruleset lacks it until the next run. The dry-run
    prints `planned update` with the diff.
- Alternative, `--context` repeatable from the caller: rejected. A typed name that never
  reported blocks every merge, and the caller file on the default branch is the declaration
  the repository already has.
- Alternative, leaving `agent-review` in classic protection: rejected by the owner, because it
  keeps two protection mechanisms and a drift checker.

**D4. `check_branch_protection.py` and `install_branch_protection.py` are deleted, and so is
the pre-push probe.**
- What stops being proven:
  - The local comparison of classic protection with a declared list before each push.
  - The workflow audit that every `pull_request` job is declared or excluded
    (`test_branch_protection.py::TestDeclarationMatchesWorkflows`).
- Catchers:
  - The ruleset is enforced by GitHub on merge.
  - `activate_protection --dry-run` reads the live ruleset and prints `unchanged` or the
    differing fields. The person runs it, and it is the one read that sees the installed
    protection.
  - A declared context that is not a real job cannot be activated, because the preflight needs
    its successful run on a head.
  - An undeclared job is not required, which is the ruleset's normal semantics.
- `v2-2i`'s activation spec already says "classic branch protection is read and printed, never
  written". After the migration it prints `classic: none (not written)`.

**D5. `request_codex_review.py` keeps `--wait` and loses `--request`.**
- The `--wait` mode is the review check's presence reader (`reusable-agent-review.yml:64,110`).
  It is `v2-2b` behaviour, and the check keeps it.
- `--request` is `run_gh(["pr", "comment", pr, "--body", "@codex review"])`, which is the
  native command itself. The Deliver rule names that command.
- `check_review_credentials.py` imports only `CODEX_REVIEWER`, which is unchanged.

**D6. The pre-push tests move with the hook.**
- `TestPrePushHook` tests the hook script, not the deleted checker.
- It moves to `tests/agent_process/test_pre_push_hook.py`, without
  `test_protection_probe_runs_before_ci_check`, `test_allow_drift_reason_reaches_protection_probe`
  and `test_drift_blocks_push_without_running_ci_check`.
- It gains `test_push_runs_ci_check_alone`: the recorded calls are exactly one `ci_check.py`.

## Risks / Trade-offs

- [The ruleset is written from the PR branch before its code is on `main`] → The person runs
  `activate_protection --confirm` from the PR's checkout, once its head is green. The written
  ruleset only adds a context that classic protection already requires, so the order is safe.
  The rollback line is printed.
- [Classic protection is deleted while the ruleset lacks `agent-review`] → Migration step 2
  runs only after step 1's read-back and the dry-run print `unchanged` with both contexts.
- [A merge between the steps] → Classic protection and the ruleset overlap on the context
  during the window. Neither step removes a barrier before its replacement exists.

## Migration Plan

The person runs these steps on the PR's green head, before merge:

1. Run `python skills/agent-process/scripts/activate_protection.py --pr <PR> --dry-run` and
   read the output, then run it with `--confirm`. Expect `planned update 23732345` with
   `required_status_checks.required_status_checks` gaining `agent-review / agent-review`,
   then `written: ruleset 23732345`. Rollback: the printed `PUT` line.
2. Save classic protection with
   `gh api repos/ekolvah/agent-process-distribution/branches/main/protection > classic.json`,
   then delete it with `gh api -X DELETE repos/ekolvah/agent-process-distribution/branches/main/protection`.
   Rollback: rebuild the body from `classic.json`: required status checks `strict: true`,
   contexts `["agent-review / agent-review"]`, `enforce_admins: true`, and `null` for
   `required_pull_request_reviews` and `restrictions`. Send it with
   `gh api -X PUT …/branches/main/protection --input <body>`.
3. Run the dry-run again. Expect `unchanged 23732345` and `classic: none (not written)`.
   Paste the output into the PR body.

## Observations

Recorded in ADR 0027 by task 4.4: the Stop gate's branch predicate on v2 branch names; the
classic and ruleset contexts before the migration; the dry-run output after it.
