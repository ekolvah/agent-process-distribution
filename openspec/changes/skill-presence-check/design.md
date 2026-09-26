## Context

A consumer holds no process script (`distribution` / The installed footprint is closed): the
procedure and scripts come from the Claude plugin or the user-wide Codex skill link. When the
plugin does not load, only the agent can see it, and in #187 it improvised instead of saying so.
Observations are in the proposal and on #187.

## Decisions

### Carrier: a project `SessionStart` hook, Claude only

The project's `.claude/settings.json` is read whether or not the plugin loads, and a
`SessionStart` hook there was observed to run and reach the agent with the plugin disabled. The
check is code with an exit code, testable per case.

Rejected:
- Prose rules in the config block — an agent can ignore them, and no test proves it will not.
- A plugin hook — absent exactly when the plugin is absent.
- Delivery-script checks — they do not run when the skill is absent (#187's agent ran a clone).
- A Codex hook — each project hook needs an interactive approval, and the Codex skill is the
  user-wide link `init` itself creates. Accepted gap.

### Check file and hook entry

`templates/skill_check.py` is copied verbatim to `.claude/agent-process-check.py` by a new
`check` file step after `settings`; it is managed as the workflow file is: its first line is
`# agent-process:managed`, and an existing file without it is a conflict. It is not a `string.Template`: the Install URL comes as its one argument, so
the same file runs in the publisher checkout. Standard library only, one `subprocess.run` with
`encoding="utf-8"` and a 10 s timeout, `shutil.which("claude")`; a missing argument is itself a
`cannot check` reason.

Decision (pure function `verdict(listing, project) -> str | None`, `None` = loaded):
- keep entries with `id` = the plugin, `enabled` true, and `scope == "user"` or
  `projectPath` equal to `project` under `os.path.normcase` — the observed drive-letter case pair
  is one project;
- zero kept → `not enabled for this project`; more than one distinct `installPath` →
  `several installs apply: <versions>`; one without `skills/agent-process/SKILL.md` →
  `plugin <version> has no skill`.

`main` wraps everything: a missing CLI, non-zero exit, timeout, output that is not a list of
objects, or any exception becomes a reason (`cannot check: <what>`), never a traceback — a
crashing hook is silent (observed). It always exits 0: a hook cannot fix the machine, and the
marker, not a blocked session, is the carrier. Output, only when a reason exists:

```json
{"systemMessage": "agent-process skill not loaded (<reason>) — fix: <Install URL>",
 "hookSpecificOutput": {"hookEventName": "SessionStart",
  "additionalContext": "agent-process skill not loaded (<reason>). Do not fetch, clone or reconstruct it; tell the person and wait. Fix: <Install URL>"}}
```

`templates/settings.json` gains
`"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python \"$$CLAUDE_PROJECT_DIR/.claude/agent-process-check.py\" https://github.com/ekolvah/agent-process-distribution/blob/v${version}/skills/agent-process/SKILL.md#install"}]}]}`
(`$$` because the template goes through `string.Template.substitute`).

`_settings_text` owns the `SessionStart` group whose command names `agent-process-check.py`:
it is added once, replaced when different, and every other hook key and group is kept. The early
`unchanged` return requires the owned group too, so an already-installed consumer gets the hook on
its next `init --confirm` (the rewrite branch). A consumer whose file is not in the form init
writes gets the existing conflict, whose manual instruction now also names the hook group — the
same outcome a release change of `ref` already has there. `hooks` or `hooks.SessionStart` of
another type is a conflict with the manual instruction, as the two existing keys are.

### The publisher checks itself

This repository's `.claude/settings.json` gains a `SessionStart` group running
`python "$CLAUDE_PROJECT_DIR/skills/agent-process/templates/skill_check.py" <Install URL on main>`,
so the three-week outage named in the proposal is marked here too.
`test_publisher_dogfoods_process` asserts it.

### Install text

`## Install` gains: a Claude session start that prints `agent-process skill not loaded` names the
reason; the fixes are `/plugin marketplace update agent-process-marketplace` and a restart, or
enabling the plugin. It also drops "pinned per repository by `.claude/settings.json`": #184
observed that the project's `ref` does not re-point a marketplace the machine already knows.

## Risks

- `python` is not on PATH, or the `claude` CLI output changes shape: the first is a silent hook
  (the process already needs Python for every script); the second prints `cannot check`, so it
  shows rather than hides.
- Every session start costs ~0.5 s (observed).
- Codex sessions stay unchecked (accepted, above). Version drift is #190.

## Migration and rollback

Consumers get the check on their next `init --confirm`; nothing breaks before that. Rollback:
revert; the consumer keeps a harmless file and hook entry until removed by hand.
