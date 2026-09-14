## Verdict

approve — self-review (the `architect-reviewer` subagent is a plugin agent not installed
in this repository's session); the change is configuration plus one agent prompt, and every
scenario is either provable by the schema/config test or is a person's action.

## Findings

- §VII · the `tasks` rule is 40 lines of prose — the largest surface of the change and where
  9 of 15 review threads of PR 121 landed. Accepted: a script that generates `tasks.md` would
  be a second entry point the OpenSpec prompts do not know; the rule is dry-run against every
  spec scenario in this change's own `tasks.md` (task 2.1).
- §IV · `Closes #<N>` removed from the rule — an explicit `Closes` masks whether
  `gh issue develop -c` links the PR and closes the issue; the `Merge` scenario of part 1 is
  observed only without it. Applied in `config.yaml`.
- §I · schema order — with `architect-review` before `tasks` the scenario → test map was
  never reviewed (PR 123 round 1, P1) → applied: `tasks` precedes `architect-review`,
  `apply` requires both; `test_review_finding`.
- §IV · a docs-only or `skip_specs` change had no honest way through Group 1 (PR 123
  round 1) → applied: `no RED: <reason>` task; its absence is a review finding.
- §II · `@latest` at runtime, `@1.13.0` in the tests (PR 123 round 1) → applied: one pin,
  `test_pinned_openspec`; `finish_change.py` follows in part 1.
- §II · `agents/architect-reviewer.md` reads its contract from `openspec instructions`
  rather than restating it — one source; kept.

## Scenario coverage

- roles / Procedure changes once, implementation / Tasks of a new change →
  `test_roles_and_carriers` (the rule's presence; its content is read by the reviewer)
- planning / Review finding → `test_review_finding`
- state / Tracking issue created, Priority field drift → tests of part 1; Priority asked
  once → `n/a: rule text, person's answer`
- roles / Codex plans a change, Reading provenance, Switching agents → `n/a: which carrier
  fills a role is a fact of the installed skills, not a script`
- planning / New task, Ambiguous scope, Validator scope, Bug change,
  Unmapped scenario → `n/a: person or planner behaviour; the only automated check on a plan
  is openspec validate --strict`
- planning / Behaviour change → `n/a: finish_change (part 1); observed on this PR`
