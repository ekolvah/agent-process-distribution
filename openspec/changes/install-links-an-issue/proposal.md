## Why

Install ends on an installation PR that the `link` step of `agent-process / quality` fails, because
nothing creates or links an issue (#247).

**Observation (2026-09-28, `ekolvah/agent-process-sandbox-2`, plugin 3.0.0).** PR 1 failed
`agent-process / link` with `PR 1 links no issue` (run 36419437237), and `quality` with it.
`gh pr view 1 -R ekolvah/agent-process-sandbox-2 --json headRefName,closingIssuesReferences,body`
now shows head `install-agent-process`, links `[2]`, and a body starting `Closes #2`: the PR went
green only after issue 2 (`Install agent process 3.0.0`) was made by hand and linked in the body.
The first sandbox was unblocked the same way (ekolvah/agent-process-sandbox#2).

**Root cause.** The check is right: `review-and-merge` / *A PR links its issue* requires the link on
every non-release PR. The gap is in the installer: `init` stops at uncommitted files (*Init writes
only the Project remotely* forbids it to commit or push), so the person makes the branch, commit and
PR by hand, and no step makes the issue. Adding the steps to SKILL.md prose would leave the link to
the person's execution, which no test can hold.

## What Changes

- **BREAKING** `init --confirm` opens the installation PR itself, as tools that install into a
  repository do (Renovate's onboarding PR `renovate/configure`, pre-commit.ci's autoupdate PR): on
  branch `agent-process/install-<version>` from the default branch it writes the files, commits
  them, finds or creates the open issue `Install agent-process <version>`, pushes the branch, and
  opens a PR to the default branch whose body starts `Closes #<N>`. The installer no longer leaves
  its changes uncommitted.
- The five new transitions are planned, reported and retried like the others; a run that would
  mix the installer's changes with the person's (dirty worktree, another branch, the installation
  branch present but not checked out) is a `conflict` before any write.
- SKILL.md Install steps 4–5: the person reviews the printed PR instead of committing and opening
  it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: *Init writes only the Project remotely* becomes *Init's remote writes are the
  Project and the installation PR*; new *Init opens the installation PR*.

## Impact

Edited: `skills/agent-process/scripts/init.py` (steps, docstring), `skills/agent-process/SKILL.md`
(Install steps 4–5), `tests/publisher/init_harness.py`, `tests/publisher/conftest.py`,
`tests/publisher/test_init_remote.py`, `tests/publisher/test_init.py`.

Added, removed: none. No ADR: design.md records the decision and its alternatives. Consumers
get it with the next release; `init --dry-run` shows the new transitions before any write.
