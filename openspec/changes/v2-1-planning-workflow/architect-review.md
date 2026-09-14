## Verdict

approve — self-review (the `architect-reviewer` subagent that writes this artifact is itself
rewritten by this change, task 3.5); the design answers every scenario with a script, a
configuration rule or a person's action, and the removals outnumber the additions.

## Findings

- §VII · design.md:Decisions "`set_status.py` duplicates the `gh project` helpers" —
  duplication of `set_issue_status.py`/`set_issue_priority.py` until v2-4; accepted because
  the alternative couples the survivor to scripts that are deleted in v2-4 → keep, the
  docstring names the reason and the deletion condition.
- §IV · design.md:Decisions "Review budget: three rounds" — the cap is prose, not a counter;
  an overrun is visible only to the person reading the PR → accepted per the v2 rule (a
  deterministic guard only after an observed overrun); ADR 0027 records the condition.
- §I · schema order — `architect-review` precedes `tasks`, so the scenario → test map is
  checked only on a re-review after `tasks.md` exists → accepted: the `tasks` rule carries
  the map and the PR reviewer reads it against the deltas; the artifact instruction says so.
- §V · design.md:Context "stale lock … cause not yet known" — handled after the root cause
  (task 5.1), not before; `finish_change` exits 2 on a pre-existing lock instead of deleting
  it → correct order, no change.

## Scenario coverage

- roles / Codex plans a change, Reading provenance, Switching agents → `n/a: which carrier
  fills a role is a fact of the installed skills, not a script`
- planning / New task, Ambiguous scope, Review finding, Validator scope, Bug change,
  Unmapped scenario → `n/a: person or planner behaviour; the only automated check on a plan
  is openspec validate --strict`
- implementation / Merge → `n/a: observed on this PR, recorded in ADR 0027`
- every other scenario → the named test in `tasks.md` § Scenario → test map
