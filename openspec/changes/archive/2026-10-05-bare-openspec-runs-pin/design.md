## Context

See proposal.md — Why. `bin/agent-process` is already on the Bash tool's `PATH` while the plugin
is enabled (observed this session, and the `Skill commands run from a consumer root`
requirement). `npx` in git-bash resolves to `/c/Program Files/nodejs/npx`, a shell script
(`command -v npx`, this session).

## Goals / Non-Goals

**Goals:** bare `openspec` runs the pin in every session with the plugin; the pin is written
once in Python and once in `bin/openspec`, and a test holds them equal.

**Non-Goals:** the `generatedBy` field of the generated OpenSpec files (upstream writes it;
`init` regenerates them when the recorded pin changes).

## Decisions

**D1 — `bin/openspec` runs `exec npx -y @fission-ai/openspec@<pin> "$@"`.** It sits beside
`bin/agent-process` and needs no Python. Alternatives: `npm install -g` (#343: fixes one
machine, adds an unpinned or hand-pinned copy; tried and removed); a Node dependency in the
consumer (adds `package.json` to repositories that have none); a SessionStart alias (the Bash
tool does not keep aliases between calls).

**D2 — `init.py`'s `OPENSPEC` is the source; `bin/openspec` is a tested copy.** `init` needs the
version as a value (it records `# openspec: <pin>` and compares it), and a shell launcher cannot
read a Python constant without starting Python on every call. Parsing the shell file from Python
was rejected as the more fragile direction. `archive_change.py` imports `OPENSPEC` from `init`
(as `start_change.py` already imports from it); `tests/publisher/openspec_cli.py` and
`test_init_config.py` read it through `load_init()`.

**D3 — `archive_change.py` keeps `npx`, not bare `openspec`.** Python on Windows does not run an
extensionless shell script (`shutil.which` honours `PATHEXT`), and the publisher tests and CI
have no plugin `bin/` on `PATH`. `test_pr_delivery.py` keeps matching `cmd[0] == "npx"`.

**D4 — `SKILL.md` prints bare `openspec`.** The skill and `bin/` ship in one plugin version, so a
session that reads the new text has the launcher. This change's own tasks still use the `npx`
form: the installed plugin (3.8.1) has no `bin/openspec` until the release. The existing
launcher sentence of `SKILL.md` (lines 10–12) names `openspec` beside `agent-process`; no new
sentence is added.
The bare command is resolved by the caller's `PATH`, so:
- Failure modes: a global `openspec` of another version earlier on `PATH` (the plugin's `bin/`
  comes last) runs Verify's `validate --strict --all` and `new change` silently at that version;
  a session whose installed plugin predates `bin/openspec` gets `openspec: command not found`,
  which is visible.
- Lost proof: Verify's own command no longer guarantees validation at the pin.
- Catcher actually reached: `tests/publisher/test_openspec_valid.py::test_openspec_changes_and_specs_validate_strictly`
  runs the pin through `tests/publisher/openspec_cli.py` inside the declared `test`
  (`ci_check.py`) — locally in Verify 3.2 and in `quality.yml` on every PR head.

**D5 — the `One pin` test.** It reads `git ls-files` outside `openspec/changes/` (plans and
archived history quote the command of their time) and matches
`@fission-ai/openspec@([0-9A-Za-z][^\s"'`)]*)` — a version or a tag such as `latest`, not the
f-string `{OPENSPEC}`. The only allowed match is `bin/openspec`, equal to `init.OPENSPEC`. Today
it fails naming `SKILL.md`, `archive_change.py` and `openspec_cli.py`, and the missing
`bin/openspec`. It supersedes `test_planning_workflow.py::test_pinned_openspec`, which
required the literal pin in `SKILL.md` and `archive_change.py`; that test is removed. The `Bare command` test copies `bin/openspec` into a temporary plugin, puts a
fake `npx` that prints `[%s]` per argument and exits 3 ahead of it on `PATH`, and runs
`sh -c "openspec a 'b c'"` as `_run_launcher` does.

## Risks / Trade-offs

- [New file committed without the executable bit on Windows] → `git update-index --chmod=+x`
  in the task, and `test_launcher_is_executable_in_git` covers both launchers.
- [First `openspec` call downloads the package] → unchanged from the current `npx` form.

## Migration Plan

Consumers get `bin/openspec` with the plugin update; nothing to run. Rollback: revert the PR;
the `npx` form keeps working.
