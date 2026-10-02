## Why

Auto-memory is machine-local. Claude Code meant it for "Your preferences, corrections you give
Claude, project context Claude can't derive from the code" ([memory](https://code.claude.com/docs/en/memory)).
A fact that every session and every person needs belongs in the repository, where they see it. In ekolvah/kinozal_scraper an agent
broke that rule twice in one session while it was prose only (#313). A `PostToolUse` `Edit|Write` check
fixed it there: a write under `.claude/projects/<project>/memory/` asks the agent to confirm
that the fact is machine-specific. Claude Code stores auto-memory at that path and writes it
with its standard file tools ([memory](https://code.claude.com/docs/en/memory): "Each project
gets its own memory directory at `~/.claude/projects/<project>/memory/`"; "Claude reads them on
demand using its standard file tools"). The same page names a hook as the mechanism for an
instruction that "must run at a specific point, such as before every commit or after each file
edit".

The plugin does not deliver the check. It runs only from local copies: this repository's
`.agent-process/scripts/hooks.py on-edit`, wired in `.claude/settings.json`, and
`scripts/hooks.py` in kinozal_scraper. Other consumers get nothing. The local copy here also
points the agent at `.agent-process/docs/architecture/project-map.md`, which does not exist
in this repository or in any consumer.

## What Changes

- New package script `skills/agent-process/scripts/memory_checkpoint.py` (`agent-process
  memory_checkpoint post-edit`): for an `Edit`/`Write` payload under the auto-memory directory
  it exits 2 with a self-contained reminder on stderr. Claude Code shows that stderr to the agent and
  does not undo the write. Any other payload is silent. The reminder asks whether every session
  and every person needs the fact. It does not ask the local copies' stricter question,
  whether the fact is machine- or operator-specific, because the platform allows project context
  in auto-memory.
- `hooks/hooks.json` gains a `PostToolUse` `Edit|Write` hook running it, behind the same
  adoption gate as the navigation hooks.
- This repository's `.agent-process/scripts/hooks.py` drops its memory branch. The plugin
  delivers it now. The ruff check and the `requirements*.in` reminder stay local until the edit-time lint decision (#321).
- SKILL.md Install names the memory checkpoint beside the navigation hooks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the plugin ships the memory checkpoint hook; this repository's post-edit hook
  carries no memory check.

## Impact

- Added: `skills/agent-process/scripts/memory_checkpoint.py`,
  `tests/publisher/test_memory_checkpoint.py`.
- Edited: `hooks/hooks.json`, `.agent-process/scripts/hooks.py`, `skills/agent-process/SKILL.md`
  (Install), `tests/publisher/test_hooks.py` (memory tests move out),
  `tests/publisher/test_plugin.py`, `tests/publisher/test_start_change.py` (`MOVED_SCRIPTS`).
- Removed: none.
- Consumers: after the release, sessions in adopted repositories get the checkpoint.
  kinozal_scraper gets it twice until it deletes its copy (ekolvah/kinozal_scraper#614, #612).
- No ADR: the decision follows the distribution mechanism of the archived change
  `2026-10-02-ship-navigation-hooks` and is recorded in `design.md`.
