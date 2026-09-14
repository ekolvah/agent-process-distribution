## Context

v1 is a Python control plane (`agent_orchestrator.py`, `delivery_state.py`, `roles.yaml`,
review state machine, Copier mirror) installed by copying files into consumers, with the
procedure duplicated per agent adapter. Constraints: GitHub Actions + Projects only, mixed
stacks, two paid subscriptions, no other services. This design is the umbrella for v2-1 … v2-6.

## Goals / Non-Goals

**Goals:** one scenario; lowest future support; lowest tokens; predictable and under user
control; identical procedure in both agents; standards instead of bespoke wherever one exists.

**Non-Goals:** multi-repo orchestration; agent-driven merge; per-project code generation; a
measurement module shipped to consumers.

## Decisions

- **Specs and planning = OpenSpec.** Living spec in `openspec/specs/`, changes as deltas
  with scenarios, `/opsx:propose` as the planner, `/opsx:apply` inside the implementer,
  `openspec archive` as the last commit of the implementing PR; project rules via `openspec/config.yaml`, architect review as
  an artifact of a forked schema. Chosen over GitHub Spec Kit by a Kepner-Tregoe trade study
  (Spec Kit has no living system spec showing implemented vs pending) and over a bespoke
  `plan-issue` skill (same loop, iterated by one team instead of many).
- **Delivery = plugin + skills + reusable workflows, no file copy.** Alternatives: Copier
  (v1: drift tests, three-way merges), pip package (Python-only), submodule (live dependency).
- **Procedure written once as Agent Skills**; adapters are entry points only.
- **The person is the only gate.** Plan approval and merge are human; validators check
  structure only. v1 `delivery_state` protected nothing the person did not already decide.
- **Merge protection is a GitHub ruleset** installed once from JSON in this repository.
- **Review is advisory; coverage is a check.** Reviewers comment; conversation resolution
  makes comments blocking by the person's choice. Scenario coverage is deterministic, so it is
  a required check, not a review comment.
- **State lives in the GitHub Project.** `set_status` resolves IDs by name at run time.
- **Telemetry is owner-side.** OTLP from both agents through one collector with
  project/task/attempt labels; comparisons per merged PR.

## Risks / Trade-offs

- Codex has no hooks → `wait_for_pr` is the only end-of-run guard there. Mitigation: it is
  the skill's last step; an early exit is visible on the PR.
- Codex architect review is a self-review artifact, weaker than an independent subagent.
  Mitigation: the person approves the plan either way.
- OpenSpec needs Node in consumers (`npx`); GitHub runners have it.
- OpenSpec-generated skills (~17k tokens each) load per invocation, about once per change.

## Migration Plan

Each change v2-N is one PR against `main`, archived by its last commit (tracking issue #107); v1
keeps working until v2-5 deletes it. Rollback of any step is a revert of its PR.

## Open Questions

- Coverage marker format in tests (scenario title in test name vs docstring) — v2-3.
- Whether `claude-code-action` review threads count for `required_conversation_resolution`
  when the app has no write permission — v2-4, on a real PR.
