## Context

See proposal.md — Why.

## Goals / Non-Goals

**Goals:** every sentence of §III, §IV and §VI is a rule a consumer without notifications,
selectors or this repository's tests can apply; each principle keeps its intent.

**Non-Goals:** sentences of the same kind outside issue 431's scope — §I
`TestConfigValidationKnownGaps`, §II "the pipeline and extraction helpers" and its Python
idiom, the Quality Gates' "extraction logic" and "pipeline orchestration"; a new home in
`CLAUDE.md` for this repository's ruff gate.

## Decisions

**D1 — Neutral rule; product cases survive as list items.** Each principle states the rule in
neutral terms; a product case stays only where it is one item of a list the rule already
carries (an empty URL in §IV, non-positive limits in §VI); §III has no such list and gets
none. Alternative: a "for example" sentence or a new list per principle — longer, and the
rule's own terms already name what it covers.

**D2 — This repository's ruff gate leaves the canon, with no new prose.** The gate is
`.agent-process/pyproject.toml` (`BLE`, `TRY400` selected) and
`tests/agent_process/test_ruff_silence_rules.py`, whose docstring names its job; the edit-time
lint reports a finding at the edit, and the guard test fails on any disabling. "Not here"
already defers how a gate is configured to the project's own docs. Alternatives: name the gate
as this repository's in §IV — keeps a repository fact in a file every consumer reads; a line in
`CLAUDE.md` — paid on every session of this repository for a gate that already announces itself.

**D3 — Governance MINOR.** Against the planned wording below:

| Section | Before | Intent |
| --- | --- | --- |
| §III | A pipeline's notification and dedupe state | Same failure signals, missed-item logs, alert condition ("delivery transport" becomes "delivery channel") and state clauses for any owed output and any delivery record: widened |
| §IV | Extraction, notification, summarization; ruff gate named | Same gap marker, fatal-error and no-collapse rules for any input and later step; delivery points to §III; the ruff sentence is a repository fact (D2): widened |
| §VI | Selectors, macro placeholders, "a central validator function", "a scheduled production run" | Same load-time gate and same-PR rule for any declarative config: widened |

No rule is removed, redefined or weakened, so no MAJOR approval is needed. The one deletion
called out is the §IV ruff sentence.

Planned wording, §III:

> The system MUST NOT silently lose output a user relies on. When a run cannot deliver an item
> it owes a user, it MUST surface an explicit operational failure: log ERROR naming the missed
> items, mark the result not-ok where the code has such a type, and exit non-zero. A
> best-effort technical alert should be sent when the failure is not the delivery channel
> itself.
>
> State that records what was delivered MUST reflect confirmed delivery. A run that can tell
> which items were delivered records only those. Recording before delivery is allowed only when
> a delivery failure is still an explicit operational failure.
>
> **Rationale:** users must be able to distinguish "there was nothing to deliver" from "the
> system failed to deliver" — a silent green run that does neither destroys trust.

§IV, after the unchanged first sentence:

> If an item is usable but one of its fields is not (an empty URL, a missing image, a broken
> asset), the item is still emitted with a clear gap marker AND a WARNING log line.
>
> Conversely, fatal input errors (no records, a malformed source) MUST
> log ERROR and exit non-zero, so CI or the operator sees the failure.
>
> The same holds for each later step: a failed transformation or technical alert MUST NOT be
> collapsed into "nothing to report"; a failed delivery is §III.
>
> Forbid swallowed errors and fail-open branches. An intentional broad catch that keeps the
> failure visible carries its reason inline.

§VI:

> Declarative config is validated at load time. Errors that can be caught at startup MUST NOT
> surface mid-run: missing required fields, out-of-range values such as non-positive limits,
> references that do not resolve, mismatched schemas.
>
> One load-time validation step is the gate. When a new class of config error becomes
> possible, that step MUST grow a check for it in the same PR, rather than defer a known
> invalid configuration to the run that first uses it.
>
> **Rationale:** a config-validation gap otherwise surfaces at first use, far from the edit
> that introduced it.

§IV's rationale stays as it is.

## Risks / Trade-offs

- [The neutral wording reads vaguer to a pipeline project] → the rule's terms (item, delivery,
  run) are the pipeline's own; only the product nouns leave.

## Migration Plan

Text only. Rollback is a revert of the PR.
