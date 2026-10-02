---
status: "accepted"
date: 2026-10-02
decision-makers: ekolvah
---

# Edit-time lint runs the project's pre-commit config

## Context and Problem Statement

Edit-time lint is the cheapest feedback loop of a session; without it a finding surfaces only
at the pre-push `quality` hook or in CI. This repository declared ruff twice, by bespoke code
each time: `ci_check.py` for the gate and `.agent-process/scripts/hooks.py on-edit` for edit
time. Consumers got no edit-time lint, and the plugin cannot assume one linter in a mixed-stack
consumer (#321). The industry standard declares per-file checks once, in
`.pre-commit-config.yaml`, with the hook repositories the tools publish, and lets every trigger
read that file.

## Considered Options

* The plugin runs the project's `pre-commit`-stage hooks after each edit; the gate runs the same
  hooks over all files
* An `edit_check` key in `.github/agent-process-quality.json`
* Ship `hooks.py` in the plugin

## Decision Outcome

Chosen: **per-file checks are declared once, in `.pre-commit-config.yaml` at the `pre-commit`
stage, and the plugin's edit-time hook and the gate are its triggers**, in line with
[ADR 0027](0027-v2-standards-replace-the-bespoke-control-plane.md).

* The plugin's `PostToolUse` `Edit|Write` hook runs `agent-process edit_lint post-edit`:
  `pre-commit run --hook-stage pre-commit --files <edited path>`. A failure reaches the agent
  with exit 2; a missing `pre-commit` is a marker. Its timeout is 120 s, since a first
  hook-environment install took 13.5 s and a timeout discards the output.
* Formatters may rewrite the edited file; the next `Edit` succeeds against the new content.
* This repository declares `ruff-check` and `ruff-format` of `astral-sh/ruff-pre-commit`; the
  hook's `rev` is ruff's only pin. `ci_check` `lint` runs `pre-commit run --hook-stage
  pre-commit --all-files --show-diff-on-failure`; `format` is no longer a check. `hooks.py` and
  its settings entry are deleted.
* No git `pre-commit` hook is installed: only agents write code in an adopted repository, the
  edit-time run is their per-file feedback, and push and CI are the gate.
* A consumer's declared `test` decides what its gate runs; SKILL.md Install recommends running
  `pre-commit run --hook-stage pre-commit --all-files` there.

### Consequences

* Good, because one file declares the checks, and the edit-time run is a subset of the gate.
* Good, because the plugin knows no linter; a consumer with no `pre-commit`-stage hooks sees
  nothing.
* Bad, because every edit spends about 0.5 s on a pre-commit start, and the first run of a hook
  environment installs it from the network.
* Bad, because the gate's format step rewrites unformatted tracked files across the checkout;
  the agent commits only the files of its own change.

### Confirmation

`tests/publisher/test_edit_lint.py`, `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`,
`::test_publisher_lints_at_edit_time` and
`tests/agent_process/test_ci_check.py::test_lint_runs_the_commit_stage_hooks`.

## Native alternatives considered

| Script | Native feature tried or ruled out | Why it falls short |
| --- | --- | --- |
| `edit_lint` | A hook command `jq -r '.tool_input.file_path' \| xargs pre-commit run --files` (the hooks guide's pattern) | `jq` is not on every consumer's machine, and a bare pipe cannot turn a missing `pre-commit` into a marker or a failed run into exit 2 |
| `edit_lint` | The git `pre-commit` hook | It runs at commit, after the agent has moved on; only agents write code here, so the edit is the moment to report |

## Deletion condition

* Claude Code runs a project's pre-commit hooks after edits natively, or pre-commit gains an
  editor/agent hook mode a plugin can enable without a script → `edit_lint.py` and its hook are
  deleted.
