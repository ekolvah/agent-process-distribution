## Why

The tracking issue (#88) reports that the mandatory pre-push route selected the WSL launcher
`C:\Windows\System32\bash.exe` on Windows. Reproduced on v2 on 2026-09-29 (Windows 11, Git
2.45.1.windows.1, WSL without a distribution), with PATH rebuilt from the registry (Machine + User)
as a new terminal or the IDE sees it:

- `where.exe bash` lists `C:\Windows\System32\bash.exe`, then `...\WindowsApps\bash.exe`, then
  `C:\Program Files\Git\bin\bash.exe`. `shutil.which("bash")` returns `C:\WINDOWS\system32\bash.EXE`,
  and running it prints `WSL (9) ERROR: CreateProcessEntryCommon:505: execvpe /bin/bash failed 2`
  and exits 1.
- `python -m pytest tests/agent_process/test_pre_push_hook.py`: `8 failed, 1 passed`. Each failing
  run is `CompletedProcess(args=['C:\\WINDOWS\\system32\\bash.EXE', ...])`, with UTF-16 WSL text on
  stdout and `stderr=''`. The full `python -m pytest` run gives `1 failed, 428 passed`: the failure is
  `tests/publisher/test_reusable_workflows.py::test_trusted_checkout_is_the_called_commit`, from the
  same `shutil.which("bash")` at line 99.
- The hook route itself works. `git hook run pre-push` on a probe hook with `#!/usr/bin/env bash`,
  run under the same PATH, prints `MINGW64_NT-10.0-26200` and `BASH=/usr/bin/bash` and exits 0: Git for
  Windows runs hooks with its own bash, not the first `bash` on PATH.

Root cause: the two test harnesses that execute shell code take `shutil.which("bash")`. On Windows,
the PATH order puts `System32` ahead of Git, so that call returns the WSL launcher. The tests then
report failures that look like defects in the hook or the workflow guard. `ci_check` runs both test
files, so the quality command fails the same way when it is started from a native terminal. It stays
green only when it inherits Git's PATH, as it does under the hook or in the Bash tool.

## What Changes

- Add a test helper `tests/agent_process/git_bash.py::git_bash()`. On Windows it returns the bash
  of the Git installation that runs the hooks, derived from `git --exec-path`. It never searches
  PATH on Windows, and it fails with the path it expected when that bash is missing. On other
  systems it returns `shutil.which("bash")`, as before.
- `test_pre_push_hook.py` and `test_reusable_workflows.py` execute shell code through
  `git_bash()`.
- Not changed: the hook, `ci_check`, and the push route, which already run Git's bash (see Why).
  The issue's UTF-8 point is already met, because both harnesses capture with `encoding="utf-8"`. The
  empty stderr came from the WSL launcher writing UTF-16 to stdout.

## Capabilities

### New Capabilities

### Modified Capabilities

None. Only the test harness changes (`skip_specs`).

## Impact

- Added: `tests/agent_process/git_bash.py`, `tests/agent_process/test_git_bash.py`.
- Edited: `tests/agent_process/test_pre_push_hook.py` (`_bash`),
  `tests/publisher/test_reusable_workflows.py` (`_run_guard`).
- Removed: none. No consumer or CI change: on Linux the selection is the same as before.
