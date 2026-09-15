## Verdict

approve — self-review (the `architect-reviewer` subagent is a plugin agent not installed in
this repository's session, ADR 0027); a reorder of one rule and a shrink of one script, both
from observations on #122–#124, each scenario a test proves or the PR itself shows.

## Findings

- §V · design.md:Decisions — the first draft kept the first-line regex of `_mark_own_task`;
  the observed failure on #124 (task 4.3 unticked, command on the second line) is a root
  cause this change touches → applied: the regex spans the task item; `test_archive_commit`
  ticks a task whose command is on a continuation line.
- §VII · proposal.md:What Changes — renaming `finish_change` is not the minimal diff →
  accepted: a script named "finish" that runs before the PR misleads the next reader (§IV
  beats §VII here); the rename is one `git mv` and the references the tests already pin.
- §IV · design.md:Risks — after the archive OpenSpec no longer tracks the tasks; a re-run
  has no `openspec status` → accepted with the rule sentence naming the archived `tasks.md`;
  a script for it is a second tracker, built only after an observed lost run.
- §II · tasks.md:0.1 — Group 0 of this change cannot ask the priority "before
  `gh issue create`": #125 exists → none needed; the task records that it was asked at
  creation.

## Scenario coverage

- planning / Behaviour change → `n/a: process behaviour; observed on this PR (its first commit is the archive)`
