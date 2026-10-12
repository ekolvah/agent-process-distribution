## Why

Once `agent_identity` has run, every Claude Code session in the clone carries the bot's
`GH_TOKEN`, which `gh` prefers to the stored accounts, so Install's admin steps
(`activate_protection`, `agent_identity`) read the rulesets as a non-admin and plan a write
that is not needed; `--confirm` then fails with HTTP 404.

Reproduction, this repository, 2026-10-12, from a session of the configured clone:

```
env login: ekolvah-agent
stored login: ekolvah            # env -u GH_TOKEN gh api user
ruleset 23732345 bot-view: agent-process default branch null person-view: []
ruleset 24939338 bot-view: agent-process person approves null person-view: []
```

Root cause: both scripts default their `gh` to `run_gh`, which passes the session's
environment on, so the person-side calls run as the bot. `gh help environment`: "`GH_TOKEN`,
`GITHUB_TOKEN` (in order of precedence) … takes precedence over previously stored
credentials." GitHub returns `bypass_actors: null` to a non-admin, the template owns `[]`, so
the plan reads `bypass_actors: null -> []`.

## What Changes

- A person-side `gh` runner that drops `GH_TOKEN` and `GITHUB_TOKEN` from the environment, so
  `gh` uses the stored active account. It is the default `gh` of `activate_protection` and
  `agent_identity`; nothing else changes its runner.
- `agent_identity`'s bot-side calls keep the bot's token in `GH_TOKEN`.
- This repository's `.claude/settings.json` gains `permissions.ask` rules for the `--confirm`
  runs of both scripts: here the launcher runs the checkout's own scripts and templates, which
  the agent edits, so an admin write asks the person even in auto mode.
- ADR 0040 records that the admin steps use, on purpose, the limit it accepts (the agent can
  drop `GH_TOKEN`), still behind `--dry-run` and the person's yes to `--confirm`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: a new requirement — Install's admin steps call `gh` as the person's stored
  account, and the bot-side calls of `agent_identity` as the bot.

## Impact

- Edited: `skills/agent-process/scripts/set_status.py` (the person runner beside `run_gh`),
  `skills/agent-process/scripts/activate_protection.py` and
  `skills/agent-process/scripts/agent_identity.py` (default `gh` and docstring),
  `tests/publisher/test_agent_identity.py` (one test covers both scripts),
  `.claude/settings.json` (the ask rules),
  `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md`.
- Added: `openspec/changes/install-admin-as-person/` (archived into `openspec/specs/distribution/spec.md`).
- Removed: nothing.
- `SKILL.md` Install is unchanged: step 6 already leaves the person as `gh`'s active account,
  and the scripts now pick it themselves.
