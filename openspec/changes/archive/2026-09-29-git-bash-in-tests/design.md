## Context

The observations are in proposal — Why. CI runs on Linux, where `shutil.which("bash")` is correct.
The defect exists only for a Windows process whose PATH is not Git's own.

## Goals / Non-Goals

**Goals:** on Windows, the tests run shell code with the same bash that Git uses for the hook, and
fail loudly when it is missing.

**Non-Goals:** changing the hook, `ci_check`, or interpreter selection anywhere outside the tests.

## Decisions

**D1 — Git's bash from `git --exec-path`.** Git for Windows reports
`C:/Program Files/Git/mingw64/libexec/git-core` as its exec path. Going up three parents gives the
installation root, and `usr/bin/bash.exe` under it is the interpreter that ran the probe hook
(`BASH=/usr/bin/bash`, MINGW64). Launched by Windows Python from the registry PATH, that bash exits 0
and prints `/usr/bin/bash msys`. Alternatives rejected:
- `git var GIT_SHELL_PATH` prints the MSYS path `/bin/sh` (observed), which Windows Python cannot
  run, and it names `sh` rather than bash. `BASH_ENV` in `test_pre_push_hook.py` needs bash.
- Dropping `System32` and `WindowsApps` from the PATH search is a denylist of launchers. Both
  directories hold a `bash.exe` here, and the next launcher would pass the filter.
- A hardcoded `C:\Program Files\Git` breaks on any other install location.
- Running the hook through `git hook run pre-push` would test the real route, but git would read
  the test's `GIT_DIR` itself, so `test_clears_repository_local_git_environment` would stop proving
  that the hook clears it.

Consumer of the replaced input: `test_missing_interpreter_fails_loudly` sets the hook's PATH to
the directory of `_bash()` alone. `Git\usr\bin` holds no `git.exe`, so on Windows the hook would
exit 2 at `git rev-parse --local-env-vars` (`pre-push:6-9`) before its interpreter loop, and the
test would still pass without proving what it is meant to prove. The test therefore gets the
bash directory plus the directory of `shutil.which("git")` as its PATH, and it asserts
`no supported Python interpreter found` in stderr. That assertion catches the lost proof on every
platform.

Found in implementation: the hook test's interpreter stubs start with `#!/usr/bin/env bash`, so
`env` searches PATH for bash again. Under the registry PATH that finds the WSL launcher, the stub
never runs, and the hook falls through to `py -3.12`. The real Python then fails on the stub
tree's missing `ci_check.py` (4 failures). Git itself puts its own directories first on PATH when
it runs a hook, which is why the probe hook printed `BASH=/usr/bin/bash`. `_run` does the same:
it puts the `git_bash()` directory first on the hook's PATH. `test_missing_interpreter_fails_loudly`
therefore passes only the directory of `git`.

**D2 — No PATH fallback on Windows.** When `git` does not start or `usr/bin/bash.exe` is missing,
`git_bash()` fails the test with the command or path it expected (§IV). A fallback to
`shutil.which` would bring the WSL launcher back silently.

**D3 — One helper for both harnesses.** `tests/agent_process/git_bash.py` is a helper module, not
a test module, so the import guard (`tests.**.test_*` in `[tool.tach]`) allows it. Both test files
import `from tests.agent_process.git_bash import git_bash`, the way publisher tests import
`tests.publisher.*` helpers. `ci_check` runs `python -m pytest`, which puts the checkout root on
`sys.path`, so the import resolves under the process config too. Task 2.1 verifies both runs.

## Risks / Trade-offs

- [A Git for Windows layout without `usr/bin/bash.exe` under the exec path's third parent] → D2
  fails the test with the path it expected, and the helper is the one place to fix.
- [The RED test needs `System32\bash.exe`, which exists only where the WSL feature is on] → it
  is skipped, with a stated reason, off Windows and where that launcher is absent. The machine that
  reproduced the issue has the launcher.
- Rollback: revert the PR. Nothing outside `tests/` changes.
