## Context

See proposal.md — Why, for the reproduction and the platform observations. Today every printed
command is `python skills/agent-process/scripts/<script>.py`; it resolves only in the publisher
checkout, and `release_drift` exempts exactly that directory (`init.release_drift`: a script dir
equal to `<root>/skills/agent-process/scripts` skips the comparison). The publisher test
`test_printed_commands_run_as_printed` checks the printed path against the publisher tree.

## Goals / Non-Goals

**Goals:** a command copied from SKILL.md into `tasks.md` runs unchanged, from the consumer root,
across releases; the publisher keeps running its working-tree scripts.

**Non-Goals:** the scripts' `Usage:` docstrings and the absolute resume lines printed at runtime
(read, not copied); a PowerShell or cmd entry point; choosing `python3` over `python`.

## Decisions

**D1 — One plugin executable, `bin/agent-process <script> [args]`.** Problem: #253. Standard: the
plugin `bin/` directory, "on the Bash tool's `PATH` while the plugin is enabled" (plugins
reference). The auto-updated install moves the directory, `PATH` follows it, so the command text
carries no release. Alternatives: `${CLAUDE_PLUGIN_ROOT}` in the skill body — substituted with the
installed version's absolute path, the pinned path the issue rules out; a launcher the installer
copies into the consumer, locating the install through `claude plugin list --json` — a bespoke
resolver and a CLI call per command for what the platform does; one executable per script — nine
generic names (`check_red`, `init`) on every Bash `PATH` of the machine.

**D2 — The current directory's scripts win.** The launcher runs
`./skills/agent-process/scripts/<script>.py` when that file exists, else
`<bin>/../skills/agent-process/scripts/<script>.py`. In the publisher (and its change worktrees,
which hold the tree) this is the file the old printed command ran, and the one `release_drift`
exempts; running the plugin's copy there would exit 2 on `release drift: project records none`.
Guard analysis: no guard is dropped — the drift check still runs in the script, and a consumer
that vendors that directory runs it exactly as the old printed command did.

**D3 — POSIX `sh`, `python`, closed names.** The Bash tool runs `sh` on every carrier (Git Bash on
Windows, observed with LF and CRLF endings, so no `.gitattributes` rule). The interpreter is
`python`, as in every printed command today. The script name must match `[A-Za-z0-9_]+` and name
an existing file of the chosen directory; otherwise exit 2 with `usage:` and the names of the
plugin's scripts — no path traversal, and a typo is visible, not a Python traceback. The launcher
`exec`s, so the exit code is the script's. Git mode `100755` so Linux and macOS clones can
execute it.

**D4 — SKILL.md prints `agent-process <script>`.** The header says the commands run through the
Bash tool from the repository root; the Install sentence mapping `skills/agent-process/` to the
skill's directory goes. `test_printed_commands_run_as_printed` inverts: every printed command
starts with `agent-process <script>` whose file exists in the skill's `scripts/`.

**D5 — `archive_change` ticks either form.** `_mark_own_task` matches
`archive_change(\.py)? <change>`, so a `tasks.md` written before this release still ticks.

**D6 — The marketplace clone is whole; the component roots are closed.** Problem: a sparse set
freezes on each machine (#184), so `bin/` — which the manifest cannot move (proposal) — would miss
every sparse clone, and the next component root would repeat it. The template and
`.claude/settings.json` drop `sparsePaths`. The guard sparse gave — nothing of the development
tree acts in a consumer — is kept where it is decided: the plugin loader reads only component
roots, so `test_plugin.py` checks every default location of the plugin reference ("Standard
layout": `skills/`, root `SKILL.md`, `commands/`, `agents/`, `hooks/`, `.mcp.json`, `.lsp.json`,
`output-styles/`, `workflows/`, `themes/`, `monitors/`, `bin/`, root `settings.json`, plus
`.claude-plugin`) and requires exactly `.claude-plugin`, `agents`, `bin`, `commands`,
`skills/agent-process`. Alternatives: add `bin` to `sparsePaths` — the frozen set stays, and the
two carriers keep giving different trees (the `plugin-channel` row adds whole); move the plugin to
a subdirectory `source` — every path in settings, tests and the hand-off moves, for 2.6 MB.
What stops proving: that the cache holds no development tree; nothing reads it there (#216 records
ballast, no harm). Catcher of a stray component root: `test_plugin_component_roots_are_closed` in
`agent-process / quality` on the PR head.

## Risks / Trade-offs

- [A machine whose marketplace was added sparse since 2.7.0 keeps its sparse set (#184)] →
  `agent-process: command not found` at the first task, visible to the agent and the person; this
  machine's clone is whole (proposal). Recovery is unverified: `marketplace add …#stable` is
  observed to re-point a known marketplace (releases-through-auto-update, #199 comment), but that
  it drops the frozen `sparsePaths` and re-clones whole is inferred, not observed — the person
  removes and adds the marketplace, and the first sparse machine observed settles it. A
  session-start check of `bin/` is deferred until then.
- [A new plugin component type appears in a later Claude Code] → the closed list does not know its
  location; the list is the reference's table as of 2026-09-28.
- [The Bash tool is absent, or a carrier runs PowerShell] → `agent-process` is not found; the
  header names the Bash tool.
- [`python` missing where only `python3` exists] → unchanged from today's printed commands.

## Migration Plan

The release ships `bin/`; plugin auto-update brings it to whole-clone machines, and a consumer's
re-run Install renders its marketplace source without `sparsePaths` (a sparse clone already on a
machine stays; see Risks). In-flight
`tasks.md` files keep the old command text: they resolve in the publisher and tick (D5). Rollback
is a revert: SKILL.md prints the old paths again; a consumer `tasks.md` written with
`agent-process` lines then fails visibly at `command not found`, and the next render adds
`sparsePaths` back (effective on a fresh add only).
