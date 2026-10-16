## Context

`skills/agent-process/always-on.md` reaches every session; `principles.md` is the canon and holds
§I–VII in full; the skill's `#principles` holds one linked line per principle. ADR 0043 moved the
goal function from `principles.md` into `always-on.md` and left a link behind; this change does
the same for the operative rule of each principle. The person rejected a second wording of
those rules in `always-on.md`: nothing would catch its drift from `principles.md`.

Three approved changes touch the same text, and this change is applied after all of them;
`consumer-neutral-principles` and `review-checks-every-principle` are merged (`1466811`) with
the text the deltas here were written from, and `delegate-exploration-reads` is not yet:
`consumer-neutral-principles` rewrites §III, §IV and §VI of `principles.md` (D2 below edits its
wording); `delegate-exploration-reads` modifies the roles requirement this change
modifies (the delta here carries its `Explore` sentence); `review-checks-every-principle` adds
the contract requirement and the `Policy source` clause this change extends. A MODIFIED delta
replaces the whole requirement at archive, so task 0.1 compares their merged text with the text
these deltas were written from.

## Goals / Non-Goals

**Goals:** a session that never invokes the skill acts on §I–VII; each rule has one wording;
every `§` in `always-on.md` resolves inside it.

**Non-Goals:** a size gate on `always-on.md`; a generator or a text-comparison test between
files.

## Decisions

### D1 — `## Operative principles` in `always-on.md`, between the goal function and the harness

> ## Operative principles
>
> - **§I** A behavioural change starts with a failing test: RED, code, GREEN. Exempt: renaming or
>   moving a tested symbol, docs-only, a one-line non-behavioural fix.
> - **§II** External services sit behind an injected `typing.Protocol`; tests use in-memory
>   doubles, never mocks of internal logic.
> - **§III** Owed output is never lost silently: a missed delivery logs ERROR, marks the result
>   not-ok, exits non-zero; state records only confirmed delivery.
> - **§IV** No swallowed error or fail-open branch: a degraded result carries a visible marker and
>   a WARNING; a fatal error logs ERROR and exits non-zero.
> - **§V** Reproduce and locate the failure before a change: instrument first, observe the live
>   system when it is the subject. No workaround, shim, retry, broader catch or CI bypass until
>   the cause is named.
> - **§VI** Config is validated at load; a new class of config error gets its check in the same
>   PR.
> - **§VII** The minimum diff for the stated task, nothing speculative: touch only what it
>   requires, match the surrounding style, refactor nothing adjacent. Ask before adding a
>   dependency, package or build step.

This is the only wording of these rules. No link inside: the installed copy cannot resolve a
relative one (ADR 0043), and the rules-file test forbids it.

Alternatives:
- A second wording in `always-on.md`, `principles.md` unchanged: rejected by the person (drift).
- Generate the section from marked sentences of `principles.md`, or test that they match: a new
  script or check where moving the text removes the problem.
- Move only §I, §IV, §V and §VII, the four the issue lists: §II, §III and §VI would keep their
  rule in `principles.md`, so a session would carry part of the core and the rules two homes.
- Import `principles.md` whole: about 3,400 tokens per session (ADR 0043).

### D2 — `principles.md` and the skill link the rules instead of restating them

Each of §I–VII opens with `The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.` and
loses the sentences D1 now states:

- §I: the first paragraph becomes "The implementer workflow enforces it from the issue's
  `## Test plan` section."; "Exceptions, all narrow: (a) … (c) … (typos, comments)." is removed;
  "Anything that changes what the code *does* needs a test that would have caught the prior
  behaviour." becomes "The test would have caught the prior behaviour." The converse, the
  known-gap paragraph and the rationale stay.
- §IV (the `consumer-neutral-principles` wording): the first sentence, the fatal-error paragraph
  and "Forbid swallowed errors and fail-open branches." are removed; the gap-marker paragraph
  becomes "This holds per field: an item that is usable but has an unusable field (an empty URL,
  a missing image, a broken asset) is still emitted, with the marker. Fatal input errors include
  no records and a malformed source." The later-step paragraph, the inline-reason sentence and
  the rationale stay.
- §II: "Every external service is hidden behind a `typing.Protocol` and injected into callers."
  is removed and the next sentence becomes "Production wires real clients in
  `if __name__ == "__main__":` blocks; tests wire doubles through the same constructor
  signature."; "Each external dependency gets its own Protocol boundary, documented with" becomes
  "Each boundary is documented with", and "tests use in-memory doubles, not mocks of internal
  functions." is removed, the preceding clause ending with a full stop. The rest and the
  rationale stay.
- §III (the `consumer-neutral-principles` wording): "The system MUST NOT silently lose output … and
  exit non-zero." becomes "The ERROR names the missed items; the not-ok mark applies where the
  code has a result type."; "State that
  records what was delivered MUST reflect confirmed delivery." is removed. The alert sentence, the
  per-item and record-before-delivery sentences and the rationale stay.
- §VI (the `consumer-neutral-principles` wording): "Declarative config is validated at load time.
  Errors that can be caught at startup MUST NOT surface mid-run:" becomes "Load-time errors
  include"; "When a new class of config error … that step MUST grow a check for it in the same
  PR, rather than defer a known invalid configuration to the run that first uses it." is removed.
  "One load-time validation step is the gate." and the rationale stay.
- §V: "Before changing code … reproduced and located. Instrument before patching:" becomes
  "Instrumenting means inspecting"; "observation of that live system is part of locating the
  failure;" is removed from the next sentence; the sentence "No workarounds, shims, retries,
  broader try/except, or CI-bypass flags are accepted as fixes when the underlying mechanism is
  not understood." is removed. The rest stays.
- §VII: "Every change is the **minimum diff** … nothing speculative." and the **Surgical changes**
  label with its clause "touch only what the task requires and match the surrounding style; do NOT … refactor
  adjacent unbroken code inside an unrelated diff." are removed, and "New dependencies / packages
  / build steps are not added without asking first — prefer stdlib and existing repo packages."
  becomes "Prefer stdlib and existing repo packages."; the dead-code, enforcement and rationale
  text stays, so the two diff-stage trigger markers that
  `test_review_contract_and_principles_stay_coupled_on_narrow_simplicity_triggers` reads stay.
- Governance: "the **goal function** (held in `always-on.md`), the **principles §I–VII**" becomes
  "the **goal function** and the rules of §I–VII (held in `always-on.md`), the **detail of §I–VII**";
  "(the former §Development Workflow)" is removed.
- `## Development Workflow` is deleted: it restates Governance's delegation paragraph.
- `SKILL.md` `#principles`: the seven lines and "On any conflict, the full text of
  `principles.md` decides." become one line, `- [§I](…), [§II](…), … [§VII](…):
  [Operative principles](always-on.md#operative-principles).` with the existing
  `principles.md` anchors; one wording leaves no conflict to decide.

`implementation` spec's "exempt (`principles.md` §I)" stays true: §I links the exemptions.

The review job treats the PR checkout's `CLAUDE.md` and `.claude/rules/` as data
(`reusable-agent-review.yml` prompt, `REVIEW_CONTRACT.md` Policy source), and
`review-checks-every-principle` observed the reviewer not following a link. So the contract's
trusted-policy clause that change adds, "principles §I–VII of
`trusted/skills/agent-process/principles.md` bind the diff", becomes "principles §I–VII, stated
in `trusted/skills/agent-process/always-on.md` with their detail in
`trusted/skills/agent-process/principles.md`, bind the diff".

The same change's `P0`/`P1` clause gives each of §I–VI a breach signal that nearly restates its
rule (§IV "a swallowed error or fail-open branch"). The signals become tags that name the breach
and leave the rule to its one wording; the clause from "a failing or missing behavioural test
(§I)" to "the full text settles a borderline case" becomes:

> a failing test, a misleading result, a leaked secret, a convention violation — including a
> principle breach tagged §I untested behaviour change, §II mocked own logic or client outside
> a Protocol, §III silent data loss, §IV swallowed error or fail-open branch, §V workaround
> without a named cause, §VI config checked after load; the tag labels the finding and names
> the section, and the rule in trusted `always-on.md`, with its detail in `principles.md`,
> settles a borderline case

The tags stay in the contract because the reviewer follows no link (that change's proposal); a
tag costs fewer tokens than the signal it replaces.

### D3 — References and repository duplicates

- Goal 1 becomes "**Minimize future bug-fixing and support.** Root cause before fix (§V),
  visibility over silence (§IV), test-first (§I)."; its current sentences restate D1.
- Goal 2's "Do not produce artefacts, scripts, or infrastructure a task does not need (§VII);"
  becomes "Simplicity first (§VII);", and *Scripts over instructions*' "(a new dependency is
  still asked first, §VII)" becomes "(§VII)": both restate D1 §VII.
- This repository's `CLAUDE.md` loses what `always-on.md`, which it imports, states: the bullet
  "Follow Principle V: instrument before patching, and observe the live external system …" is
  deleted, and "Keep a PR to one logical unit." (goal 3) is cut from the next bullet.

### D4 — Cost

Characters at about 3.7 per token, the ratio `goal-function-every-session` used (2,200
characters, roughly 600 tokens): D1 adds about 1,170 characters, D3 removes about 240 from
`always-on.md`, net about 930, roughly 250 tokens per installed session — the issue's ceiling,
reached by moving §II, §III and §VI as well (the person's decision on this plan). `principles.md` and
`SKILL.md` shrink. The implementer records both `wc -c` figures of `always-on.md` in the PR
report and in the ADR.

### D5 — Tests

- `test_rules_carry_the_always_on_file` adds `## Operative principles` to its heading check and
  asserts that `set(re.findall(r"§([IVX]+)", source))` and the same set within that section are
  both §I–VII, each section bullet opening with its `**§N**`.
- `test_skill_carries_principles_core_and_harness_tactics` asserts that the skill line holding
  `](always-on.md#operative-principles)` holds the anchors of §I–VII and, with its links
  removed, nothing but punctuation; that the core holds no other principle line; and that each of the
  seven sections of `principles.md` links the `#operative-principles` anchor of `always-on.md`.
- `test_review_contract_labels_each_principle` also asserts that the `Policy source` bullet
  names `trusted/skills/agent-process/always-on.md`.

## Risks / Trade-offs

- `principles.md` §I–VII no longer read standalone; a reader follows one link, as for the goal
  function.
- Every installed session pays about 250 tokens for the section, the issue's ceiling; a later
  rule edit that grows it passes the ceiling unless it is cut elsewhere.
- An edit of one of these rules is made in `always-on.md` and reaches consumers at their next
  Install.

## Migration Plan

Consumers receive the text at their next Install (the release-drift exit forces it). Rollback is
reverting the PR; no state is written.
