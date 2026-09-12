# Planning

**Question this document answers:** how the process gets high-quality plans out of agents,
and what the person approves before implementation starts.

Status: draft

## Requirements

- **PLAN-1** (MUST) Substantive work starts from a GitHub issue created through an issue
  form that carries the plan structure: Context, Acceptance criteria, Test plan,
  Implementation outline, Docs to update, Out of scope, Architect review, Agent handoff.
  The agent cannot forget a section because the section is already there.
- **PLAN-2** (MUST) The `plan-issue` skill reads the code and the prior art before writing
  a plan, and asks the person instead of guessing when a decision is theirs.
- **PLAN-3** (MUST) A non-trivial plan gets an architect review before implementation: the
  `architect-reviewer` subagent in Claude (independent), a self-review section in Codex.
  Criteria are `principles.md` §I–VII; findings are recorded in `## Architect review`.
- **PLAN-4** (MUST) The person approves the plan; that approval is the gate. The
  validator checks only that the headings exist and `## Agent handoff` is filled (~100
  lines), never which sections a label requires.
- **PLAN-5** (MUST) The issue references the system-spec requirement IDs it implements;
  a PR that changes behaviour updates the spec in the same PR.
- **PLAN-6** (SHOULD) Bugs ship a reproducing test before the fix (`40-implementation.md`,
  IMPL-1); the core does not prescribe how evidence is captured.

## Rationale

The person reviews **decisions**, not form; the four layers above make the decisions good
enough to review cheaply. The architect review is kept deliberately: it is the cheapest
second look, it happens before any code, and the person relies on it for quality.

v1's `validate_issue_sections.py` (727 lines) derived the required set from the type label
via `change-classes.yaml` and parsed `Evidence` and `Prior art` field by field. With a
human approval gate that machinery answers a question nobody asks; the form answers the
structural half at creation time.

## Non-goals

- Per-label section sets.
- A `discovery` role or `capture_external_fixture.py` in the core (ADR 0009 moves to the
  project that needed it).
- Agents changing issue labels.

## Open questions

- GitHub Spec Kit as the carrier of the change spec (`/speckit.specify → plan → tasks`,
  files under `specs/NNN/`): it would replace "issue as plan" and rewrite `plan-issue`.
  Deferred until v2 is stable; settled by running two comparable issues each way and
  comparing tokens per merged PR.
- Whether `## Prior art` stays a required heading or becomes a line in Context.

## Traceability

- Issue contract in `agent-process.md` — replaced by PLAN-1/PLAN-4 once v2 lands.
- ADR 0009 — discovery moved out of the core.
- Spec-driven development adopted (#105).
