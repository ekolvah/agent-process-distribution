## Why

After the local installer lifecycle ([issue 155](https://github.com/ekolvah/agent-process-distribution/issues/155))
`init` composes a consumer's files but leaves it without a board: `set_status.py`,
`create_tracking_issue.py`, and `start_change.py` need exactly one Project linked to the
repository, and nothing creates it. The frozen PR
[151](https://github.com/ekolvah/agent-process-distribution/pull/151) had a Project step, and
its review (Codex P2, "Make project creation recoverable before copying again") found the
defect of its shape: `gh project copy` and `gh project link` are two remote writes, and when
the link failed the next run saw no linked Project and copied again. Its step also ran after
local writes without a preflight, so an ambiguous remote state was found only mid-run.

Root cause: the Project phase decided from the result of its own previous command instead of
from the remote state a retry can observe. This change adds that phase to `init` as the
installer's only GitHub write ([parent issue 112](https://github.com/ekolvah/agent-process-distribution/issues/112)),
classified from reads before any write, like every local transition.

## What Changes

- `init` gains two transitions after `settings`: `project-copy` and `project-link`, each
  classified `planned`, `unchanged`, or `conflict` from reads of the repository's linked
  Projects and of its owner's Projects, in the same preflight as the local transitions.
- Reuse a linked Project; otherwise reuse the one open, unlinked Project titled
  `<repository name> agent process`; otherwise copy template Project 4 under that title; then
  link it. Several linked Projects, several such candidates, or a same-titled Project that is
  closed or linked elsewhere with none reusable is a `conflict` before any write.
- A retry after a failed or response-lost copy or link reuses the copy and reports a link
  that exists as `unchanged`.
- The plan prints two `manual` rows — Project visibility and the template's built-in
  workflows — that `init` never performs.
- No ruleset, classic protection, required check, secret, workflow landing on the default
  branch, advisory review, or Project Status migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: add Project provisioning, its recovery, and the printed UI actions; rename
  `Local installation writes nothing remote` to `Init writes only the Project remotely` and
  restate it around the two Project writes and a read-only dry-run.

## Impact

- Edited: `skills/agent-process/scripts/init.py` (the Project transitions and `manual`
  rows), `tests/publisher/test_init.py` (a fake GitHub at the runner boundary, the new tests,
  and the rename of `test_no_remote_write`), `skills/agent-process/SKILL.md` (`## Install`:
  the Project write and the `gh` authentication it needs).
- Added and removed: nothing.
- ADR: none. ADR 0027 already decides that `init` copies and links the template Project and
  prints its visibility as a checklist (v2-2a observations); the observations this design
  adds go to `design.md`.
- External systems: GitHub Projects of the consumer's owner — one copy of Project 4 and one
  link, only on `--confirm`. This PR's own runs write nothing remote; tests use a fake
  GitHub at the process boundary.
