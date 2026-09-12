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
- **ROLE-6** (MUST NOT) No discovery role in the core, no budgets or run counters per role,
  no Codex hooks.
