## Why

Install's person-only actions are spread over the run: the `gh` scope (step 1), the review
secret (step 3), the `plugin-channel` row (step 4), then, after the merge, the bot account and
its `gh auth login` (step 6). Each is a separate stop for the person, and a bot created only at
step 6 holds up steps 5–6 of a run that otherwise continues in one session.

## What Changes

- `skills/agent-process/SKILL.md` `## Install` opens with a **Prepare** checklist, done by the
  person in one sitting before the first `init`: the bot account and its
  `gh auth login -s project,workflow`, the person's own `gh auth login -s project,workflow`
  (active again via `gh auth switch --user <person>`), and the review secret
  (`claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`). The
  plugin is not in it: Install runs from the plugin's own `/agent-process:init`.
- Steps 1, 3 and 6 drop the instructions Prepare now carries and point back to it when
  `init` still prints the row; the step numbers stay.
- `README.md`'s `Requires:` line points to Prepare instead of listing a `project`-only scope.
- No behaviour changes: `init`'s `manual` rows and every script are untouched.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: the procedure text changes, no requirement does (`skip_specs: true`).

## Impact

- Edited: `skills/agent-process/SKILL.md` (`## Install` only), `README.md` (the `Requires:`
  line of `## Install`; the once-per-machine plugin commands stay).
- Added, removed: none. Docs only.
