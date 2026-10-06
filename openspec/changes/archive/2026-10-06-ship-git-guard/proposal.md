## Why

The skill says "The person merges", but nothing the plugin installs stops the agent from
merging or from running an irreversible git command. The ruleset covers only the server
side: a push to the default branch and a merge without the required checks. It does not stop
`gh pr merge` on a green PR, a local `git reset --hard` or `git branch -D`, or `--no-verify`
skipping the pre-push hook that `init` installs.

Two repositories hold the line locally with the same static `permissions.deny` block: this
repository's `.claude/settings.json` and ekolvah/kinozal_scraper's (#312). Other consumers get
nothing. A plugin cannot ship that block: "`settings` | Object | Settings Claude Code applies
while the plugin is enabled. Only `agent` and `subagentStatusLine` take effect"
([plugins-reference](https://code.claude.com/docs/en/plugins-reference), Fields). A
`PreToolUse` hook can ship. It also names what to do instead, and a deny rule cannot.

The hook is a guardrail against agent error, not a security boundary. Claude Code documents
that a Bash rule "covers the invocation Claude usually produces and isn't a security boundary
around the program", and its example: `Bash(git push *)` does not stop
`git -C . push origin main`, `git -c push.default=current push origin main`, or
`git 'push' origin main` ([permissions](https://code.claude.com/docs/en/permissions#bash-rule-limits)).
The server-side boundary for merging is the agent's own GitHub identity, which this change
does not touch (#357).

A static deny entry for a guarded command shadows the hook: "Claude Code evaluates deny and
ask rules regardless of what a PreToolUse hook returns: a matching deny rule blocks the call"
([permissions](https://code.claude.com/docs/en/permissions#extend-permissions-with-hooks)).
This repository's deny block therefore has to go, as its navigation entries did.

## What Changes

- New package script `skills/agent-process/scripts/git_guard.py` (`agent-process git_guard
  pre-bash`). It denies, and names the alternative for, these commands in any stage of a Bash
  command: `gh pr merge`, `gh repo delete`, `git push` with a force flag, a `+` refspec,
  `--no-verify`, or a destination of `main`, `git commit --no-verify`/`-n`, `git reset --hard`,
  and `git branch -D` (or delete plus force). Git's global options (`-C`, `-c`, …) before the
  subcommand do not hide it.
- `navigation_policy.py` exposes its shell-stage splitter (separators, wrappers, `sh -c`) for
  the guard to reuse. Its behaviour is unchanged.
- `hooks/hooks.json` gains the guard as a second hook of the `PreToolUse` `Bash` group, behind
  the same adoption gate.
- This repository's `.claude/settings.json` drops the deny entries the guard covers. It keeps
  `Bash(sleep:*)`, which is token economy, not safety, and is out of scope here.
- SKILL.md Install names the guard beside the navigation hooks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the plugin ships the git guard, and this repository's settings carry no deny
  entry that shadows it.
- `review-and-merge`: "Local safety in Claude Code" names the git guard instead of the
  deny-list as the local stop for a push to `main`, a force push and `gh pr merge`.

## Impact

- Added: `skills/agent-process/scripts/git_guard.py`, `tests/publisher/test_git_guard.py`.
- Edited: `skills/agent-process/scripts/navigation_policy.py` (shared splitter),
  `hooks/hooks.json`, `.claude/settings.json`, `skills/agent-process/SKILL.md` (Install),
  `tests/publisher/test_plugin.py`, `tests/publisher/test_start_change.py` (`MOVED_SCRIPTS`).
- Removed: `tests/agent_process/test_delivery_gate_wiring.py::test_claude_denies_push_to_main_force_push_and_merge`,
  which asserted the deny entries; its scenario maps to `tests/publisher/test_git_guard.py`.
- Consumers: after the release, sessions in adopted repositories get the guard.
  kinozal_scraper deletes its deny block afterwards, or its entries keep shadowing the
  guard's messages (tracked in the consumer's roadmap epic).
- No ADR: the decision follows the distribution mechanism of the archived change
  `2026-10-02-ship-navigation-hooks` and is recorded in `design.md`.
