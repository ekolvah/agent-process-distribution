# Roles and agents

**Question this document answers:** which roles the process has, which carrier fills each
one in Claude Code and in Codex, and how two agents share one procedure without duplication.

Status: draft

## Requirements

- **ROLE-1** (MUST) The skill is the only carrier of a procedure. An adapter is an entry
  point (`/plan` in Claude, `$plan-issue` in Codex) plus provider-specific capability, never
  a second copy of the steps.
- **ROLE-2** (MUST) Roles and carriers:

  | Role | Claude Code | Codex |
  | --- | --- | --- |
  | planner | skill `plan-issue` | the same skill |
  | architect review | subagent `architect-reviewer` (independent) | self-review section of the skill |
  | implementer + fixer | skill `implement-issue` | the same skill |
  | PR review | `claude-code-action` workflow | Codex GitHub app |
  | merge | person | person |

- **ROLE-3** (MUST) Provenance ("who planned, who implemented") is one line in the
  issue's `## Agent handoff` section, not a catalogue file.
- **ROLE-4** (MUST) Any route selection is the person's: which agent runs a role is
  decided by which chat the person opens. No file records a "default adapter".
- **ROLE-5** (SHOULD) Implementer and fixer are one skill: after the PR is open the same
  run waits for checks and reviews and applies fixes (`40-implementation.md`, IMPL-5).

## Rationale

v1 kept `roles.yaml` with `adapter_routes`, `carrier_selection`, `adapter_files`,
`adapter_independence` and `max_runs` per role, read by an orchestrator and by the issue
validator. The table above carries the same information in ten lines of `AGENTS.md`, and
the person choosing a chat is the routing. The independence of the architect reviewer
(Claude subagent = independent, Codex = self) stays visible in the issue text — the
validator no longer resolves it from a map.

Codex hooks are dropped (`.codex/hooks.json`, `codex_hooks.py`,
`check_codex_project_trust.py`). What is lost: in Codex, a lint error surfaces at
`ci_check` instead of immediately after the edit — one extra cycle at the end of a task;
the command deny-list was defense in depth behind branch protection, which stays
authoritative. What is gained: no trust preflight, one installation step fewer, no
dependency on a feature Codex still flags experimental.

## Non-goals

- A discovery role in the core; a project that needs fixture capture keeps it locally.
- Budgets or run counters per role.

## Open questions

- Restore Codex hooks when Codex ships them as a stable feature; settled by re-running the
  post-edit lint through both agents and comparing review rounds (`70-telemetry.md`).

## Traceability

- ADR 0009 (discovery role) — moved out of the core.
- ADR 0015 (Codex primary, Claude fallback) — superseded; see `50-review-and-merge.md`.
- `.agents/orchestration/roles.yaml` — replaced by ROLE-2.
