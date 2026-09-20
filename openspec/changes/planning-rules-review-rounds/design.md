## Context

See proposal.md — Why. The propose run is the stock `spec-driven` workflow with the
`rules:` of `openspec/config.yaml`: a rule keyed by an artifact id is returned with that
artifact's `instructions`, so it is read at the moment the artifact is written; the
Architect review entry of `rules.tasks` is the reviewer's whole contract
(`agents/architect-reviewer.md`, step 1); the Deliver group entry is the fixer's. The
`tests/publisher/test_planning_workflow.py` tests prove a rule by its text. Today the
config has `proposal` and `tasks` rules only; `test_roles_and_carriers` allows `design`
and `specs` as keys. The archive-before-PR order (`v2-1d-archive-before-pr`) puts the
change under `openspec/changes/archive/<date>-<change>/` on the first head of the PR, and
the existing Deliver rule already sends a spec-changing fix through a change of its own.

This change rests on no platform behaviour: it edits configuration, two specs, a test
file and two documents.

## Goals / Non-Goals

**Goals:**

- Each of the three causes is answered in the rule the run that commits it loads: the
  design rule for the planner, the Architect review entry for the reviewer, the Deliver
  entry for the fixer.
- A catcher is a step of the flow, traced, not a role: the review asks "after the
  described case, which step runs next?" and a "none" is a finding.
- The rules stay sentences: no script, no schema fork, no new artifact.

**Non-Goals:**

- A script that recognises a replaced input, an untraced catcher or a fix by example:
  each is judgement (D3, and the memory rule of this project: a bespoke check only after
  an observed deterministic problem).
- Re-narrating PR 145 and 147: ADR 0027 already carries their entries; the new entry
  points at them (D5).
- Changing the round limit or the `escalate` budget.

## Decisions

- **D1 — The failure-mode list is a `design` rule, and the catcher is a step.** A new
  `rules.design` key with one bullet: the trigger (a design that replaces a
  project-declared input with one the caller supplies, or drops a guard), the three
  lists beside the decision (failure modes of the new input, when one is replaced; what
  the component stops proving; for each lost proof, the delivery-flow step that catches
  it — which script, which run, on which head), and the exclusion (not a role or the platform in general: PR 147 named "the next
  loop" and branch protection, and the flow reached neither).
  *Alternative:* a bullet of `rules.proposal` as `observe-platform-facts` did — rejected:
  the proposal is written before the design is thought through, and the list belongs
  beside the decision in `design.md`; `proposal` would have the planner promise a list a
  later artifact carries. *Alternative:* a section of the design template — rejected: the
  schema is the unmodified `spec-driven` (`v2-1e`), and the section would be empty for
  most changes.
- **D2 — The archive stays before the PR; a design change at review amends the archive
  in the same push.** One sentence of the Deliver entry after the spec-changing-fix
  sentence: a fix that changes a design decision amends the archived `design.md` beside
  that decision (an *Amended at round N* paragraph, as PR 145 and 147 wrote by hand) and
  the scenario → test map of the archived `tasks.md`, in the push that carries the fix;
  a fix that changes a spec still goes through a change of its own (existing rule — the
  two cases are disjoint by what the fix touches). Weighed and rejected, as issue 146
  asks: *archive after the review*. It would leave the head the review reads without the
  delta under `openspec/specs/`, so the review would judge the spec as pending, not as
  implemented (`A behaviour change carries its spec delta`); the archive commit would
  then move the head after the last review, so either the merged head is unreviewed or a
  fourth wait-and-review round is spent on a mechanical commit; and the whole tail of the
  Deliver rule (no tick after the archive, resume from `gh pr view`) rests on the archive
  being the first head. The cost of the kept order is one paragraph and one map line per
  amended decision, in the push the fix makes anyway.
- **D3 — Fix by class is a clause of the Deliver entry, bound to a finding on what a
  script does.** Before the round limit: a finding on what a script does is closed by
  its class — the invariant it violates, the other inputs that violate it from the tool's
  own documentation (its exit-code table, its `--help`), what each added switch takes
  away, a RED test of the class, not the reviewer's example. The trigger is named so the
  clause has no reading on wording and doc threads. The round limit and the fourth
  round's reply are unchanged. The `fixer` row of the roles table in `agent-process.md`
  follows in one clause. *Alternative:* a check that a fix commit
  names an invariant — rejected: a word in a commit message proves nothing; the
  enumeration from the tool's documentation is what closes the class, and that is a read
  of `pytest --help` or an exit-code table, judgement of the fixer that the reviewer then
  reads.
- **D4 — The two findings are clauses of the Architect review entry; the reviewer agent
  is not edited.** After the asserted-platform-fact clause: a design that replaces an
  input without the D1 list, and a named catcher the review cannot trace to a step the
  flow reaches in the described case (after a clean verdict, which step runs next?). The
  subagent reads its contract from the entry (step 1 of `agents/architect-reviewer.md`);
  the trace is a read of the Deliver entry and the scripts it names, which the reviewer
  already reads for the code the artifacts touch. *Alternative:* a fourth section of
  `architect-review.md` ("Catchers") — rejected: three sections are tested
  (`test_review_finding`) and a section would restate the design.
- **D5 — ADR 0027 carries the worked examples; the specs carry none.** One entry after
  the observed-platform-facts bullet: the three causes in one sentence each, pointing at
  the PR 145 and 147 entries the ADR already holds (their rounds are recorded there and
  in the archived `design.md` amendments), and D2's rejected alternative. Deletion
  condition: none, the rules are sentences of `config.yaml`.
- **D6 — The tests assert the words the rules use.** One test per scenario:
  `test_replaced_input_designed` (the `design` rule joined: `replaces a project-declared
  input`, `failure modes`, `stops proving`, `which script, which run, on which head`,
  `not a role`), `test_untraceable_catcher` (the Architect review entry: `cannot trace`
  and `without the list`, after `is a finding`), `test_design_decision_changed_at_review`
  (the Deliver entry: `amends the archived `design.md`` between `never a direct edit of
  `openspec/specs/`` and `three rounds`), `test_finding_closed_by_its_class` (the Deliver
  entry: `closed by its class`, `invariant`, `takes away`, `not the reviewer's example`
  between `amends the archived` and `three rounds`). A word the entries already contain (`finding`, `design`) guards
  nothing on its own.

## Risks / Trade-offs

- [The Deliver entry grows past what a fixer reads carefully] → Two clauses, one per
  obligation; the order of the loop is unchanged, and the tests pin the positions so a
  later edit cannot move them silently.
- [The D1 trigger is read as "every design"] → The bullet names the trigger (a
  project-declared input replaced by a caller-supplied one, a guard dropped); a design
  that adds and replaces nothing carries no list, and the reviewer's finding is for a
  replacement without one.
- [A catcher exists but the review's trace is wrong] → The trace is a question with a
  concrete answer (which step runs next on which head); a wrong answer is one reviewer
  error visible in `architect-review.md`, not a silent approve.
