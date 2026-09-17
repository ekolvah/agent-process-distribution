## Why

Step 2b of the v2 plan (#107, tracking issue #130): the review *mechanism* is still v1 — a
277-line workflow with 15 steps that parses Codex's native review into evidence, validates
Claude's structured output against a JSON schema, classifies every thread with a
`BLOCKING`/`NON-BLOCKING` reply, diagnoses a failed Claude run and enforces an outcome. Every
one of those steps reads the *meaning* of a review; every one has broken on a format change
of one of the apps. ADR 0027 decided the review is the apps' own and nothing of ours parses it.

Three decisions of the person on this proposal (solution review, 2026-09-17), which amend the
text of the tracking issue (#130):

- **One reviewer per head, as today.** Codex is the primary reviewer; Claude runs only as
  the fallback when no Codex review of the head arrives within the bounded wait — the
  expected case being Codex out of quota (it then posts `You have reached your Codex usage
  limits for code reviews` instead of a review, which the wait does not read: no review on
  the head is no review). Two reviews on every push is a token cost the person does not want.
- **Codex is requested, not automatic.** The Deliver rule keeps posting `@codex review`
  after `gh pr create` and after every push, so the number of Codex reviews stays the
  number of pushes the agent decides to make. *Automatic reviews* in the Codex app is not
  enabled: its "On PR open" trigger would leave every later push to the Claude fallback,
  and its "On every push" trigger reviews exactly as often as the rule does, only outside the
  agent's control (Codex settings → Code review; docs and openai/codex #15477, #32224).
- **A `P0`/`P1` thread keeps the PR from merging through a required check**, not through
  GitHub's conversation resolution, which treats a `P3` nit like a `P0`. The check reads the
  label of a thread's first comment and its resolved state — nothing else — and replies to
  no thread.

## What Changes

- **The review job keeps its shape and loses its parser.** `reusable-agent-review.yml`
  becomes five steps: checkout of the PR head, checkout of the trusted review source (this
  repository at the ref the caller pinned, `github.job_workflow_sha`, so a consumer needs no
  process file), *Wait for the Codex review of the head* (`request_codex_review.py --wait`,
  a present/absent read, never a parse), *Claude review* (`anthropics/claude-code-action@v1`
  with the trusted contract, only when the wait ended absent) and *Enforce unresolved
  P0/P1 threads* (`check_blocking_review_threads.py`, no reply). The
  `codex-timeout-seconds` input stays; the bootstrap fallbacks, the outcome classifier, the
  evidence publication, the diagnostic and the JSON schema go. The wait and the Claude step
  run only on `pull_request` events, so a later PR can let the check follow review events.
- **The request stays the rule's.** `request_codex_review.py --request` after
  `gh pr create` and after every push, as today; the rule loses only its `(v1, until v2-4)`
  note and the `BLOCKING` wording.
- **`request_codex_review.py`** keeps `--request` (and `CODEX_REVIEWER` for
  `check_review_credentials.py`) and gains `--wait`: one GraphQL read of the PR's reviews
  and comments, true when a review by `chatgpt-codex-connector` is on the head or its clean
  comment names the head (`Reviewed commit:` prefix), exit 3 after `--timeout-seconds`.
  The parser half (`find_verdict`, `poll_for_verdict`, the evidence records, the reaction
  reads, `STANDARD_REVIEW_PARSER`) and its tests go.
- **`check_agent_review_outcome.py`** and its test are deleted.
- **`check_blocking_review_threads.py`** stays as the gate and loses its replies: no
  `_publish_classifications`, no marker, no `classified`; it accepts a `P0`/`P1` first
  comment by either reviewer login (`chatgpt-codex-connector`, `github-actions` — the login
  the action's inline comments carry under `github.token`) and prints `unresolved P0/P1
  review threads:` with the URLs. `resolve_review_thread.py` reads through it unchanged,
  so the fixer resolves a `P0`/`P1` thread of either reviewer it addressed and nothing else.
- **Required contexts, branch protection, `wait_for_pr.py`: unchanged.** The check still
  waits for the review or runs the fallback, so a running `agent-review` check is still a
  pending review for `wait_for_pr`; only its docstring's `v2-4` sentence goes.
- **`REVIEW_CONTRACT.md`** is reduced to what a reviewer needs: what to look for, the
  `P0`–`P3` scale with the two narrow §VII triggers (still coupled to `principles.md` by
  test), no re-raising of answered findings, the reviewed head in every publication, no
  review state, no merge. The transports, the structured-output schema, the
  `BLOCKING`/`NON-BLOCKING` labels and the deferred-scope downgrade go; ADR 0020's
  generate/verify halves (`open_pr.py`, `verify_pr_link.py`, `check_orphan_scope.py`) stay
  inert until `v2-2c`, which the ADR 0027 observation records.
- **A second, small PR after the first merges: the check follows review events.** The
  caller `agent-review.yml` gains `pull_request_review: [submitted]` and
  `pull_request_review_thread: [resolved, unresolved]`; on those events the job runs only
  the enforce step, so a resolve by the fixer and a Codex review that lands after the wait
  re-run the check without `gh run rerun`. That PR deletes the "before the run reaches its
  last step / `gh run rerun`" clause from the Deliver rule. Separate because on the first PR
  the caller still points at the v1 workflow on `main`, which would run its whole chain —
  Claude included — on every thread event.
- **ADR 0027** gains *Observations from v2-2b* — the open questions (#114) on Codex's automatic
  reviews are closed by decision (not enabled; the request is the rule's), the rest by
  observation: did the Claude fallback run and what it cost; the login its comments carry;
  whether a check run started by a review event is listed for the head. The installation
  guide's step 4 names the token as the fallback credential and what the check fails on;
  its sentence that the workflow never posts `@codex review` nor enables automatic reviews
  stays true.

## Capabilities

### New Capabilities

none

### Modified Capabilities

- `review-and-merge`: "Codex reviews on the author's request, Claude is the fallback"
  (present/absent instead of evidence; an error or limit message from Codex is absence;
  review events run the enforcement only); new "Unresolved P0/P1 threads fail the review
  check"; "No automation resolves a review thread"
  (no classification reply; the fixer resolves a `P0`/`P1` thread of either reviewer it
  addressed); "Reviewer instructions name the simplicity triggers" (the contract is the
  prompt file both apps read). "Required checks protect the default branch" is unchanged.
- `implementation`: "Delivery steps are tasks of every change" (`P0`/`P1` and `P2`/`P3`
  wording; no re-run by hand once the check follows review events).

## Impact

Removed:

- `.agent-process/scripts/check_agent_review_outcome.py`,
  `tests/publisher/test_agent_review_outcome.py`

Edited (first PR):

- `.github/workflows/reusable-agent-review.yml` (rewritten)
- `.agent-process/REVIEW_CONTRACT.md`
- `.agent-process/scripts/request_codex_review.py`, `tests/publisher/test_request_codex_review.py`
- `.agent-process/scripts/check_blocking_review_threads.py`,
  `tests/publisher/test_blocking_review_threads.py`
- `.agent-process/scripts/resolve_review_thread.py` (docstring),
  `tests/publisher/test_resolve_review_thread.py` (one case: a `P1` by the action's login)
- `.agent-process/scripts/wait_for_pr.py` (docstring)
- `.agent-process/scripts/open_pr.py`, `.agent-process/scripts/verify_pr_link.py` (one comment
  line each no longer points at a deleted file)
- `openspec/config.yaml`, `tests/publisher/test_planning_workflow.py`
- `tests/publisher/test_reusable_workflows.py`
- `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`
- `.agent-process/docs/architecture/agent-process-installation.md` (step 4)
- `openspec/specs/review-and-merge/spec.md`, `openspec/specs/implementation/spec.md` (by the
  archive)

Edited (second PR): `.github/workflows/agent-review.yml`, `openspec/config.yaml`,
`tests/publisher/test_planning_workflow.py`, `tests/publisher/test_reusable_workflows.py`,
ADR 0027 (one observation line).

Untouched: `check_branch_protection.py` and its tests, `test_review_gate.py`,
`test_delivery_scripts.py`, the classic protection of `main`, the `CLAUDE_CODE_OAUTH_TOKEN`
secret.

No setting changes: *Automatic reviews* in the Codex app stays off. Text the person amends in the tracking issue (#130):
"enable automatic code reviews", "the review job stops being a required check … add
`required_review_thread_resolution`" and "both apps review every PR" are superseded by the
decisions above.

Out of scope (per the issue): `init` printing the Codex enablement (#112); deleting
`request_codex_review.py` and `review_gate.py` while v1 paths reference them (#115);
`agent-process.md`, the v1 procedure, keeps its stale review steps until the v1 removal (#115).
