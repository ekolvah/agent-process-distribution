## Verdict

approve — second review: the three findings of the first are applied in tasks.md and carried
consistently by design.md (D1, Non-Goals, Risks) and proposal.md (What Changes); the design
is the minimum that meets the two scenarios (one bullet, one clause, two text tests, one ADR
entry that points instead of narrating) and D3 holds the owner's decisions of 2026-09-18.

## Findings

none

Checked and consistent: `test_design_on_a_platform_behaviour` (1.1) asserts
`"the observation, not the inference"` and `"pointed at, not repeated"`, phrases absent from
`rules.proposal` today and present in the 2.1 bullet, so the test is RED before 2.1 and green
after it; `test_asserted_platform_fact` is RED today and 3.1 appends its clause after
`"is a finding"` where `test_review_finding` and `test_plan_approved` keep passing; the 2.1
bullet's "already on record" clause closes the case ADR 0027's "Re-run on a fallback head"
bullet settled by hand, and D1 records why; 4.1 points at the `pull_request_review_thread`
bullet (`397c54f`) and the withdrawn-trigger bullet (`a1d0bad`, `35262221116`) of ADR 0027
and adds only what would have shown each in minutes, the exemption, D3 and the deletion
condition, matching Non-Goals; the spec delta stays a contract (the recorded-observation
clause is how the rule is satisfied, not a new requirement, so the delta needs no edit);
D3 (no script; `actionlint` a separate issue) matches the owner's decision and 6.2 carries
the deferral; `openspec instructions proposal --json` (2.1) is the command ADR 0027 line 211
already measures; the doc-guard tests of 4.1 exist under `tests/agent_process/`;
`agents/architect-reviewer.md` reads its contract from the rule and needs no edit. Nit,
not a finding: D4's first clause ("records the two facts … what was inferred, what the
platform did") reads as narration; Non-Goals and 4.1 are the operative text and say "points
at" — the implementer follows 4.1.

## Scenario coverage

- planning / Design on a platform behaviour → the rule text is proved by
  `test_design_on_a_platform_behaviour`; the planner's compliance on a given change →
  n/a: judgement of the propose run, read by the architect review (tasks.md map).
- planning / Asserted platform fact → the finding's presence in the entry is proved by
  `test_asserted_platform_fact`; the reviewer's reading of a given change → n/a: the
  subagent's judgement, exercised on every propose run, not a script (tasks.md map).
