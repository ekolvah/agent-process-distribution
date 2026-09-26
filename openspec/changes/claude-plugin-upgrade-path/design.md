## Context

The observed Claude mechanism is in proposal.md, Why. `release_drift` in
`skills/agent-process/scripts/init.py` builds both drift messages. `start_change.py` and
`create_tracking_issue.py` print them. `## Install` of `skills/agent-process/SKILL.md` is the
page that the skill check's `SessionStart` marker links, through the Install URL of the
installed release.

## Goals / Non-Goals

**Goals:** every text that tells a person how to move a machine to a release names the path
that was observed to work.

**Non-Goals:**
- The installer does not write `~/.claude/settings.json`.
- The session-start check does not compare releases.
- Plugin versions on `main` are not bumped. The plugin cache is keyed by the version string:
  every `2.0.0` install here carries `9d1b5cd`, a `main` commit after tag `v2.0.0`
  (#184 comment 5844804395). This is a release-procedure defect that gets an issue of its own.

## Decisions

### The message carries the commands, not a link

The skill-behind message names the commands itself: `marketplace add "…#v<recorded>"`, the
declaration file, `plugin update … --scope <user|project>` and the two restarts.
Alternative: link `## Install`. Rejected: the linked page belongs to the release the
person is leaving, so on an older skill it is the page with the wrong fix.

### `add` or an edit of the declaration, named together

`add` works only while no settings declare the name (#184 comment 5844817104, step E).
The machine keeps the declaration after its first `add`, so every later move is an edit.
The message names both, so neither case needs a lookup. `marketplace remove` followed by `add`
is not named: it was not observed, and a remove may drop the installs of every repository.

### Install rewrite scope

`## Install` names the fixes for the `agent-process skill not loaded` marker. Only the
`/plugin marketplace update` remedy is replaced, by the release path, which answers the
reasons "plugin … has no skill" and a plugin behind the project. The remedy `enabling the
plugin for the project` is kept for "not enabled for this project". Nothing was observed about
the reason "several installs apply", so the change leaves it alone.

### Installer writes stay project-local

Alternative: `init.py` writes the user-scope declaration. Rejected: the `distribution`
requirement "The installed footprint is closed" bounds what a confirmed run changes. A
machine-wide ref also moves every other repository on the machine, and that decision belongs
to the person.

## Risks / Trade-offs

- [The Claude CLI changes this behaviour] → the message names CLI commands observed on 2.1.283.
  A new observed failure reopens the issue (#184). No test can reach the live CLI.
- [Two repositories on one machine need different releases] → not possible: the user-scope
  declaration pins the machine. `## Install` states this.
- [Old skills keep printing the old fix] → accepted. See proposal.md, Impact.

## Migration Plan

Text-only: messages and docs. Rollback is a revert of the PR.
