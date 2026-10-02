## 0. Delivery start

- [x] 0.1 Run `agent-process start_change declare-jsonschema-prerequisite --planner Claude --implementer Claude` for tracking issue 309. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/declare-jsonschema-prerequisite`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py`, add `_session_start(tmp_path, manifest, **env)`: copy `skills/agent-process/scripts/plugin_env.py` into a temporary plugin root beside `.agent-process/requirements.txt` holding `manifest`, and run the one `SessionStart` command of `hooks/hooks.json` through `_run_plugin_hook` with `CLAUDE_PLUGIN_ROOT` that root, `CLAUDE_PLUGIN_DATA` and `CLAUDE_ENV_FILE` under `tmp_path`. Add `plugin_env.py` as a stub whose `main` returns 0, so the tests fail in their bodies, and add `plugin_env.py` to both closed sets `MOVED_SCRIPTS` (`tests/publisher/test_plugin.py:25`, `tests/publisher/test_start_change.py:23`)
- [x] 1.2 Add `test_session_start_installs_the_plugin_environment` with a comment-only manifest (no download): the first run exits 0 with empty stdout, the env file exports `AGENT_PROCESS_PYTHON` naming an existing interpreter inside a `venv-*` directory of the data directory that holds `.complete`; a second run exits 0, leaves that `pyvenv.cfg`'s mtime unchanged and exports the same interpreter again; after the interpreter file is deleted, a third run exits 0 with empty stdout, recreates it and exports it (spec *First session*, *Manifest unchanged*, *Broken environment*)
- [x] 1.3 Add `test_session_start_keeps_the_previous_environment`: after a run with one comment-only manifest, a run with a different comment exports an interpreter in a second `venv-*` directory, and the first directory's `pyvenv.cfg` mtime and `.complete` are unchanged (spec *Manifest changed*)
- [x] 1.4 Add `test_session_start_reports_a_missing_environment`, parametrized: `pip` — manifest `agent-process-no-such-package==0` with `PIP_NO_INDEX=1`, then no `.complete` and a second run installs again (same failure, the marker again); `data` — no `CLAUDE_PLUGIN_DATA`; `env-file` — no `CLAUDE_ENV_FILE`. Each exits 0, `systemMessage` and `additionalContext` name `agent-process plugin environment not installed` and the cause (`pip`'s error, or the missing variable's name), and no export is written (spec *Install fails*, *Hook variables absent*)
- [x] 1.5 Add `test_launcher_runs_the_session_interpreter`: `_run_launcher` gains an `env` argument; with `AGENT_PROCESS_PYTHON` an executable `sh` script printing `session` and its arguments, `agent-process probe a` prints `session` and the probe's path and `a` (spec *Launcher uses the session interpreter*). Restrict `test_plugin_hooks_are_silent_outside_an_adopted_repository` to `PreToolUse` and `PostToolUse` (modified requirement)
- [x] 1.6 Run `agent-process check_red` with the node ids of 1.2–1.5, quoted. Verify that each fails in its body: no `SessionStart` entry, no export, no marker, `python` instead of the session interpreter; and that `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py` fail nowhere else. Commit as `test(distribution): the plugin installs its runtime environment`

## 2. Environment and launcher

- [x] 2.1 Implement `skills/agent-process/scripts/plugin_env.py session-start` per design D1, D3, D4 (`venv-<sha256[:12]>` of the manifest; without `.complete` or when its interpreter fails `-m pip check`, `sys.executable -m venv --clear` there, then the environment's `python -m pip install --disable-pip-version-check -q -r <manifest>`, then `.complete`; the interpreter is `Scripts/python.exe` on Windows and `bin/python` otherwise; append the export when `.complete` exists; a missing variable or a failed step prints the hook JSON marker with its cause and writes nothing). In `hooks/hooks.json` add `SessionStart` running `python "${CLAUDE_PLUGIN_ROOT}/skills/agent-process/scripts/plugin_env.py" session-start`, timeout 300, not gated (D5). In `bin/agent-process` run `exec "${AGENT_PROCESS_PYTHON:-python}" "$file" "$@"` and say so in its header comment. Verify that `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_start_change.py -q` passes. Commit as `fix(distribution): the plugin installs and runs its own environment`

## 3. Documentation

- [x] 3.1 In `skills/agent-process/SKILL.md` Install, one sentence: the plugin installs its Python dependencies itself at session start, and a failure shows the `agent-process plugin environment not installed` marker. In `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`, replace the sentence calling a consumer's `jsonschema` a prerequisite with the plugin environment that installs it (#309). Verify that `python -m pytest tests/publisher/test_planning_workflow.py tests/agent_process/test_adr_records.py tests/agent_process/test_doc_links.py -q` passes. Commit as `docs(distribution): the plugin installs jsonschema`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 4.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes
- [x] 4.3 Live check (Principle V): remove `~/.claude/plugins/data/agent-process-inline` (the data directory of a `--plugin-dir` load, observed as `<name>-inline`), then run `claude -p --plugin-dir <worktree>`, asking the Bash tool to run `agent-process start_change --help` and print `$AGENT_PROCESS_PYTHON`; verify the export names the data directory's interpreter and the script runs. Time the run against a second one with the environment in place, so the first reply's wait for the install is measured. Record both outputs and the wait in the PR report

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `agent-process archive_change declare-jsonschema-prerequisite`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "fix: declare-jsonschema-prerequisite" --body-file <report>`. The report references the tracking issue plainly (#309), never with `Closes`, and carries the scenario → test map and the live check of 4.3
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / First session, Manifest unchanged, Broken environment → `tests/publisher/test_plugin.py::test_session_start_installs_the_plugin_environment`
- `distribution` / Manifest changed → `tests/publisher/test_plugin.py::test_session_start_keeps_the_previous_environment`
- `distribution` / Install fails, Hook variables absent → `tests/publisher/test_plugin.py::test_session_start_reports_a_missing_environment` (`pip`, `data`, `env-file`)
- `distribution` / Launcher uses the session interpreter → `tests/publisher/test_plugin.py::test_launcher_runs_the_session_interpreter`
- `distribution` / Unadopted repository (modified: tool hooks) → `tests/publisher/test_plugin.py::test_plugin_hooks_are_silent_outside_an_adopted_repository`
