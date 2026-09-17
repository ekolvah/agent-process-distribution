## Verdict

approve — self-review by the planning session (the `architect-reviewer` plugin agent is not
loaded in this repository's own session), second pass after the person's three decisions of
2026-09-17 (one reviewer per head; Codex requested by the rule, not automatic; `P0`/`P1`
block through the required check). The first
PR deletes more than it adds (one script, eleven workflow tests, the parser half of
`request_codex_review.py`, the replies of the gate), every scenario maps to a named test,
and the gate that stays is the one that exists today minus its classification.

## Findings

- §IV · design.md:D4 — `--wait` matches the Codex clean comment by the `Reviewed commit:`
  prefix; that is a read of *whether* a review exists, not of what it says, which is the
  line the `review-and-merge` requirement draws. Kept; the module docstring must say so
  and `test_wait_reads_nothing_but_presence` (task 1.3) keeps the next reader from
  growing it back into a parser.
- §VII · design.md:D6 — two PRs for one change. Justified by Context: the first PR's
  caller still runs the v1 chain on `main`, so adding review events there would run the
  parser and the Claude fallback on every thread event of that PR — the cost the person
  refused. The second PR is one trigger block and one deleted clause, and it is the only
  place the "check run listed for the head" question can be observed. Acceptable.
- §V · design.md:D1 — `continue-on-error` on the wait step hides nothing: the step's
  outcome is the fallback condition and stays visible in the run; exit 3 vs 2 keeps a
  crash of the script distinguishable from an absent review. No change.
- §I · tasks.md:1.6 — the RED set contains rewritten tests of files that also lose tests;
  `check_red` needs only the named node ids, so the deleted tests do not affect the proof.
  No change.

## Scenario coverage

- review-and-merge / Advisory thread, Required check and threads → one new test each plus
  an existing one (`test_open_p2_is_explicitly_nonblocking`,
  `test_the_required_check_never_resolves_a_thread`); the existing ones are unchanged.
- implementation / Tasks of a new change, Propose run stopped before its tail → existing
  tests, unchanged scenarios.
- implementation / Blocking thread addressed → `test_tasks_of_a_new_change` in two steps
  (task 1.4 wording, task 7.1 the re-run clause), matching the two PRs.
