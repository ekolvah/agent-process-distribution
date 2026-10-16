## Context

Each `### N.` section of `principles.md` opens with a link to the `#operative-principles` anchor
of `always-on.md` and keeps detail and a Rationale (ADR 0044); Quality Gates and Governance
follow. `SKILL.md:23` links each section's anchor, the review contract and the
`architect-reviewer` agent read the file, and three tests read or map it (decision 6).
`test_doc_links.py` fails on any link to a removed file or anchor, such as those of
`SKILL.md:23` and ADR 0011 line 30.

## Goals / Non-Goals

**Goals:** one home per principle; every remaining rule lives where a role reads it.

**Non-Goals:** rewording a rule of `always-on.md` beyond decision 2.

## Decisions

### 1. Where each §I–VII detail goes

| Section | Detail | Destination |
| --- | --- | --- |
| §I | enforced from the issue's `## Test plan` | dropped: `testing.md` item 1 and skill `#tasks` Group 1 state it |
| §I | a non-behavioural regression without a guard test is a recorded decision | dropped: `REVIEW_CONTRACT.md` asks for an explicitly recorded coverage decision |
| §I | a test pinning a known bug needs a tracking issue and is inverted when fixed | dropped: no such test exists here and no role checks it |
| §II | `__main__` wiring, a project boundary document, ready clients never credentials | dropped: the rule's injected `Protocol` implies injected clients; no role checks the rest |
| §III | ERROR names the items, best-effort alert, record only delivered items | dropped: the rule states ERROR, not-ok, non-zero exit and confirmed-only state |
| §IV | per-field gap marker, fatal input examples, later steps, inline reason on a broad catch | dropped: the rule's visible marker covers them |
| §V | instrument = logs, inputs, failure point; trace the call path; boundaries broad to narrow; fixture only with its test | dropped: the rule says instrument first |
| §V | reproduction recorded before design | dropped: skill `#proposal` already states it |
| §V | external system: the failing and a valid record from one captured response | skill `#proposal`: one clause on its platform-behaviour bullet, which the planner applies |
| §V | a fix too large for the PR may ship a documented mitigation with an issue for the cause | `always-on.md` §V (decision 2) |
| §VI | load-time error examples; one validation step | dropped: examples of the rule |
| §VII | no unrequested features; half-its-length; single-caller abstraction | dropped: the rule ("nothing speculative") and the contract's indirection trigger |
| §VII | dead code is its own unit; prefer stdlib | dropped: goal 3 (one PR, one unit) and the rule's "ask before adding a dependency" |
| §VII | plan-stage review, two diff-stage triggers | dropped: the schema's `simpler` class and `REVIEW_CONTRACT.md` hold them |
| all | Rationale | dropped: the goal function is the why |

`openspec/config.yaml` line 20 drops its partial paraphrase of the rules and names
`always-on.md`.

**Alternative:** move every detail into `always-on.md`. Rejected: every session pays for it
(ADR 0044 sits near its 250-token ceiling), and most of it restates the rule.

### 2. The §V mitigation stays a rule

Dropping it would remove an exemption from §V, a rule change this change does not intend. The
last sentence of §V ends "…until the cause is named or a documented mitigation links its
issue." ADR 0044 leaves `always-on.md` near its 250-token ceiling and says growth is cut
elsewhere, so the same edit drops the `**Rationale:**` line of *Scripts over instructions* (the
same treatment decision 1 gives every Rationale): the file shrinks by about 40 characters,
counted in characters of the committed text, not `wc -c` bytes of a CRLF checkout.

### 3. Readers of the principles read `always-on.md` alone

The `Policy source` bullet of `REVIEW_CONTRACT.md` names `trusted/skills/agent-process/always-on.md`
alone, and its `P0`/`P1` bullet drops "with its detail in `principles.md`". Step 2 of
`agents/architect-reviewer.md` reads `always-on.md` alone.

### 4. Skill lines

Line 23 becomes one bullet whose only content is a link with the text `§I–VII` to the
`#operative-principles` anchor of `always-on.md`, so the test's "nothing outside the links"
check still proves the line restates no rule. Line 17 says `always-on.md` binds every role.

**Alternative:** fold the link into line 17's sentence and drop the regex. Rejected: nothing
would then prove the skill's principles line restates no rule.

### 5. `principles.md` is deleted

After decision 1 the file would hold only Quality Gates and Governance:

| Item | Destination |
| --- | --- |
| the `activate_protection` ruleset passes | dropped: GitHub enforces it |
| tests match behaviour; extraction, config and pipeline test kinds | dropped: `always-on.md` §I and §II state the rule; the kinds are examples |
| a rejected coverage decision goes to a ledger | dropped: `REVIEW_CONTRACT.md` asks for an explicitly recorded coverage decision |
| `P2`/`P3` threads answered before merge | dropped: skill `#delivery` states it |
| E2E smoke test for external API contracts | dropped: no role applies it |
| this document supersedes `CLAUDE.md` and `.claude/rules/` | dropped: this repository's `CLAUDE.md` names OpenSpec and the skill as the source of truth; a consumer sets its own precedence |
| delegation of procedure to the skill and specs | dropped: the same `CLAUDE.md` sentence |
| MAJOR/MINOR/PATCH amendment classes | dropped: no role or check applies them; releases are versioned from commit types |
| the PR states the principles it interacts with; a breach is justified in the body | skill `#delivery`: one clause on the report's contents |

The review contract already makes a principle breach a `P0`/`P1` finding, so the reviewer's
check of the PR statement is not carried.

**Alternative:** keep the file for Quality Gates and Governance. Rejected: a document of
rules no role applies, and a second place the package names as binding.

### 6. Tests

`test_skill_carries_principles_core_and_harness_tactics` finds the line by its link
to the `#operative-principles` anchor of `always-on.md`, asserts it is the one link `§I–VII`, keeps the
regex and drops the `principles.md` headings and anchor loop and the `PRINCIPLES` constant.
`test_package_contents_are_closed` drops `principles.md` from the expected set. The coupling
test `test_review_contract_and_principles_stay_coupled_on_narrow_simplicity_triggers` becomes
`test_review_contract_names_the_narrow_simplicity_triggers` and loses its `principles.md`
assertion. `test_review_contract_labels_each_principle` asserts the policy names no
`principles.md`. `test_doc_headers.py` drops the file from its mapped paths, since its
"every scoped directory contributes" test fails on a missing path. A stray link is left to
`test_doc_links.py`. No new script or check.

## Risks / Trade-offs

- A dropped item was guidance someone relied on → the tables name, for each, the text that
  still states it or why nothing applies it; the person reviews them before approval.
- ADRs 0016, 0043 and 0044 describe `principles.md` as it was; ADR 0045 supersedes those parts.
  Only ADR 0011's link target changes, because `test_doc_links.py` requires it to resolve.
- A consumer document linking `principles.md` breaks on the plugin update;
  `test_doc_links.py` covers the plugin's own files, not a consumer's. Rollback: revert the PR.
