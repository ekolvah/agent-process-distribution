## Context

The observations are in proposal — Why. Every installer test builds its consumer through
`init_harness.consumer_repo` (the `sandbox` fixture, and `test_retry_after_each_write`'s own
sandboxes), with `HOME` and `USERPROFILE` set to the sandbox's `home`, so `$HOME/.gitconfig` is
the global git configuration of every git command the sandbox runs, the pre-push hook's
pre-commit clone included. The pre-push step tests (`test_init_remote.py`) assert that `init`
calls `pre-commit install --hook-type pre-push` and what the hook file then holds; the legacy
move in `test_foreign_pre_push_is_migrated` is pre-commit's own behaviour.

## Goals / Non-Goals

**Goals:** a sandbox git command never reaches the network; a sandbox push still runs the hook
`init` installed, which resolves the hook repository locally at `v{CURRENT}`, whatever tags the
real repository has.

**Non-Goals:** `npx` of `test_installed_footprint_is_closed` (`real_npx=True`) still needs the
npm registry — it is not a git URL and not a push; changing `init` or the rendered consumer
configuration.

## Decisions

**D1 — Git URL rewriting in the sandbox's global config.** `consumer_repo` writes
`url.<sb.repo as posix>.insteadOf = https://github.com/ekolvah/agent-process-distribution` into
`$HOME/.gitconfig` (the file's text is D4's); pre-commit fetches through git, so the rendered `repo:` resolves to the
fixture's `process.git` (observed, proposal — Why). The installed hook, the push through it and
pre-commit's clone all stay real. Alternatives rejected:
- A stub `pre-commit` on the sandbox's `which`: the hook file and the `pre-push.legacy` move
  would come from the stub, so `test_pre_push_hook_is_installed` and
  `test_foreign_pre_push_is_migrated` would test the stub.
- `git push --no-verify` injected by `Runner`: the command logged would differ from the command
  run, and no sandbox push would prove that `init`'s push goes through the hook it installed.
- `core.hooksPath` in the sandbox: `init` reads it as a blocked clone and plans no `pre-push`
  step, so the pre-push step tests would stop running.
- The real hook repository (`language: python`) behind the mapping: pre-commit `pip install`s
  it into a fresh cache per test, which needs the package index. `test_quality.py::
  test_hook_repository_runs_at_pre_push` already covers it.

**D2 — A network guard beside the mapping.** The same file sets `url.file:///no-network/.insteadOf
= https://`; the longer, process-repository match of D1 wins for that URL (observed). Any other
`https://` git URL a future test or `init` change reaches fails at once with a clone error in the
test's output (§IV), instead of passing only while the network and a tag exist. It is also the
RED of this change: with the guard and without D1, the five tests that failed on the release PR (#277) and the new test fail
on `main` exactly as on the release branch.

**D3 — A probe manifest in `process_repo`.** The fixture's `v{CURRENT}` commit adds a root
`.pre-commit-hooks.yaml` whose `quality` hook is `language: system`, `stages: [pre-push]`,
`always_run: true`, `pass_filenames: false`, with the entry `"<sys.executable in forward-slash
form>" -c "<touch $HOME/pre-push-ran>"`, as the probe ran; the double quotes keep an interpreter
path with a space one word when pre-commit splits the entry; `v{OTHER}` inherits it. The new test
`test_init_remote.py::test_sandbox_push_runs_the_local_hook` asserts the record is absent after
the first run (its push precedes the `pre-push` step) and present after a second run that
re-renders an owned file and pushes — the proof that the sandbox's push runs the installed hook,
locally.

**D4 — The profile proofs compare against the harness's own file.** `init_harness.snapshot` skips
only `.git`, so the new `$HOME/.gitconfig` would break `test_init.py`'s
`test_confirm_selects_release_before_composing` (`snapshot(sandbox.home) == {}`) and
`test_init_takes_no_quality_command` (`snapshot(sandbox.root, sandbox.home) == {}`). One harness
function `gitconfig(sb) -> str` renders the file's text, `consumer_repo` writes exactly it, and
`home_baseline(sb)` returns `{str(sb.home / ".gitconfig"): gitconfig(sb).encode()}`; the two tests
compare against that instead of `{}`. `init` writing any other file under `home`, or changing
that file's bytes, still fails them. Skipping `.gitconfig` in `snapshot` was rejected: a write by
`init` to the user's global git config would pass.

## Risks / Trade-offs

- [A test snapshots `home` across a run that pushes] → the record and pre-commit's cache land
  under `home`; the cache already did before this change (the network clone), so the snapshot
  class is unchanged. Task 2.2 runs the whole suite.
- [A machine without `pre-commit` on PATH] → `init` plans no `pre-push` step and the new test
  fails on the missing record, naming it; `pre-commit` is pinned in
  `.agent-process/requirements-dev.txt`, which the quality `setup` installs.
- Rollback: revert the PR. Nothing outside `tests/` changes.
