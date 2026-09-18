## Context

See proposal.md — Why. The propose run is the stock `spec-driven` workflow with the
`rules:` of `openspec/config.yaml`; everything the planner must do that the schema does not
say lives in those rules, and everything the architect review must catch lives in the
Architect review entry of `rules.tasks` (`agents/architect-reviewer.md` reads it from
there). The existing `proposal` rules are three sentences; the tests of
`tests/publisher/test_planning_workflow.py` prove a rule by its text.

This change rests on no platform behaviour: it edits configuration, a spec, a test and two
documents.

## Goals / Non-Goals

**Goals:**

- One place says what an observation is and when it is required; the reviewer catches its
  absence before the person approves.
- The rule survives a compaction and a carrier switch: it is in the rule the propose run
  loads, not in a document only Claude reads.

**Non-Goals:**

- A script that decides whether a design rests on a platform behaviour: that is judgement.
- The deterministic checks issue 138 names as examples (see D3).
- Re-observing or re-narrating the two facts of the worked examples: they are observed and
  recorded in ADR 0027 already (the `pull_request_review_thread` bullet, the
  withdrawn-trigger bullet); the entry points at them and adds only what would have shown
  each in minutes.

## Decisions

- **D1 — The rule is a bullet of `rules.proposal`, and it defines the observation.** The
  bullet names the trigger (a design that rests on an event, a permission, a merge rule, a
  token scope, a CLI flag), the step (verify on the platform before the proposal is written)
  and what counts: the reference page — URL and the sentence — for a documented rule, or
  the run id / command and its output for a behaviour of this repository; a listing (an
  enum from `gh api`, a docs index), a name or an inference from another event's behaviour
  does not. Where it goes: **Why** or `design.md`, beside the design decision that rests on
  it. An observation already on record — an ADR entry, an archived change with its run id
  or page — is pointed at, not repeated: `fix-rerun-fallback-head` rested on a fact ADR
  0027 had recorded a day earlier and needed an owner's decision to say so (ADR 0027, the
  "Re-run on a fallback head" bullet); the bullet says it once. *Alternative:* a fifth section of the proposal template — rejected: the template is
  the schema's (`v2-1e-unfork-schema`), and a section would be empty for most changes.
  *Alternative:* a note in `agent-process.md` only — rejected: the apply and the propose
  never load it (`v2-2b-resolve-thread-rule` showed what a rule outside `config.yaml` is
  worth after a compaction).
- **D2 — The finding is a clause of the Architect review entry.** "A simpler design … is a
  finding; a scenario missing … is a finding, and so is a Group 1 … " gains "and a platform
  behaviour a design rests on that is asserted, not observed". The reviewer already reads
  the code the artifacts touch; reading a URL or a run id beside a claim is the same read.
  *Alternative:* a fourth section of `architect-review.md` listing platform facts —
  rejected: three sections are tested (`test_review_finding`) and a section would restate
  the artifacts the review is told to point at.
- **D3 — No new script.** Scripts > instructions holds for a deterministic step; deciding
  that a design rests on a platform behaviour is not one. Of the two checks issue 138 names
  as examples, the caller's event set against the required contexts has nothing left to
  compare (the caller runs on `pull_request` alone since `v2-2b-push-only`), and the
  workflow-file check is a standard tool, `actionlint`, whose adoption is CI code, not a
  planning rule — a unit of its own (owner's decision, 2026-09-18: separate issue). The
  rule names the tool's run as an observation when one exists, so the day it is in CI the
  rule needs no edit.
- **D4 — ADR 0027 carries the worked examples; the specs carry none.** The entry records
  the two facts of PR 137 as the rule's examples (what was inferred, what the platform did,
  what would have shown it in minutes) and D3; the spec requirement stays a contract.

## Risks / Trade-offs

- [The rule is read as "cite a docs page for everything"] → The trigger is a design that
  *rests on* a behaviour; the bullet says so, and the reviewer's finding is for an
  asserted fact a decision depends on, not for a missing footnote.
- [A reference page is wrong or stale, as the events reference was silent on the required
  context per event] → An observation of this repository (run id, command output) ranks
  with a page; the bullet lists both and the examples show a page settling one fact and a
  run settling the other.
- [Rule text drifts from the tests] → The tests assert the words the rule uses
  (`the observation, not the inference`, `reference page`, `run id`, `pointed at, not
  repeated`, `asserted, not observed`), as the file's other tests do for their rules; a
  word the existing Bug bullet already contains (`observation`) guards nothing on its own.
