## Why

Since `principles-core-every-session`, `always-on.md` holds the only wording of each rule of
§I–VII, yet `principles.md` keeps one section per principle with detail and rationale. A
principle has two homes: adding or removing one edits both files, the detail can contradict the
rule it explains with nothing to catch it, and every section repeats the same link line. What
else the file holds, Quality Gates and Governance, is either stated elsewhere or no role applies
it.

## What Changes

- `skills/agent-process/principles.md` is deleted (design decision 5).
- Each §I–VII detail moves to the role that applies it or is dropped (decision 1): two §V
  clauses fold into existing sentences of `always-on.md` (which drops a Rationale line to stay
  under its token ceiling) and of the skill's Proposal section (decisions 1 and 2); the §VII
  diff triggers stay only in `REVIEW_CONTRACT.md`; the rest and every Rationale are dropped.
- Quality Gates and Governance (decision 5): the PR's principle statement becomes one clause of
  the skill's Delivery report; the rest is already stated elsewhere or dropped, including the
  MAJOR/MINOR/PATCH amendment classes.
- The skill's principles line becomes one link, `§I–VII`, to `always-on.md` (decision 4).
- `REVIEW_CONTRACT.md` and the `architect-reviewer` agent read `always-on.md` alone (decision 3).
- `openspec/config.yaml`, the specs and ADR 0011's link point at `always-on.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `roles`: the skill links §I–VII through `always-on.md`.
- `review-and-merge`: the simplicity triggers are no longer coupled to the principles file;
  the contract's policy source is `always-on.md` alone.
- `planning`: the architect review reviews against §I–VII of `always-on.md`.
- `implementation`: the RED-first exemptions cite `always-on.md` §I.
- `maintenance`: the question-line guard covers `.claude/rules/` alone.

## Impact

- Deleted: `skills/agent-process/principles.md`.
- Edited: `skills/agent-process/always-on.md`, `skills/agent-process/SKILL.md`,
  `.agent-process/REVIEW_CONTRACT.md`, `agents/architect-reviewer.md`, `openspec/config.yaml`,
  `.agent-process/docs/adr/0011-agentic-process-distribution-mechanism.md` (one link target),
  `tests/publisher/test_plugin.py`, `tests/publisher/test_reusable_workflows.py`,
  `tests/agent_process/test_doc_headers.py`.
- Added: `.agent-process/docs/adr/0045-each-principle-has-one-home.md`.
- Specs (through this change's deltas): `roles`, `review-and-merge`, `planning`,
  `implementation`, `maintenance`.
- Consumers: the plugin update removes the file; a consumer document linking it breaks.
