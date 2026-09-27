# Design

## Context

See proposal.md — Why. The installer composes each managed workflow from a
`skills/agent-process/templates/` file with `string.Template` (`render_workflow`) and owns it
by the first line `# agent-process:managed`; a file without that line is a `conflict`
(`_workflow_text`). `activate_protection.preflight` reads both callers in one GraphQL query
and today makes the review context conditional (`contexts(review_caller)`).

## Goals / Non-Goals

- Goal: every installed consumer carries the review caller and activation requires its check.
- Non-goal: changing `reusable-agent-review.yml`, the review contract, or the publisher's own
  caller. Non-goal: removing Codex from the callee and the process (a separate change).
  Non-goal: detecting whether the secret is present.

## Decisions

**D1 — A second managed template, rendered at the release tag.** Add
`templates/agent-review.yml`: the managed marker line, `on: pull_request` with `types:
[opened, synchronize]`, the publisher caller's permissions, and one job `agent-review` that
`uses: ekolvah/agent-process-distribution/.github/workflows/reusable-agent-review.yml@v${version}`
with no `with` and only `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}`
— the callee's only input, `codex-timeout-seconds`, is optional and leaves with Codex, so
the caller survives that removal unchanged.
The installer writes it as step `review` right after `workflow`, with the same ownership rule
(`_workflow_text` generalised over the path and renderer). `_template` uses
`string.Template.substitute`, which raises `ValueError: Invalid placeholder` on a bare
`${{ ... }}` (verified by the architect review), so the template spells each GitHub
expression `$${{ ... }}` (`$$` renders `$`) and `substitute` stays strict — a missed
placeholder keeps failing loudly. The render test asserts the rendered text carries
`${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` verbatim.
Alternative: `@main`, as the publisher calls it. Rejected: a consumer would run whatever
lands on `main` without an install step; the release tag matches `quality.yml` and ADR 0012's
pin for consumers.
Alternative: a second job `agent-review` in the managed `agent-process.yml` — no new template,
footprint path or conflict case. Rejected: the review subscribes to `opened, synchronize`
only (a review-event run would become a context of its own, `test_agent_review_caller_runs_on_pushes_alone`)
while quality runs on every `pull_request` type; the review needs `pull-requests: write`;
and `resolve_review_thread.py` re-runs the head's run of `agent-review.yml` by file name
(`_gh_head_run`), which in one file would re-run quality too. The consumer file also matches
the publisher's, which `activate_protection` reads by path.

**D2 — The review secret is a `manual` row.** `_manual` gains one row, printed on
every dry-run and confirmed run: `manual review-secret:
https://github.com/<repo>/settings/secrets/actions -- set CLAUDE_CODE_OAUTH_TOKEN`, where `<repo>` is the
consumer's `owner/name` that `_project_steps` already reads through `_repository`: it returns
that slug beside the URL and `_manual(url, repo)` takes it (`ctx.repository` is the publisher's
slug and is not used). The installer writes
no secret (requirement "Init writes only the Project remotely"). Alternative: read `gh secret
list` and print the row only when absent. Rejected: a new read and state for a row the person
reads once; a missing secret still surfaces as a red `agent-review` on the install PR, which
activation refuses (D3).

**D3 — Activation requires the review caller unconditionally.** `preflight` refuses with
`refused: caller absent on <branch>: .github/workflows/agent-review.yml` when the `review`
object is null, checked after the quality caller; `contexts()` loses its parameter and returns
both contexts. This adds a guard; no proof is lost. A consumer installed by 2.2.0 has no review
caller and is refused until it reruns `init` and merges the result — the refusal names the
missing file.

**D4 — The reusable/caller split stays.** With a consumer caller the callee has a second
caller, which answers issue #215. Merging into one file was rejected by the person, and would
let a PR rewrite the review steps it is judged by, because a `pull_request` run takes the
workflow file from the PR.

**D5 — ADR 0032** records "the review gate is installed in every consumer": context (#215),
the decision (D1–D3), the rejected merge, and the deletion condition — the process stops
depending on a review check. ADR 0020/0022/0031 stay valid: they describe the callee, which is
unchanged.

## Risks / Trade-offs

- [The consumer sets no secret] → the Claude review fails, the install PR's `agent-review`
  is red, and activation refuses; the `manual` row and SKILL Install step 4 name the secret.
- [Codex still in the callee when this lands] → every consumer head waits the callee's
  default 600 s for a Codex review that never comes, then Claude reviews; slower, not
  broken, and gone with the Codex-removal change.
- [A consumer already has its own `agent-review.yml`] → `conflict`, exit 2 before any write;
  the person removes or renames it.

## Migration Plan

Released as a minor bump with a breaking note (activation). Existing consumers rerun `init`
for the new release, set the secret, merge the install PR, then rerun activation. Rollback:
revert the PR; installed consumer callers keep pointing at the old tag and keep working.
