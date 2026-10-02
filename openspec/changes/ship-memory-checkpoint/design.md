## Context

See proposal.md, Why. The archived change `2026-10-02-ship-navigation-hooks` set up the
mechanism this change reuses:
- `hooks/hooks.json` holds the plugin's hooks;
- each hook calls a package script through `bin/agent-process`;
- each command first checks for `$CLAUDE_PROJECT_DIR/.github/workflows/agent-process.yml`;
- the requirement "Plugin hooks act only in adopted repositories" covers every hook command of
  the plugin.

The memory branch of `.agent-process/scripts/hooks.py` consists of a path predicate
(`_MEMORY_DIR_RE`), a signal, and the exit-2 contract. This change ships that branch and
nothing else.

## Goals / Non-Goals

**Goals:**
- Ship the memory checkpoint to every adopted consumer, with the same gate as the navigation
  hooks.

**Non-Goals:**
- Edit-time lint and the `requirements*.in` reminder (#321; the reminder is not shipped).
- Telling a personal note from a fact that others need. That judgement is semantic, so
  the hook asks the agent instead of deciding.

## Decisions

### D1. A package script of its own

`skills/agent-process/scripts/memory_checkpoint.py` holds the predicate, the message and a
`main` taking `post-edit`. It is the memory branch of `hooks.py`, moved.

Alternatives:
- Add it to `navigation_policy.py`. Rejected: that script answers PreToolUse cost questions,
  and this is a PostToolUse question about content.
- Ship `hooks.py` whole. Rejected: it carries the ruff check and the pip-tools reminder, which
  this change does not ship.

The name avoids `hook`, which `test_package_contents_are_closed` forbids in package paths.

**Problem and standard (SKILL.md Design).** The problem: the rule was broken twice in one
session while it was prose only (#313). The standard for the job is a Claude Code hook. The
memory documentation names a hook for an instruction that "must run at a specific point, such
as before every commit or after each file edit", and no standard checker can tell what a note
is about. The check stays a reminder, not a block.

Rejected standard: `autoMemoryEnabled: false` in the project's settings. The memory page:
"To turn it off for a single project, set `autoMemoryEnabled` in that project's settings",
with the example `{ "autoMemoryEnabled": false }`. It stops misplaced project facts with one setting and no script. It
also drops what auto-memory is for: the person's preferences and corrections, which the agent
would then lose between sessions.

### D2. One `PostToolUse` entry in `hooks/hooks.json`

The entry uses matcher `Edit|Write`, timeout 10, and the command
`cd "$CLAUDE_PROJECT_DIR" && { [ ! -f .github/workflows/agent-process.yml ] || sh "${CLAUDE_PLUGIN_ROOT}/bin/agent-process" memory_checkpoint post-edit; }`.
This is the command form and gate of the navigation hooks. The memory directory lies outside
the project, but the gate reads the session's project directory, and the payload carries the
absolute `file_path`.

The live probe on record (archived navigation design) covers a plugin `PreToolUse` hook only.
For `PostToolUse`, the plugin manifest reference covers the same file shape
([plugins-reference](https://code.claude.com/docs/en/plugins-reference), `hooks`): "`hooks`
takes a `.json` file path, an inline hooks object in the same shape as `hooks` in
`settings.json`"; "A hooks file wraps the event map in a top-level `"hooks"` key, the shape
`hooks/hooks.json` uses". Its example declares a plugin `PostToolUse` hook with matcher
`"Write|Edit"`. The group-1 tests run the command through `sh -c`. They prove the command, not
that the platform dispatches it.

### D3. Exit 2 with stderr

The hooks reference gives the `PostToolUse` row for exit 2 as "Shows stderr to Claude; the
tool already ran" ([hooks](https://code.claude.com/docs/en/hooks)). The local copy here and the
one in kinozal_scraper already use this contract.

Alternative: exit 0 with `additionalContext` JSON. Rejected: it would change a channel the
consumer already relies on, with no observed problem behind the change.

A payload that is empty, malformed, or has no `tool_input.file_path` exits 0 silently, as
`hooks.py` does today: a payload bug must not red every edit. An unknown subcommand prints
usage and exits 2, as `navigation_policy.py` does. Under `PostToolUse` exit 2 does not block
the call, and the agent sees the broken wiring (§IV).

### D4. A self-contained English message

The message names the file and asks one question: does every session and every person working
on the repository need this fact? If so, the agent moves it into the repository (its docs,
rules, or scripts). Otherwise the fact stays.

The question follows the platform's own split, not the local copies' rule. The local copies
ask to confirm that the fact is machine- or operator-specific. The memory page instead assigns
auto-memory "Your preferences, corrections you give Claude, project context Claude can't
derive from the code", including the `project` type: "ongoing work, deadlines, and decisions
that Claude can't derive from the code or git history". The old question would challenge every
such note. The new one targets the failure that prompted this change (#313): a fact that others need, kept where only
one machine sees it.

The message points to no file. The current one cites
`.agent-process/docs/architecture/project-map.md`, which exists neither here nor in any
consumer. It is written in English, the language of the package.

### D5. This repository drops its local memory branch

`hooks.py` loses `_MEMORY_DIR_RE`, `_is_memory_write`, `memory_write_signal`, the
`memory_write` kind and its dispatch. Otherwise this repository would print two reminders per
memory write.

The PostToolUse `on-edit` entry in `.claude/settings.json` stays for ruff and the
`requirements*.in` reminder until the edit-time lint decision (#321).

The predicate tests of `TestMemoryWriteGuard` move to `tests/publisher/test_memory_checkpoint.py`,
together with the fixture paths that use either separator.

Dropping the local guard makes the plugin hook this repository's only memory check. Its
failure modes, each with the catcher that is reached:
- **The plugin is not installed, disabled, or has no skill on this machine.** Caught: the
  `SessionStart` check `skills/agent-process/templates/skill_check.py`, wired in
  `.claude/settings.json`, prints `agent-process skill not loaded (<reason>)` at the start of
  every session here.
- **The machine runs a release older than this change.** The window lasts from merge until
  auto-update fetches the release, within a session per SKILL.md Install. Uncaught:
  `skill_check.py` checks the install, not its version against `main`. During the window a
  memory write here gets no reminder, and nothing reports that.
- **The platform does not dispatch the plugin's `PostToolUse` entry.** Uncaught by the suite
  (D2). The person or agent notices a missing reminder only at the first memory write after
  the release.

The two uncaught cases cost the same as the state before the local check existed. Their rollback
is a revert of this change, which restores the local branch.

### D6. Install names the checkpoint

SKILL.md Install already says that the plugin's navigation hooks act only in an adopted
repository. That sentence gains the memory checkpoint, so the person knows where the reminder
comes from.

## Risks / Trade-offs

- [The memory directory can be moved: `autoMemoryDirectory`, or a `CLAUDE_CONFIG_DIR` whose
  path has no `.claude` segment. The predicate then misses every memory write and the
  checkpoint is silent.] → Accepted, the same limit as the local copies have today. The memory
  page documents both settings. Revisit when a consumer that uses one is observed.
- [It fires on every memory write, including legitimate preferences and corrections.] → By design:
  the hook asks, it does not block. The cost is one stderr paragraph per memory write.
- [After merge, until auto-update, this repository has no memory check, and nothing reports
  that (D5).] → Accepted: the window is bounded by auto-update. Rollback: revert this change.
- [kinozal_scraper prints the reminder twice until it removes its copy.] → Tracked in the
  consumer's follow-up (ekolvah/kinozal_scraper#614, #612), as with the navigation hooks.

## Migration Plan

Release through release-please. Machines get it with the plugin's auto-update. No `init` step
is needed: plugin hooks need no project setting. Rollback is a revert PR and the next release.
