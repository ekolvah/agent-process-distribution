## Context

Every skill script runs under the `python` the launcher finds on PATH (`bin/agent-process:30`).
The only third-party import of the shipped scripts is `jsonschema`, in
`start_change.verdict` (also used by `create_tracking_issue`); CI of a consumer never runs them.
They run only in a Claude session, through the Bash tool. The plugin is the whole repository (no
`sparsePaths`), so `.agent-process/requirements.txt` ships with it.

Claude Code documents the mechanism for plugin dependencies: `${CLAUDE_PLUGIN_DATA}` is a
per-plugin directory kept across updates, "for `node_modules`, virtual environments, and caches",
and a `SessionStart` hook installs into it when the manifest copy there differs ("Install
dependencies into the data directory", plugins/components). The variables are not exported to
the Bash tool; a `SessionStart` hook's `export` lines in `CLAUDE_ENV_FILE` are. Observed
2026-10-02 with Claude Code 2.1.283 on Windows: a `--plugin-dir` plugin's `SessionStart` hook
received `CLAUDE_ENV_FILE` and `CLAUDE_PLUGIN_DATA`, and its exported variable reached the Bash
tool's `echo`; `CLAUDE_PLUGIN_DATA` itself did not.

## Goals / Non-Goals

**Goals:** a consumer's first propose run validates the review without the person installing
anything (#309); one manifest for the plugin's runtime.

**Non-Goals:** removing `jsonschema` (ADR 0027 chose the standard validator); a consumer
`manual` row or project marker; changing the interpreter of the tool hooks, whose scripts use
only the standard library; Linux/macOS consumers (the plugin's supported platform is Windows),
though nothing in the script is Windows-only.

## Decisions

- **D1. The documented plugin-data pattern, in Python.** `plugin_env.py session-start` names the
  environment `venv-<first 12 hex of sha256 of ${CLAUDE_PLUGIN_ROOT}/.agent-process/requirements.txt>`
  under the data directory. When that directory has no `.complete` file, or its interpreter fails
  `-m pip check` (it cannot start once the base interpreter it was built from, possibly a project
  `.venv`, is deleted or replaced — architect review round 2), it runs
  `<python> -m venv --clear` there and `pip install -r`, then writes `.complete`. Keying by content
  replaces the doc's manifest copy and makes an install never touch another manifest's
  environment, which a parallel session may still be exporting (architect review: `venv --clear`
  in one shared directory would delete it). Older environments stay until the plugin is
  uninstalled; one appears only when the pins change. A script, not the doc's shell one-liner,
  because the interpreter path differs by platform (`Scripts/python.exe`, `bin/python`) and a
  failure must produce the hook JSON marker. Rejected: PEP 723 with `uv run` / `pipx run` (an undeclared
  tool replaces an undeclared package); vendoring (`rpds-py` is compiled); a consumer `manual`
  row (the person installs by hand what the plugin can).
- **D2. One manifest.** The plugin installs `.agent-process/requirements.txt`, which already
  pins `jsonschema`, is pip-audited and is this repository's CI runtime install. Two extra small
  packages (PyYAML, markdown-it-py) are installed into an environment nothing else uses, in
  exchange for no second pin set to keep in step.
- **D3. Hand-off through `CLAUDE_ENV_FILE`.** The hook appends
  `export AGENT_PROCESS_PYTHON='<interpreter>'` every session; the launcher runs
  `"${AGENT_PROCESS_PYTHON:-python}"`. Not a `PATH` prefix, which would replace the consumer's own
  `python` in the Bash tool. Tool hooks keep `python`: they do not source the file.
- **D4. Visible failure, retried.** On a failed `venv` or `pip`, or without `CLAUDE_PLUGIN_DATA`
  or `CLAUDE_ENV_FILE`, the hook exits 0 with `systemMessage` and `additionalContext` (the
  session-start marker shape of `skill_check.py`) naming
  `agent-process plugin environment not installed` and the cause (pip's last error line, or the
  missing variable); no `.complete` and no export are written, so the next session retries and
  the launcher falls back to `python`. Accepted, not marked: no `python` on the hook's PATH (the
  hook command fails and Claude Code reports the hook error) and a package deleted by hand from a
  completed environment that `pip check` still passes (the call site's exit 2 names the import;
  deleting the `venv-*` directory reinstalls it).
- **D5. Not gated on adoption.** The install is per user, not per project, and a consumer runs
  `init` and its first propose in one session; the adopted-repository gate stays on the tool
  hooks.

## Risks / Trade-offs

- The install runs once per machine and manifest, not per project: the data directory is per
  plugin. That first session runs `venv` and `pip` (network); the hooks doc says SessionStart
  runs in the background and Claude's first reply waits for it. Timeout 300 s; task 4.3
  measures the wait and the PR report records it.
- `CLAUDE_ENV_FILE` for a plugin hook is observed, not documented per hook source; if it
  regresses, the hook prints the marker (D4) and the launcher falls back to `python`.
- A session already running when the pins change keeps its export; its environment stays
  intact (D1).
- Two sessions starting together on a new manifest can both run `venv --clear` in the same
  directory; one may fail and print the marker, and the next session retries. Not locked (§VII).
- Rollback: revert the PR; the data directory is removed with the plugin.
