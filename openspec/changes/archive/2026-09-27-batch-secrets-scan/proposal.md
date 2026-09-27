## Why

On Windows `ci_check` — and so the `pre-push` hook — fails in the `secrets` check with
`FileNotFoundError: [WinError 206] The filename or extension is too long` (issue 231).
Reproduced on `remove-additions-rule` at `c50e7eb`: `_secrets_targets(_tracked_files())` is 490
files and `subprocess.list2cmdline(_secrets_cmd(targets))` is 33135 characters, over the
32767-character `CreateProcess` command line.

Root cause: `check_secrets` passes every target to `detect_secrets.pre_commit_hook` as the argv
of one process. The list grows with every archived change, so every Windows push fails once it
crosses the limit; Linux CI does not hit it.

## What Changes

- `check_secrets` splits the targets into batches whose command line stays under the Windows
  limit and runs the hook once per batch; a finding in any batch fails the check. The empty-list
  refusal stays.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: `ci_check` scans secrets within the command-line limit.

## Impact

- Edited: `.agent-process/scripts/ci_check.py` (`check_secrets`, a batching helper).
- Edited: `tests/agent_process/test_ci_check.py` (the scenario's test).
- Added: `openspec/changes/batch-secrets-scan/` (archived into `openspec/specs/implementation/spec.md`).
- No docs or ADR apply: the gate's contract is unchanged, only how its argv is passed.
