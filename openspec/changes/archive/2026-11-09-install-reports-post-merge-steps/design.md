## Context

See proposal.md — Why. Steps 5 and 6 cannot be done by `init`: `activate_protection` needs the
process checks observed green on the merged installation PR, the bot account is created by
the person, and `agent_identity` adds the `agent-process person approves` ruleset, which must
follow that merge (the person cannot approve their own PR). So the fix is reporting, not
performing.

## Standard approach

- The repository's own mechanism for work only a person or UI can do is the `manual` row
  (requirement `Manual rows follow observed state`); the new rows use it unchanged.
- GitHub REST "Get a repository" returns `allow_auto_merge`
  (https://docs.github.com/en/rest/repos/repos#get-a-repository). Observed without admin:
  `gh api repos/ekolvah/lampa-mediacenter -q '{allow_auto_merge, perm: .permissions.admin}'`
  printed `{"allow_auto_merge":true,"perm":false}`. `gh repo view --json` has no such field.
- GitHub REST "Get rules for a branch" returns the active rules of a branch
  (https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch), readable without
  admin rights; `wait_for_pr._required` already reads it. Observed on
  `repos/ekolvah/lampa-mediacenter/rules/branches/main` without admin: the rule types include
  `required_status_checks`.
- `gh repo edit --help` lists `--enable-auto-merge  Enable auto-merge functionality`.

## Goals / Non-Goals

**Non-Goals:**
- Suggesting the bot login from `gh auth status` (the issue's optional item): `agent_identity`
  already refuses with exit 2 naming a login `gh` holds no token for, and growing the script
  runs against reducing it to standard `gh` commands. Add it if a run shows the login is a
  real stumbling point.
- Checking `allow_auto_merge` at session start: the hook makes no network call today.

## Decisions

- **D1 — three rows, one state each.** Closes the observed gap: install ended silently with
  steps 5 and 6 pending. As every other row, each row is one state and one fix, so a person
  with only auto-merge off is not told to redo the bot setup:
  - `protection`: done when the `required_status_checks` rules of
    `manual._gh_read(t, "api", f"repos/{t.repo}/rules/branches/{default}")` name both
    `activate_protection.CONTEXT` and `activate_protection.REVIEW_CONTEXT`; `default` is the
    `default_branch` of the repository read below, so the row costs one call. The contexts are
    imported, not copied, so the row cannot drift from the script it names. The parsing
    mirrors `wait_for_pr._required`, which takes a PR and prints a note, so it is not called.
    Unlike there, a result that is not a list of rule objects — `gh api` prints GitHub's error
    object on a 4xx and exits 1, and `_gh_read` returns any JSON — raises `Unreadable`, as do
    settings that are not an object, or whose `env` is present and not an object (a missing
    `env` is `{}`, as in `agent_identity._settings`), so no read can crash a run after its
    writes.
  - `agent-identity`: done when this clone's `.claude/settings.local.json` holds
    `env.GH_TOKEN`, read with `manual._plugin_file` (the existing guarded JSON reader). The
    text says the steps follow the merge of the installation PR.
  - `auto-merge`: done when `allow_auto_merge` is true, read with one new
    `manual._gh_read(t, "api", f"repos/{t.repo}")` call; `init` makes no such call on a
    non-empty repository, and the `protection` row takes its `default_branch` from the same
    read. A failed read or an absent field keeps the row with `(cannot read: <reason>)` — both
    rows when the repository read fails.
  Alternatives: an `auto-merge` transition of `agent_identity` — the person removed exactly
  that transition as bespoke (`openspec/changes/archive/2026-10-12-approval-merges/design.md`,
  Revision after delivery); `allow_auto_merge` in `manual.QUERY` — saves the call but turns
  the row unreadable whenever the Project read fails.
- **D2 — one fix text.** `IDENTITY_FIX` becomes the dry-run, then `--confirm`, then
  `gh repo edit --enable-auto-merge`, then the restart; the advice sentence drops what the fix
  now names. `manual.py` holds the same constant for the `agent-identity` row, and a
  publisher test asserts the two are equal, as it already does for `PRE_COMMIT_ID`: the
  template is copied into the consumer and cannot import `manual`. The drift that caused the
  bug — the marker behind SKILL.md — then fails a test for the two scripted copies.

## Risks / Trade-offs

- [A clone of an already-configured repository without its own settings token shows the
  `agent-identity` row] → correct: identity is per clone.
- [The `protection` row checks the required contexts, not every field of the ruleset; a
  ruleset that drifted in another field stays unreported] → `activate_protection --dry-run`
  prints such a difference; reading the ruleset itself needs admin rights.
- [With both states pending, both rows name `gh repo edit --enable-auto-merge`] → the command
  is idempotent.

Rollback: revert the PR; no state is written.
