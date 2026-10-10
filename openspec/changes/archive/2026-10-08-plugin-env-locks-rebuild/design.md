## Context

See proposal.md, Why. `install(data)` in `skills/agent-process/scripts/plugin_env.py` is called
once per session by the plugin's `SessionStart` hook (timeout 300 s, asserted by
`tests/publisher/test_plugin.py::_session_start`). The hook runs under the bare `python` of the
session, before the environment exists. It can import only the standard library, so the
`filelock` package is not available.

Prior art. A shared cache of environments named by content, used by parallel processes, is
pre-commit's store. pre-commit takes `store.exclusive_lock()` (a `.lock` file in the store), and
`install_hook_envs` checks `_need_installed()` before the lock and again under it, with the comment
"Another process may have already completed this work". It then installs in place. Its
`file_lock.py` uses `fcntl.flock` (`LOCK_EX | LOCK_NB`, then blocking) on POSIX and
`msvcrt.locking` on Windows. uv and Nix build in a temporary directory and rename it into place.
For a venv that means moving it, and the venv documentation calls environments "inherently
non-portable, in the general case".

Platform observations this design rests on (`lockprobe.py` in a scratch directory; Windows 11 with
Python 3.12.8, and `docker run python:3.12-slim` with Python 3.12.15):

| Probe | Windows (`msvcrt.locking`, `LK_NBLCK`, 1 byte) | Linux (`fcntl.flock`, `LOCK_EX \| LOCK_NB`) |
|---|---|---|
| first handle in a process | acquired | acquired |
| second handle of the same file, same process | `PermissionError 13` | `BlockingIOError 11` |
| while a child process holds it | `PermissionError 13` | `BlockingIOError 11` |
| after that child is killed | acquired | acquired |

Both error types are `OSError`. The OS releases the lock of a killed holder, so a hook killed at
its timeout leaves no stale lock. A second handle conflicts within one process, so threads in one
test process contend the way two sessions do.

## Goals / Non-Goals

**Goals:**
- Two sessions never build the same environment at the same time, and the second reuses the
  first one's result.
- A session that cannot get the lock ends with the visible marker, not with a hook killed at its
  timeout.

**Non-Goals:**
- Protecting a session that is running from an environment while another session rebuilds it
  after a failed `pip check` (see Risks).
- A lock per manifest. One `.lock` per data directory, as in pre-commit's store. Installs of two
  manifests at once are rare: after an update only new sessions install.

## Decisions

### D1. Exclusive lock with a check before and under it

`install` keeps its fast path: if the environment is usable (`.complete` exists and
`pip check` passes), it returns the interpreter without the lock. Otherwise it creates `data`,
takes the lock on `data / ".lock"`, and checks again. If the environment is now usable, another
session built it, and `install` returns its interpreter. Otherwise `install` builds in place as
today: unlink `.complete`, `venv --clear`, `pip install`, write `.complete`. The OS releases the
lock when the hook exits or is killed.

The lock helper `_locked(path)` is a context manager of about 20 lines. It opens `path` in `a+b`
mode and polls a non-blocking lock every second: `fcntl.flock(LOCK_EX | LOCK_NB)` on POSIX,
`msvcrt.locking(LK_NBLCK, 1)` on Windows. On Windows it unlocks with `LK_UNLCK` before closing,
because the docs recommend unlocking explicitly. It retries only on the errors the Context table
observed for a held lock: `PermissionError` on Windows, `BlockingIOError` on POSIX. Any other
`OSError` (for example `ENOLCK`) propagates with its own cause instead of turning into a 240 s
wait and a false "another session held" marker.

Alternative: build in a temporary sibling and publish with `os.rename`, as uv and Nix do.
Rejected. It moves a venv, which the venv documentation calls non-portable. The move works for
`python -m` (observed on Windows and Linux), but every console script in the environment keeps the
old path in its shebang. The rename design also needs a second branch for replacing a broken
environment, and a race analysis of its own.

Alternative: a separate environment per session. Rejected. Every session would pay `venv` plus
`pip install` and need the network at start. Environments of crashed sessions need a sweep, and a
sweep cannot tell them from live ones. Claude Code's plugin reference presents
`${CLAUDE_PLUGIN_DATA}` as the place for "Installed dependencies such as `node_modules`,
generated code, and caches" kept across updates, which is a shared cache.

### D2. Bounded wait reported as the marker

`LOCK_WAIT = 240` seconds, below the hook timeout of 300. When the deadline passes, `_locked`
raises `InstallError(f"another session held {path} for {LOCK_WAIT} s")`. `session_start` turns it
into the existing marker, and the next session retries. Without a bound, a session that waits
behind a slow install would be killed at 300 s with no marker and no export.

### D3. Test seam: `_run`, and threads as sessions

The new tests load `plugin_env` in-process, set `MANIFEST` to a manifest in `tmp_path`, and
replace `_run` with a wrapper that records each command per thread and then calls the real `_run`.
`_run` is the module's only subprocess boundary, so every real command still runs. Each test
session is a thread that calls `install(data)`. Per the Context table, the lock contends between
threads as it does between processes. `LOCK_WAIT` is a module constant, and the timeout test sets
it with `monkeypatch.setattr(..., raising=False)`, so on `main` the test fails in its body. That
test asserts the original value is 240 after its behaviour assertions. A thread that a test blocks
waits on a bounded event and is released and joined in a `finally`, so a failing assertion never
leaves a non-daemon thread hanging the run. The existing tests drive the hook as a subprocess and
stay as they are.

## Risks / Trade-offs

- [A session rebuilds an environment another running session uses, after its own `pip check`
  failed] → Accepted. `pip check` reads installed metadata locally and has no network step, so a
  failure means the environment is broken for every session that uses it. Rebuilding is the
  repair. pre-commit makes the same trade.
- [The fast path reads `.complete` without the lock] → A session can pass the fast path just
  before a lock holder unlinks `.complete` to rebuild. This only happens in the rebuild case above,
  and it is accepted with it.
- [A session waits behind a slow first install] → Its start is delayed by up to 240 s, then it
  shows the marker. Without the lock it would have cleared the first install.
- [A hook killed mid-build leaves the environment without `.complete`] → The OS releases the
  lock. The next session sees no `.complete` and rebuilds under the lock, as today.

## Migration Plan

Existing `venv-<digest>` directories stay valid: their path and the usability test do not change.
`.lock` appears in `${CLAUDE_PLUGIN_DATA}` on the first install that needs it. To roll back,
revert the commit. The old code ignores `.lock`.
