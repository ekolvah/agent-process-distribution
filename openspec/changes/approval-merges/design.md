## Context

The delivery procedure (`skills/agent-process/SKILL.md#delivery`) runs `archive_change`,
`gh pr create`, then the `wait_for_pr` loop. This repository allows only squash merges and
allows auto-merge (`gh api repos/ekolvah/agent-process-distribution`: `allow_auto_merge: true`,
`allow_squash_merge: true`, `allow_merge_commit: false`, `allow_rebase_merge: false`), set by
hand for the release PR (ADR 0031 D4); no script of the process sets it in a consumer.

GitHub, "Automatically merging a pull request": "People with write permissions to a repository
can enable auto-merge for a pull request."; "Auto-merge is disabled if someone without write
permissions pushes new changes to the head branch"; "Before you use auto-merge, it must be
enabled for the repository."; "The option to enable auto-merge is shown only on pull requests
that cannot be merged immediately." The bot is a write collaborator (ADR 0040 D1).

## Goals / Non-Goals

**Goals:** the person's approval is the one action that merges the agent's PR, and nothing
merges a PR the platform does not hold for an approval.

**Non-Goals:** any change to the approval ruleset; converging the allowed merge methods.

## Decisions

### D1 — One script, gated on `reviewDecision`

`enable_auto_merge <PR>` reads `gh pr view <PR> --json reviewDecision` and runs
`gh pr merge <PR> --auto --squash` only on `REVIEW_REQUIRED`. The standard for the job is
`gh pr merge --auto --squash`; it does not fit alone, because in a repository where no rule
asks for an approval (no `agent_identity` run) auto-merge would merge the agent's PR on its
checks alone, and on a PR that can merge at once GitHub offers no auto-merge — what `gh --auto`
then does is unobserved and the gate makes it irrelevant. `reviewDecision` is GitHub's own
evaluation of the rules for that PR, so it covers the `agent-process person approves` ruleset,
other rulesets and classic protection alike. Unobserved: the value in the first seconds after
`gh pr create`; any other value fails toward the status quo (exit 1, the person merges), and
task 5.3 observes it on this change's own PR.

Exit codes: 0 enabled, 1 not enabled and the person merges, 2 `gh` failed with its message
(§IV: no silent branch). It uses the `set_status` seam as `agent_identity` does — `Gh`,
`run_gh` as the injected default (§II), `_json` for the read — and exit 2 is the `RuntimeError`
`run_gh` raises with gh's stderr.

Alternatives:
- A shell line in SKILL.md (`[ "$(gh pr view …)" = REVIEW_REQUIRED ] && gh pr merge …`) —
  its false branch is silent and only the text is testable.
- Check for the ruleset by name — misses classic protection and other rulesets, and reads
  repository config instead of the PR's own state.
- One script that also runs `gh pr create` — more general, larger than the issue needs.

### D2 — Squash, once, right after `gh pr create`

Squash is the only method this repository allows, the release PR uses it, and it makes the
PR title `<type>: <change>` the commit headline release-please reads. It runs once: a push by
the bot (write permission) keeps auto-merge enabled, while the ruleset dismisses a stale
approval on push (`dismiss_stale_reviews_on_push`, ADR 0040 D2), so the PR waits for a new one.

### D3 — `agent_identity` allows auto-merge

GitHub leaves `allow_auto_merge` off, so without a transition every consumer would reach exit 2
of D1. `agent_identity` already converges the ruleset whose approval D1 reads; one more
transition reads `gh api repos/<repo>` `allow_auto_merge` and, when it is not true, plans
`gh api -X PATCH repos/<repo> -F allow_auto_merge=true`, run as the person (ADR 0040 D6) under
the same `--dry-run`/`--confirm` and re-plan. A consumer that disallows squash still gets exit 2
of D1 with gh's message, and the person merges.

### D4 — ADR 0040 gains D7

D2 of ADR 0040 already allows auto-merge; D7 records that the agent enables it, gated as D1
says, that `agent_identity` allows it, and that `wait_for_pr` stops on a merged PR (D5). No
new ADR.

### D5 — `wait_for_pr` stops on a PR that is no longer open

With auto-merge on, an approval during the review loop merges the PR; a corrective push after
that recreates the deleted branch with no PR, and the fix silently reaches nothing. The head
read of every poll becomes `gh pr view <PR> --json headRefOid,state` — the same call, no extra
request — and a `state` other than `OPEN` prints the state and that a push after it is not in
the PR, and exits 4 before checks or threads are read. A merge during the wait stops the loop
before the fix; a push already made after the merge is caught by the `wait_for_pr` run that
follows it. Delivery stops on exit 4 and reports to the person.

Alternatives:
- A pre-push hook reading the PR state — a network call in every push, and it breaks offline
  work.
- A rule in SKILL.md to check the state before each push — prose, not testable (§VII).
- Disable auto-merge while the loop runs and enable it at the end — the person's approval
  during the loop would again need a second action.

## Risks / Trade-offs

- [A P2/P3 finding still being answered when the approval merges the PR] → exit 4 reports it,
  and the person, who approved with the threads in view, decides on a follow-up.

## Migration Plan

Consumers get the script and the procedure with the next plugin release; a consumer that ran
`agent_identity` before it plans the `auto-merge` transition on its next `--dry-run`. Rollback:
revert the PR; auto-merge on an open PR is undone with `gh pr merge <PR> --disable-auto`.
