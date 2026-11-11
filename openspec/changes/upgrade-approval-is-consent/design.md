## Context

See proposal.md — Why. The Install procedure (SKILL.md `## Install`) is prose the agent follows.
`init --dry-run` is reads only; `init --confirm` reports `conflict` and exits non-zero before any
write. Besides the PR's files and its `onboarding-*` steps, a confirmed run writes outside the PR
(`init.py` docstring, steps 1, 14, 15, 20, 21, 22): `onboarding-root` (only in a repository with
no commits), `project-copy`, `project-link`, the clone's `pre-push` hook, the Project's `Area`
options of `project-areas` (planned on an upgrade of a repository installed before
`init-replaces-project-areas`), and the `GRAFANA_URL`
variable, the token secret and the dashboard import of `task-readings-url`, `-token`,
`-dashboard`.

## Standard approach

Dependency-update bots open the upgrade as a PR and take the PR's review or merge as the
consent, with no separate preview step: Dependabot version updates
(https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/about-dependabot-version-updates)
and Renovate automerge, where branch protection's required review gates the merge
(https://docs.renovatebot.com/key-concepts/automerge/). This change follows that pattern for the
writes the PR carries, and keeps the question for any write it does not.

## Decisions

- **D1 — the dry-run decides, not the session markers.** The question is skipped when the
  dry-run, which runs as now and is shown, plans none of the out-of-PR transitions above and
  prints no `manual agent-identity` row. Both signals come from the release being installed
  (`manual.py:222-232` reads `env.GH_TOKEN` of `.claude/settings.local.json`), not from the
  consumer's older `.claude/agent-process-check.py`, whose copies before v3.15.0 print no
  identity marker. A first install plans `project-copy`/`project-link` or prints the identity
  row, so it always asks. `onboarding-root` needs no mention: it is planned only in a repository
  with no commits, which also has no identity. Alternative: key the path on the session-start
  markers (`agent-process release drift`, no `agent identity not set`) — rejected: a missing
  identity marker is also what a pre-3.15.0 check or a crashed check prints, so the path would
  fail open (architect review round 1). Alternative: an `init` summary line classifying its own
  plan — rejected until a misread of the named transitions is observed (§VII); a misread toward
  asking costs one question.
- **D2 — the exception sits where the question is.** Step 3 carries the skip; step 4 carries the
  PR side (`gh pr merge <PR> --auto --squash` once the PR opens, approval asked instead of merge),
  as in Delivery (ADR 0040 D7).
- **D3 — after the merge, step 5 only on its row.** On the unasked path the identity is set, so
  `agent_identity` has run and steps 5–6 would ask setup questions already answered; step 5 runs
  only when the confirmed run printed `manual protection`, and step 6's row cannot print because
  the skip required its absence.
- **D4 — test slices.** Existing tests cut steps at ` 4. ` and ` 5. `; the new prose in steps 3
  and 4 ends no sentence in a step number.

## Risks / Trade-offs

- [The settings carry the bot's token but this session started before it was written, so
  `init` runs as the person and opens a PR the person cannot approve] → fails closed: the
  approval ruleset holds the PR; the session start prints `agent-process agent identity not set`
  and a restart fixes it.
- [The approval ruleset is gone while the token is set, so `--auto` merges unapproved] → same
  reliance as every Delivery PR (ADR 0040 D7); `agent_identity` writes the token and the ruleset
  in one run, which exits 1 while the ruleset is still planned.
- [`init`'s reads of secrets and variables under the bot's write role] → unchanged by this
  change: the dry-run already runs with the session's token, and an unreadable state keeps its
  row with `(cannot read: <reason>)` without changing the exit code (`init.py` docstring). The
  unasked path writes no secret or variable, since `task-readings-*` must not be planned.

## Migration Plan

Prose only; the release that carries it applies on the next upgrade. Rollback: revert the
SKILL.md sentences.
