## Context

Install (`skills/agent-process/SKILL.md#install`) has six numbered steps. Tests pin text by
step: `test_install_names_the_skill_marker` and `test_install_continues_past_the_installation_pr`
split the section on ` 4. ` / ` 5. `, and the requirement *Install continues past the
installation PR* names "steps 5 and 6". `init`'s `manual` rows (`manual.py`) keep naming each
person action, since they report state, not order.

## Standard approach

none found: no external standard was searched for the order of person-only actions in an
agent-run install; the `gh` behaviour the decisions rest on is observed below. The form is a
prerequisites list before the first command.

## Decisions

- **D1 Prepare is an unnumbered list before step 1.** Steps keep their numbers, so the spec's
  "steps 5 and 6" and the step-split tests hold. Alternative: a new step 0 or renumbering —
  rejected, it rewrites references for no gain.
- **D2 The bot logs in first, the person last.** Observed `gh auth login --help` (gh 2.87.3):
  login is per account on a host; `gh auth switch --help`: "Switch the active account for a
  GitHub host". `agent_identity` reads the bot's token with `gh auth token --user <login>`
  (`agent_identity.py:109`), so the bot need only be logged in, not active. Prepare: create the
  bot, `gh auth login -s project,workflow` as the bot, then as the person (or
  `gh auth switch --user <person>` when already logged in), so `init` runs as the person.
  The person's login gains `workflow` (today step 1 and README ask `project` only): the
  installation push (`onboarding.py` `_push_step`) sends `.github/workflows/*` with the
  person's credentials, and
  <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps>
  says of `workflow`: "Grants the ability to add and update GitHub Actions workflow files";
  `gh auth login --help` (gh 2.87.3) gives only `repo`, `read:org` and `gist` as the minimum.
- **D3 Prepare sets the review secret, not only keeps a token at hand.** `gh secret set --help`
  (gh 2.87.3) shows "Paste secret value for the current repository in an interactive prompt",
  and the secret does not depend on `init`. Setting it in Prepare removes step 3's stop; step 3
  remains only for a dry-run that still prints the `review-secret` row. Alternative: the issue's
  "token at hand" — leaves a stop and a token waiting in the person's clipboard.
- **D4 The plugin stays out of Prepare.** Install runs from the plugin's own
  `/agent-process:init`, so its reader has the plugin; its commands already stand in README, in
  Install's closing paragraph and in the `plugin-channel` row step 4 handles. A third copy
  would add length only. Alternative: list it in Prepare as the issue suggests — rejected for
  that reason.
- **D5 README points to Prepare.** README's `Requires:` line names `gh` with `project` only and
  no review secret; it points to Install's Prepare instead, keeping its plugin commands, which
  come before Install.
- **D6 No script changes.** The `manual agent-identity` row says "once the installation PR has
  merged -- create a bot account …"; it is printed only when the clone lacks the identity, and
  creating the bot earlier does not make it wrong. Changing it is behaviour, outside this
  docs-only issue.

## Risks / Trade-offs

- [The person runs Prepare's `gh auth login` lines in the wrong order and `init` runs as the
  bot] → Prepare ends on `gh auth switch --user <person>`; `gh auth status` shows the active
  account.

## Migration Plan

Docs only; revert the PR to roll back.
