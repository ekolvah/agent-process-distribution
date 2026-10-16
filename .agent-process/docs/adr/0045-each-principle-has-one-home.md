---
status: "accepted"
date: 2026-10-16
decision-makers: ekolvah
---

# Each principle has one home

## Context and Problem Statement

ADR 0044 made `always-on.md` the only wording of each rule of §I–VII, but `principles.md` kept
one section per principle with detail and a Rationale, then Quality Gates and Governance. A
principle had two homes: adding or removing one edited both files, the detail could contradict
the rule it explained with nothing to catch it, and every section repeated the same link line.
Only the `architect-reviewer` agent read the file whole.

## Considered Options

* Delete `principles.md`; move each detail to the role that applies it, or drop it
* Move every detail into `always-on.md`: every session pays for it, ADR 0044 left the file near
  its 250-token ceiling, and most of the detail restates the rule
* Keep `principles.md` for Quality Gates and Governance: a document of rules no role applies,
  and a second place the package names as binding

## Decision Outcome

Chosen: **delete `principles.md`**. The destination of each detail, Quality Gate and Governance
item is tabled in decisions 1 and 5 of the archived design of the `principles-one-home` change
(openspec/changes/archive/2026-10-16-principles-one-home/design.md). Two details move:

* The §V external-system evidence (the failing record and a valid one from the same captured
  response) becomes one clause of the skill's Proposal platform-behaviour bullet, which the
  planner applies.
* The PR's statement of the principles it interacts with, with a justified breach, becomes one
  clause of the skill's Delivery report.

The §V mitigation stays a rule: dropping it would remove an exemption from §V. Its last
sentence ends "…until the cause is named or a documented mitigation links its issue." To keep
`always-on.md` under its ceiling, the same edit drops the `**Rationale:**` line of *Scripts over
instructions*, as every Rationale of `principles.md` is dropped: the goal function is the why.

The skill's principles line becomes one bullet whose only content is the link `§I–VII` to the
`#operative-principles` anchor of `always-on.md`, so its test still proves the line restates no
rule. Folding the link into the skill's opening sentence was rejected: nothing would then prove
that. `REVIEW_CONTRACT.md` and the `architect-reviewer` agent read `always-on.md` alone, and
`openspec/config.yaml` names it instead of paraphrasing the rules.

This supersedes what ADRs 0016, 0043 and 0044 say of `principles.md`; the rest of those records
stands. The MAJOR/MINOR/PATCH amendment classes of its Governance are dropped: no role or check
applied them, and releases are versioned from commit types.

### Consequences

* Good, because each principle has one wording, and a change to it edits one file.
* Good, because every session pays a little less: `always-on.md` goes from 3,523 to 3,479
  characters, about 12 tokens fewer at 3.7 characters per token.
* Bad, because a consumer document linking `principles.md` breaks on the plugin update.
* Bad, because the dropped detail and examples no longer guide a reader; the design's tables
  name, for each, the text that still states it or why nothing applied it.

### Confirmation

`tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics`,
`tests/publisher/test_plugin.py::test_package_contents_are_closed`,
`tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle` and
`tests/agent_process/test_doc_links.py`.

### Deletion condition

None while `always-on.md` is the canon of §I–VII.
