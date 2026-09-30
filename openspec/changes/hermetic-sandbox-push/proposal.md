## Why

Release PR #277 (3.2.3) fails `agent-process / pytest`: `test_update_keeps_consumer_bytes` and
the four `test_consumer_session_start_is_not_owned[*]` in `tests/publisher/test_init_config.py`
exit 1 from `install(..., "--confirm")`, while the same tests pass on `main`. The issue (#278)
reproduced it on the release branch: `git checkout v3.2.3` → `error: pathspec 'v3.2.3' did not
match any file(s) known to git`.

Root cause: since #276 the first `init` run of a test installs the real pre-commit `pre-push`
hook in the sandbox clone. A second run that re-renders an owned file commits and pushes the
installation branch, the hook runs, and pre-commit clones the consumer config's
`https://github.com/ekolvah/agent-process-distribution` at `rev: v<VERSION>` into the sandbox's
empty cache (`HOME` is the sandbox). A release PR bumps `VERSION` before its tag exists, so every
release PR goes red; on `main` the suite passes only with network access and a published tag.

Observed on 2026-09-30 (pre-commit 4.6.0, the pinned dev dependency), with a consumer whose
`.pre-commit-config.yaml` names that URL at `rev: v9.9.9` and `HOME` set to a scratch directory:

- `url.file:///no-network/.insteadOf = https://` in `$HOME/.gitconfig`:
  `pre-commit run quality --hook-stage pre-push` exits 3 (`Please make sure you have the
  correct access rights and the repository exists`) — the network clone fails at once.
- adding `url.<local repo>.insteadOf = https://github.com/ekolvah/agent-process-distribution`
  (the longer match wins), whose `.pre-commit-hooks.yaml` defines `quality` as a `language:
  system` probe and is tagged `v9.9.9`: exit 0, `[INFO] Initializing environment for
  https://github.com/ekolvah/agent-process-distribution.`, `quality ... Passed`, and the probe
  wrote its file.

## What Changes

- The sandbox's `$HOME/.gitconfig` (written by `consumer_repo`, the one helper every sandbox
  goes through) rewrites every `https://` git URL to a path that does not exist, and the
  process repository's URL to the fixture's local `process.git`: a sandbox git command cannot
  reach the network, and pre-commit resolves the hook repository locally.
- The `process_repo` fixture's `v{CURRENT}` commit carries a `.pre-commit-hooks.yaml` whose
  `quality` hook is a `language: system` probe that records its run under `$HOME`; the real
  hook repository (`language: python`, a `pip install` per clone) stays covered by
  `test_quality.py::test_hook_repository_runs_at_pre_push`.
- Not changed: `init`, the rendered `.pre-commit-config.yaml` (`repo` + `rev: v<version>` is the
  standard pre-commit distribution), and the message of a failed command (out of scope in #278).

## Capabilities

### New Capabilities

### Modified Capabilities

None. Only the test harness changes (`skip_specs`).

## Impact

- Edited: `tests/publisher/init_harness.py` (`consumer_repo`, `gitconfig`, `home_baseline`),
  `tests/publisher/conftest.py` (`process_repo`), `tests/publisher/test_init_remote.py` (the new
  test), `tests/publisher/test_init.py` (the two empty-profile assertions compare against the
  harness's own `.gitconfig`).
- Added, removed: none. No consumer, CI or product change; #277 goes green once this lands on
  `main` and release-please rebases it.
