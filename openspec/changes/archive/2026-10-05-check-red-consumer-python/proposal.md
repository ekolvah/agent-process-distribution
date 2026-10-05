# Proposal

## Why

`agent-process check_red` cannot run a consumer's tests (issue 342). Reproduced in this
repository with plugin 3.8.1, `AGENT_PROCESS_PYTHON` set by the SessionStart hook:

```
$ agent-process check_red tests/publisher/test_check_red.py::test_runner_owns_the_selection
check_red: cannot evaluate the junit report: [Errno 2] No such file or directory: '...\red.xml'
--- pytest output ---
...\venv-afaa303d915e\Scripts\python.exe: No module named pytest
rc=2
```

Root cause: since change `declare-jsonschema-prerequisite` (#334) the launcher runs every script
with the plugin environment, and `check_red` runs `sys.executable -m pytest`, so pytest runs in
that environment. It holds only the plugin's runtime manifest — no pytest, and none of the
consumer's dependencies, which the consumer's tests import. Installing pytest there would not
help: the test run needs the consumer's interpreter. The script itself imports only the
standard library; it runs in the plugin environment because the launcher runs every script there.

## What Changes

- `check_red` runs `python -m pytest` of the `python` on `PATH` — the interpreter the
  consumer's tests run under, as the baseline `pytest` pre-commit hook already does — instead of
  its own interpreter. The script itself keeps running under `AGENT_PROCESS_PYTHON`.
- `python` absent from `PATH` is no verdict: exit 2 naming `python`, nothing run.
- `SKILL.md` Group 1 and the script's docstring say the same.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: requirement "RED first for behavioural changes" — the runner is the `python`
  on `PATH`, not the script's interpreter; a missing `python` is exit 2.

## Impact

- Edited: `skills/agent-process/scripts/check_red.py`, `tests/publisher/test_check_red.py`,
  `skills/agent-process/SKILL.md` (Group 1 sentence).
- Spec: `openspec/specs/implementation/spec.md` through this change's delta.
- No file added or removed; the launcher and `plugin_env.py` are unchanged.
