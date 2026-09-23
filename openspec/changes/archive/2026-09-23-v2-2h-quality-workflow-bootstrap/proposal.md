## Why

The installer's managed caller (`skills/agent-process/templates/agent-process.yml`, issue
[155](https://github.com/ekolvah/agent-process-distribution/issues/155)) calls a reusable
quality workflow with `setup` and `test` inputs, but `main` has no such callee:
`reusable-quality.yml` takes no inputs and is what the required `quality / quality` context of
the v1 `ci.yml` calls at `@main`. The frozen PR
[151](https://github.com/ekolvah/agent-process-distribution/pull/151) changed that callee in
place and swapped the caller in the same PR; run `35523639249` created zero jobs because the
caller passed the new inputs to the `@main` callee, which did not declare them yet.

Root cause: one PR both changed the interface that the required context reads from the
default branch and depended on the change. This change lands the new callee and a caller
beside v1 on `main`, so no required context depends on it
([parent issue 112](https://github.com/ekolvah/agent-process-distribution/issues/112); the
activation is issue 154).

Observations (details and run ids in `design.md`, Observations):

- The GitHub page on workflows says that a workflow run uses the workflow version in the event's
  commit, and the page on reusable workflows says that a `./` reference comes from the same
  commit as the caller.
- On disposable repository `ekolvah/agent-process-bootstrap-probe`, a bootstrap PR adding
  a callee and a caller beside a required `quality / quality` got both contexts on `opened`
  and merged under ruleset `23897425`. The next PR got the new context on `opened` without
  close/reopen.

## What Changes

- Add `.github/workflows/quality.yml`: a `workflow_call` callee with inputs `setup`
  (optional) and `test` (required) and one job `quality`. It verifies the PR links its issue,
  checks out the PR, sets up Python, and runs the two commands.
- Add the publisher caller `.github/workflows/agent-process.yml`. Its job `agent-process`
  calls `./.github/workflows/quality.yml` with this repository's setup and
  `python .agent-process/scripts/ci_check.py`, so the context is `agent-process / quality`,
  which is distinct from `quality / quality`.
- Point the consumer template at `quality.yml@v${version}` and rename its job to
  `agent-process`, so consumers report the same context. The pin stays an immutable release tag.
- Declare `agent-process` in `NOT_REQUIRED` of the v1 guard
  (`check_branch_protection.py`) with its reason. No required context is added or removed.
- Keep v1 `ci.yml`, `reusable-quality.yml`, `agent-review.yml`, and
  `reusable-agent-review.yml` byte-identical.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: add `The quality callee runs the caller's commands` and `Callers reach the
  quality callee` (consumer pin versus publisher same-commit path, one context name).

## Impact

- Added: `.github/workflows/quality.yml`, `.github/workflows/agent-process.yml`.
- Edited: `skills/agent-process/templates/agent-process.yml` (callee path, job key),
  `.agent-process/scripts/check_branch_protection.py` (`NOT_REQUIRED` entry),
  `tests/publisher/test_reusable_workflows.py` (new callee and callers),
  `tests/publisher/test_init.py` (`test_caller_inputs` path and job).
- Removed: nothing.
- ADR and docs: none. ADR 0027 decides that delivery uses reusable workflows. The archived
  `v2-2g-b-local-installer-lifecycle` design (D4, D5) decides the consumer caller's
  `setup`/`test` inputs and its `@v<version>` pin. The bootstrap path and its trust boundary are specific to this transition
  and are recorded in `design.md`. The installation guide describes v1 until issue 115.
- External systems: none from the PR itself. GitHub runs one more workflow per PR of this
  repository. Ruleset `23732345` is read back before and after the merge, not written.
