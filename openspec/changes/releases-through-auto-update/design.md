## Context

The observations this design rests on are in the proposal (Why). `stable` already exists on
origin at `v2.6.0` (45876bf) from the #199 experiment; `v2.6.1` and `v2.7.0` were released since
without moving it. No ruleset of the repository targets `stable` (`agent-process default
branch` includes `refs/heads/main`, `pr-title` includes `~DEFAULT_BRANCH`).

## Decisions

**D1 — The channel is a `stable` branch with auto-update on.** `templates/settings.json`
renders `"ref": "stable"` in the source and `"autoUpdate": true` on the marketplace entry,
beside the unchanged `sparsePaths`. The hook's Install URL keeps `v<version>`: it names the
installed release's text. The `_settings_text` comparison needs no change: the owned entry is
compared whole, so an entry at a tag, or without `autoUpdate`, is replaced by the render.
Alternatives: keep the tag and have Install bump it — rejected: a project `ref` does not
re-point a known marketplace (#184), so it moves nothing; `main` as the channel — rejected: it
ships every merged PR before its release PR, and the release-drift check compares releases,
not commits; the release-channel pattern of the reference (host-marketplace, "Run release
channels") is a ref per channel.
Project `autoUpdate` is written although step 4 did not confirm it: the reference names any
settings file first, and nothing relies on it alone. `_manual` gains one row, `manual
plugin-channel: once per machine -- claude plugin marketplace add
"ekolvah/agent-process-distribution#stable", then /plugin → Marketplaces → Enable auto-update
for agent-process-marketplace` — the step 5 configuration (user declaration at `stable` with
`autoUpdate`), observed working, for a fresh machine and a migrating one alike. The installer
prints it and runs no `claude` command: plugin state is the person's machine, not the
repository (same pattern as the Project UI rows).

**D2 — The release workflow fast-forwards `stable`.** A step after release-please, `if:
steps.release.outputs.release_created == 'true'`, runs `gh api -X PATCH
repos/$GH_REPO/git/refs/heads/stable -f sha="$SHA" -F force=false` with
`RELEASE_PLEASE_TOKEN`, `SHA` from `steps.release.outputs.sha` ("SHA that a GitHub release was
tagged at", release-please-action README, root component outputs; the package path is `.`).
`force=false` makes the REST update a fast-forward or a refusal (docs.github.com, "Update a
reference": "Indicates whether to force the update or to make sure the update is a fast-forward
update"); a refusal fails the step and the run (Principle IV) instead of rewriting the channel.
The token already writes tags; no new secret. Problem it closes: #199. Standard: the reference's
release-channel pattern; no release-please option moves a branch.

**D3 — Dependabot ignores the process refs.** The marker block of `templates/dependabot.yml`
gains `ignore: [{dependency-name: "ekolvah/agent-process-distribution*"}]` (Dependabot options
reference: `dependency-name` "optionally using `*` to match zero or more characters"). The
wildcard covers both the `owner/repo` form and a workflow-path form of a reusable-workflow
dependency, since the name form was not observed. Decided in the #199 comment; no bespoke
quality check.

**D4 — The drift fix names a plugin update.** `release_drift`'s skill-older message becomes
`update the skill to <x>: \`claude plugin update agent-process@agent-process-marketplace --scope
<user|project>\` (the scope \`claude plugin list\` shows for this project); then restart the
session`. Observed to refresh the marketplace and update the install in one command (proposal,
05:24Z), so no separate `marketplace update` is named. SKILL.md Install says the same and
describes the channel and the migration.

**D5 — Migration ships as a BREAKING CHANGE note (person's decision: 3.0.0).** The PR body
carries `BEGIN_COMMIT_OVERRIDE` with `feat!: releases-through-auto-update` and a
`BREAKING CHANGE:` footer naming the steps below; release-please reads the merged PR's override
on the merge push (release-please README, "the next time Release Please runs, it will use that
override section"; squash merge is the only merge method here). The PR title stays
`feat: releases-through-auto-update` for the title check.
Migration, once per machine, outside any project: where `~/.claude/settings.json` declares
`agent-process-marketplace`, set its `ref` to `stable`; run
`claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`; turn on
**Enable auto-update** for it under `/plugin` → Marketplaces; then re-run Install in each
repository (release drift names that). The first two are the `plugin-channel` row of D1.

## Risks / Trade-offs

- A push to `stable` by anyone with write access ships to every consumer → the only writer is
  D2's fast-forward; the ruleset `stable channel` (id 24099105, added 2026-09-28) restricts
  updates, deletion and non-fast-forward pushes, bypassed only by the Repository admin role —
  the owner of `RELEASE_PLEASE_TOKEN` (the author of every release).
- Install records duplicated by drive-letter case (#199 comment): auto-update moved only the
  record of the session's own path (proposal, step 5), so the skill check of the next session
  in the other spelling reports `several installs apply: <old>, <new>` until a session there
  updates it, or `claude plugin update … --scope project` is run from that spelling (observed,
  proposal 05:24Z). The degradation is visible (the marker), not silent; removing the duplicate
  records is not a channel question and is left to a follow-up issue.
- The first release after merge (3.0.0) fast-forwards `stable` from `v2.6.0`; `main` is linear
  (squash only), so the update is a fast-forward.
- Dependabot's name for a reusable-workflow dependency was not observed → D3's wildcard; a
  half-update PR that still appears fails on `PR links no issue` as today.

## Migration / Rollback

Migration: D5. Rollback is a revert PR: the next release renders a tag ref again and stops
moving `stable`; a machine on `stable` keeps following it until it is re-pointed.
