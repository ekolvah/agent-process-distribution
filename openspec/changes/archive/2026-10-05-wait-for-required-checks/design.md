# Design

## D1. The expected checks are the base branch's required status checks

Before the loop `wait_for_pr` reads the PR's base (`gh pr view <PR> --json baseRefName`) and
the rules on it (`gh api repos/{owner}/{repo}/rules/branches/<base>`), and collects the
`context` of every `required_status_checks` rule — the platform's own definition of what must
pass to merge, which GitHub shows as "Expected" while a check has not reported. A read counts
as concluded only when every required context is among the head's check names and none is
`pending`. The rules are read once: they do not change with the head.

Observed:
- `gh api repos/ekolvah/kinozal_scraper/rules/branches/main` → `agent-process / quality`,
  `agent-review / agent-review`; the same URL without any token → HTTP 200 with the same
  contexts, while `/branches/main/protection` (classic) → 401. The "needs admin" that left the
  required contexts out of `v2-2e-wait-for-pr-checks` and `v2-1a` is classic protection's.
- This repository's `rules/branches/main` → `agent-process / quality`,
  `agent-review / agent-review`, `pr-title`: a required check the plugin does not install.
- `gh pr checks 346 --json name` here and `gh pr checks 630 -R ekolvah/kinozal_scraper --json
  name` list the required contexts verbatim as check names.
- `rules/branches/<a branch without rules>` → `[]`, exit 0.

Alternatives rejected:
- The plugin's own contexts (`activate_protection.contexts()`), the first draft of this plan:
  misses `pr-title` here and any check a consumer requires, and is a second source for a fact
  the platform holds.
- `gh pr checks --required`: filters the reported checks by `isRequired`
  (`pkg/cmd/pr/checks/checks.go`, `aggregateChecks` over `statusCheckRollup.Nodes`); a required
  check that has not reported is not in the rollup, so it cannot name the absent one.
- A longer settle delay (poseidon/wait-for-status-checks `delay`): the two-read settling is
  already one, and issue 348's gap was two minutes; no delay bounds a gap.
- Auto-merge or a merge queue, where GitHub waits: the person merges (goal 3, user control), and the delivery
  loop needs the verdict and the threads, not a merge.

## D2. No required check is a visible note, not a fallback

An empty list (a repository before `activate_protection`, or one protected by classic
protection only, which the endpoint does not return) prints once
`note: <base> requires no status check; settling on the reported checks only` and waits as
before this change. It is not an error: the install PR runs before activation by design. What
stops being proved there is the presence of the plugin's checks; its catcher is
`activate_protection`, which refuses (exit 2) unless the current head of that PR carries a
successful `agent-process / quality` and `agent-review / agent-review` run. A `gh` failure of
either read is exit 2 with its stderr, never a verdict.

## D3. An absent required check is waiting; the gap left is recorded

A missing context resets the agreement like a pending check and prints
`waiting: <contexts> (not reported)`; never exit 1, because a workflow attaches minutes after a
fast foreign one. An empty rollup keeps its `no checks reported` line. The timeout names the
absent contexts (exit 3) — the end of a renamed or removed required job, or of a reopened PR
that `agent-review`'s `types: [opened, synchronize]` skips. The gap ADR 0027 records as not
proved (a run attaching more than 30 s after the others) is closed for required checks and
stays for the others: a check the base branch does not require that attaches more than 30 s
after the required ones concluded still settles unseen. It does not gate the merge; the ADR
line says so.

## Migration and rollback

None: one script, no state; two reads per invocation more. Rollback is reverting the PR.
