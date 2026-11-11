## Why

`agent_identity` (~275 lines, ~340 of tests) converges a setup the person runs once per
repository and clone, and four of its five transitions are standard commands (design,
**Standard approach**). Only two failures were observed: a bot that is a repository admin, and a
`GH_TOKEN` in `.claude/settings.local.json` that is not the bot's.

Observed on 2026-11-11:
- `gh auth setup-git` with a sandboxed global config wrote
  `[credential "https://github.com"] helper = ` then `helper = !'…gh.exe' auth git-credential`,
  the reset-and-route the script writes per clone, in the global config.
- With the `GH_TOKEN` of this clone's settings,
  `gh api graphql -F owner='{owner}' -F name='{repo}' -f query='…{viewer{login} repository(owner:$owner,name:$name){viewerPermission}}'`
  printed `{"data":{"viewer":{"login":"ekolvah-agent"},"repository":{"viewerPermission":"WRITE"}}}`:
  the permission is one read with that token.
- `git check-ignore -v .claude/settings.local.json` printed
  `~/.config/git/ignore:3:**/.claude/settings.local.json`: Claude Code ignores the file
  machine-wide.

## What Changes

- **BREAKING** `agent-process agent_identity` is removed.
- `init`'s `manual agent-identity` row, which today checks only that `env.GH_TOKEN` is set,
  stays outstanding unless that token's permission on the repository is write or maintain
  (the person's token is admin).
- Install step 6 becomes a runbook. Per machine: `gh auth login -s project,workflow` as the
  bot, `gh auth switch --user <person>`, `gh auth setup-git`. Per repository:
  `gh api -X PUT repos/{owner}/{repo}/collaborators/<bot> -f permission=push`, the bot accepts
  the invitation, the bot as Writer in the Project's access settings,
  `gh api -X POST repos/{owner}/{repo}/rulesets --input <skill dir>/templates/approval_ruleset.json`,
  `gh repo edit --enable-auto-merge`. Per clone: the person sets `env.GH_TOKEN` of
  `.claude/settings.local.json` to `gh auth token --user <bot>`, then the Install dry-run shows
  no `manual agent-identity` row, and Claude Code restarts.
- The session-start marker and the `manual agent-identity` row name Install step 6 as the fix
  instead of inline commands.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: "Agent identity converges" is removed; "Install reports a pending agent
  identity" gains the permission check; the session-start marker's fix, "Install's admin steps run as
  the person" and the scenarios of "Install continues past the installation PR" drop
  `agent_identity`.
- `review-and-merge`: "The person approves" holds the ruleset's content and no longer names
  `agent_identity`.

## Impact

- Removed: `skills/agent-process/scripts/agent_identity.py`, `tests/publisher/test_agent_identity.py`.
- Edited: `skills/agent-process/scripts/manual.py`, `skills/agent-process/templates/skill_check.py`,
  `skills/agent-process/SKILL.md` (Install step 6), `.claude/settings.json` (the
  `agent_identity --confirm` ask rule), `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md`
  (D1, D3, D6, Confirmation).
- Tests edited: `tests/publisher/test_init_remote.py`, `tests/publisher/test_skill_check.py`,
  `tests/publisher/test_activate_protection.py` (receives `test_approval_ruleset_body` and the
  `activate_protection` half of `test_a_clone_with_the_agent_identity`),
  `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py` (script lists),
  `tests/publisher/init_harness.py` if its fake `gh` needs the GraphQL read.
- Specs: `openspec/specs/distribution/spec.md`, `openspec/specs/review-and-merge/spec.md`.
  No dependency changes.
