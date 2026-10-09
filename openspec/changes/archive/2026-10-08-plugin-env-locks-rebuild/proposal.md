## Why

`plugin_env.install()` builds `venv-<digest>` in place with `python -m venv --clear` and takes no
lock. Environments of different manifests never collide, but two sessions on the same manifest
do. Two sessions start together after a plugin update. Neither sees `.complete`, so both run
`venv --clear` on the same directory. The second clear deletes the first session's install
halfway, or one session writes `.complete` into a directory the other has just emptied.
`AGENT_PROCESS_PYTHON` then names a missing or partial interpreter, and every `agent-process`
script fails until a later session rebuilds the environment. Parallel sessions are the normal way
this repository is worked on.

Reproduced on `main` (8ee412f) in-process. A wrapper around `_run` starts a second `install()`
while the first runs `pip install`. Each row is the command, whether `venv-<digest>` exists, and
whether it has `.complete`:

```
('-m venv --clear', False, False)
('-m pip install', True, False)
('-m venv --clear', True, False)   <- the second session clears the first one's directory
('-m pip install', True, False)
```

Root cause: nothing serializes the check-then-build sequence across processes that share
`${CLAUDE_PLUGIN_DATA}`. pre-commit faces the same problem: hook environments named by hash in a
shared cache, a completion marker, and a rebuild when a health check fails. It solves it with an
exclusive file lock in the cache directory and a second check under the lock (`store.py`
`exclusive_lock`, `repository.py` `install_hook_envs`).

## What Changes

- An install that finds no usable environment takes an exclusive lock on `${CLAUDE_PLUGIN_DATA}/.lock`,
  checks again, and builds in place only if the environment is still unusable. A session that
  waited reuses the environment the lock holder completed.
- An install that cannot take the lock within 240 seconds, below the hook's 300-second timeout,
  fails with the existing `agent-process plugin environment not installed` marker, naming the wait.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: "The plugin installs its runtime environment" runs installs one at a time,
  reuses the environment a parallel install completed, and bounds the wait.

## Impact

- Edited: `skills/agent-process/scripts/plugin_env.py` (a lock helper, `install`, module
  docstring).
- Edited: `tests/publisher/test_plugin.py` (two new tests; the existing session-start tests stay as
  they are).
- Edited by archive: `openspec/specs/distribution/spec.md`.
- Not edited: `hooks/hooks.json` (same command and timeout) and `bin/agent-process`. The layout of
  `${CLAUDE_PLUGIN_DATA}` gains only `.lock`, so existing environments stay valid. No ADR records
  this hook's build, so no ADR changes.
- Consumers get the fix with the plugin update. Nothing changes on their side.
