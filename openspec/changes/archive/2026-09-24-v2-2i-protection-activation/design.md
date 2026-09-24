## Context

See `proposal.md` (Why). On `main` (`6b8f59f`), PR 165 (issue 153) landed the callee
`quality.yml` and the publisher caller `agent-process.yml`, whose job `agent-process` reports
`agent-process / quality`. The v1 `ci.yml` still reports the required `quality / quality`.
`init` never writes protection (`distribution`: `Init writes only the Project remotely`).
The v1 guard `check_branch_protection.py` runs on pre-push and compares **classic** protection
with `REQUIRED_CONTEXTS = (quality / quality, agent-review / agent-review)`. PR 151's
`upsert_ruleset` (branch `pr151`, `skills/agent-process/scripts/init.py`) and its
`templates/ruleset.json` are the code source; this change does not take them as an approved
plan. `test_package_contents_are_closed` forbids `ruleset` and `protection` in the file names
of the package. That boundary came from `v2-2g-a` for this issue.

## Observations

All on 2026-09-23, with `gh` authenticated as the owner:

- `gh api repos/ekolvah/agent-process-distribution/rulesets` lists exactly one ruleset:
  `{"id":23732345,"name":"agent-process default branch","source_type":"Repository","enforcement":"active"}`.
- `gh api …/rulesets/23732345` shows `conditions.ref_name.include ["refs/heads/main"]`, `exclude
  []`, `bypass_actors []`, and the rules `deletion`, `non_fast_forward`, and `pull_request`.
  The `pull_request` rule has `required_approving_review_count 0` and all of
  `dismiss_stale_reviews_on_push`, `require_code_owner_review`, `require_last_push_approval`,
  and `required_review_thread_resolution` set to `false`. The server also added
  `require_extra_approval_for_unattributed_changes: true` and `allowed_merge_methods
  [merge, squash, rebase]`, which PR 151's template does not carry. The last rule is
  `required_status_checks` with `strict_required_status_checks_policy true`,
  `do_not_enforce_on_create false`, and `[{"context":"quality / quality","integration_id":15368}]`.
- `gh api …/branches/main/protection` shows `required_status_checks.strict true`,
  checks `quality / quality` and `agent-review / agent-review` (both `app_id 15368`), and
  `enforce_admins true`. Issue 112's "classic protection no longer requires `agent-review /
  agent-review`" is not the live state.
- `gh api …/commits/9be0cbb…/check-runs` (PR 165 head) lists `agent-process / quality`,
  `quality / quality`, and `agent-review / agent-review`, each with app `github-actions` id
  `15368` and conclusion `success`. The composed name comes back as the check run's `name`.
  The same read with `?check_name=agent-process%20/%20quality` returns `total_count 1` and
  only that run.
- The GraphQL `repository.object(expression: "HEAD:.github/workflows/agent-process.yml")`
  returns `{"__typename":"Blob"}`. The same query for a missing path returns `null`, and
  `defaultBranchRef.name` is `main`.
- `gh pr view 165 --json headRefOid,baseRefName,state` prints `baseRefName main` and the head
  OID. A merged PR keeps its head OID.

## Goals / Non-Goals

**Goals:** a portable, explicit, idempotent command that makes `agent-process / quality`
required only after observing it, previews and reads back its writes, and converges the
publisher's live ruleset in place.

**Non-Goals:** writing classic protection. Deleting `ci.yml` and removing classic
`quality / quality` (the follow-up issue). Review and state migration (issue 114), the rest of
the v1 deletion (issue 115), consumer migration (issue 117), and the `v2.0.0` tag (the
person's action).

## Decisions

### D1. A separate script in the package, not an `init` step

`skills/agent-process/scripts/activate_protection.py --pr <N> (--dry-run | --confirm)` is
stdlib-only. It calls `gh` through `set_status.run_gh` (`Gh = Callable[[list[str]], str]`), and
tests inject the `Gh`. Consumers (issue 117) need it, so it lives in the package. The package
test drops `ruleset` and `protection` from its forbidden tokens, lists the script, and lists
`ruleset.json` as a template. `hook` stays forbidden. Exit codes are 0 for success, 2 for a
refusal (preflight, `conflict`, wrong usage), and 1 for a tool failure or a read-back mismatch.

Alternative: restore PR 151's `upsert_ruleset` in `init`. Rejected because a first install
cannot have observed the context yet, and this repository's `Init writes only the Project
remotely` would have to be reversed.

### D2. Preflight from two reads, before anything else

1. One GraphQL query returns `defaultBranchRef.name`, and returns
   `object(expression: "HEAD:.github/workflows/agent-process.yml")` as `null` or `Blob`
   (Observations). `null` is a refusal: `caller absent on <branch>`.
2. `gh pr view <N> --json headRefOid,baseRefName` must show `baseRefName` equal to the
   default branch; another base is a refusal. Then `gh api
   "repos/{owner}/{repo}/commits/<headRefOid>/check-runs?check_name=agent-process%20/%20quality"`.
   A check run must have `name ==
   "agent-process / quality"`, `app.slug == "github-actions"`, and `conclusion ==
   "success"`. Without one, the run refuses and prints every run of that name as `name app
   conclusion`, or `none`. Its `app.id` becomes the ruleset's `integration_id`.

The command checks the file's presence, not the job inside it. The observed check run proves
the composed name, and the caller file on the default branch lets later PRs report it. The PR
may be merged: its head OID stays readable. For this repository, delivery passes this change's
own PR, which is the "subsequent PR" that issue 153 asks for.

### D3. One ruleset converged by name over owned fields

`templates/ruleset.json` is PR 151's template, with `__DEFAULT_BRANCH__`, `__CONTEXT__`
(`agent-process / quality`), and `__INTEGRATION__` substituted. The owned fields are
`name`, `target`, `enforcement`, `conditions.ref_name`, `bypass_actors`, the set of rule
types, the five `pull_request` parameters in the template, and the three
`required_status_checks` parameters. Server-added keys (Observations) are not owned and are
not compared.

`gh api repos/{owner}/{repo}/rulesets` is listed, then filtered by name:

- 0 → `planned create` (`gh api -X POST … --input <tmp>`). Rollback: `gh api -X DELETE
  repos/<repo>/rulesets/<id printed by the write>`.
- 1 with `source_type == "Repository"` → `GET` by id, then compare the owned fields. Equal →
  `unchanged`. Otherwise `planned update <id>`, with one line per differing field (`field:
  live → desired`), via `gh api -X PUT …/rulesets/<id> --input <tmp>`. Rollback: the same
  `PUT` with the live owned body, which is printed as one JSON line.
- ≥ 2, or 1 not owned by the repository → `conflict` naming the ids. The run exits 2 before
  its first write.

The temporary input file is removed in `finally`. A retry after an interrupted write decides
again from the list, so it never creates a second ruleset. The run reads classic protection
(`gh api …/branches/<b>/protection`; an unprotected 404 prints `none`) and prints `classic:
<contexts> (not written)`. It issues no classic write.

### D4. Read-back of the written ruleset

After a `POST` or `PUT`, the run makes a `GET` by id and checks these fields in order:
`enforcement == active`, `conditions.ref_name.include == ["refs/heads/<default>"]` with empty
`exclude`, `bypass_actors == []`, and the rule types ⊇ {`pull_request`, `deletion`,
`non_fast_forward`, `required_status_checks`}. It then checks `strict == true` and the
required list equal to exactly `[{context, integration_id}]`. The first mismatch exits 1 as
`read-back: <field> is <observed>`. A successful run prints `written: ruleset <id>`.

### D5. The trust boundary: what stops proving and who catches it

The activation replaces a required trusted-driver context in the ruleset with a PR-owned
one, which is the guard this design drops.

- **Failure mode:** a publisher PR edits `ci_check.py` (or `quality.yml`, or the caller's
  `test`) so that `agent-process / quality` passes a head that the full checks would fail.
- **What stops proving:** the ruleset alone no longer proves that the trusted driver passed
  the head.
- **Catcher until the follow-up issue:** classic protection requires strict `quality /
  quality` from integration `15368` (Observations) with `enforce_admins true`. GitHub enforces
  it on the same head at merge, and it runs `reusable-quality.yml`'s default-branch driver.
  `check_branch_protection.py` fails the author's pre-push when classic protection loses it.
- **Catcher after the follow-up:** classic `agent-review / agent-review` runs on the same
  head. It is Codex's review or the Claude fallback of the driver diff. It is a review, not
  a re-run: a weakening the reviewer misses merges. The person accepted this on 2026-09-23.
  Issue 114, which owns that context, must name a successor before it removes it.
- **Pin:** `test_publisher_driver_keeps_a_same_head_catcher` asserts that
  `REQUIRED_CONTEXTS` still contains one of the two contexts. The pre-push guard proves that
  the live classic protection matches that declaration.
- **Consumers:** they call `quality.yml@v<version>`, an immutable callee, with their own
  `test`. The caller's command is the consumer's own trust, and the modified requirement is
  scoped to "this repository".

- **Accepted divergence:** `review_gate.py` (`evaluate`) decides `ready-for-human` from
  `REQUIRED_CONTEXTS`, the classic set, which does not contain `agent-process / quality`. On
  a head where that context is red and the classic contexts are green, the gate says ready
  while GitHub blocks the merge. The ruleset is the catcher on that head: the merge box shows
  the red required context to the person. `wait_for_pr` also waits for every check to
  conclude, and it prints each one's bucket. The two contexts run the same `ci_check.py`, so
  they diverge only when a PR changes the driver, and that is D5's failure mode. No check is
  added. The follow-up issue, which edits `REQUIRED_CONTEXTS`, adds the context there, and
  issue 115 deletes the gate.

`NOT_REQUIRED["agent-process"]` stays: the guard reads classic protection, where the context is
not required. Its reason becomes "required by ruleset `agent-process default branch` (issue
154); this guard reads classic protection only".

### D6. Install step and ADR row

`SKILL.md` `## Install` gains step 5. After the first PR shows `agent-process / quality`, run
`activate_protection.py --pr <N> --dry-run` (admin rights), show the whole output, ask once,
then run `--confirm`. ADR 0027 *Native alternatives considered* gains a row. The native
feature is `gh api` rulesets `POST`/`PUT`. It falls short because a raw write of a context
never observed blocks every merge (PR 151 run `35523639249`). The preflight, the one-name
convergence, and the read-back are the composition. The ADR's deletion conditions gain one:
GitHub refuses to require a check that has not reported on the repository → the script is
deleted.

## Risks / Trade-offs

- [A page of check runs holds 30 by default] → the server-side `check_name` filter
  (Observations) returns only runs of that name.
- [A server default that the template does not own changes later] → not compared, so it is
  not reverted. The rollback line carries only owned fields, as the `PUT` does.
- [The follow-up issue is forgotten while classic still requires `quality / quality`] → no
  merge is blocked, since `ci.yml` still reports. Each PR runs quality twice until the
  follow-up issue deletes `ci.yml`.

## Migration Plan

Delivery of this PR on this repository happens after `wait_for_pr` settles the first head.
Run `activate_protection.py --pr <this PR> --dry-run`: it shows `planned update 23732345`,
with `required_status_checks: quality / quality → agent-process / quality` and the rollback
line. Show the output to the person and run `--confirm` only on their yes. Then run
`--dry-run` again: it must print `unchanged`. The PR report carries all three outputs.
Classic protection stays unchanged. Merge after that is gated by the ruleset
(`agent-process / quality`) and classic (`quality / quality`, `agent-review / agent-review`),
all green on the head.

Rollback: run the printed `PUT` with the previous owned body **before** any revert of the PR,
then revert the PR. The PR changes no workflow, so a revert without the ruleset rollback
leaves `agent-process / quality` required and still reported.
