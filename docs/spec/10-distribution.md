# Distribution

**Question this document answers:** how the process is installed into a project, how it is
updated there, what footprint it leaves, and how a project extends it without forking it.

Status: draft

## Requirements

- **DIST-1** (MUST) This repository is the single source. The process is written **once**
  as Agent Skills (`SKILL.md` plus a `scripts/` directory inside the skill) — the format
  both Claude Code and Codex read.
- **DIST-2** (MUST) Three native delivery channels, nothing hand-rolled:

  | Channel | Carries | Install | Update |
  | --- | --- | --- | --- |
  | Claude Code plugin (marketplace = this repository) | skills `plan-issue`, `implement-issue`; agent `architect-reviewer`; hooks resolved from `${CLAUDE_PLUGIN_ROOT}`; rules | `/plugin install` | `/plugin marketplace update` |
  | Codex skills | the same skill directories | `git clone` into `~/.codex/skills`, once per machine | `git pull` |
  | Reusable workflows `@v2` | CI gates | one `uses:` line | Dependabot (`github-actions`) opens the bump PR |

- **DIST-3** (MUST) The consumer footprint is created by one command,
  `/agent-process:init`, and consists of: `.github/workflows/agent-process.yml` (~15
  lines), `.github/ISSUE_TEMPLATE/task.yml`, `AGENTS.md` (pointer to the skills and the
  project's `ci_check` command), the ruleset applied once, a repository variable with the
  Project number. Process files are **not copied** into the consumer.
- **DIST-4** (MUST) Scripts run from where they are delivered: from the skill directory
  when an agent runs them, from a checkout of this repository inside the reusable workflow
  when CI runs them (ADR 0012 already does this).
- **DIST-5** (MUST) A consumer extends the process **beside** it, never inside it: its own
  workflows, its own `ci_check`, its own rules and skills under its own paths. The process
  never edits consumer files and never requires a consumer to edit process files.
- **DIST-6** (MUST) Updating is replacement, never a merge: plugin update, `git pull`, tag
  bump. Any per-consumer value lives in a repository variable or `AGENTS.md`, not in a
  templated process file.
- **DIST-7** (SHOULD) This repository dogfoods its own plugin from a local marketplace.

## Rationale

The open question of the redesign was "plugin, or out of the box with nothing to do".
The answer is **plugin plus `init`**. Copier is the right tool only when a consumer edits
process files locally and therefore needs a three-way merge on update. DIST-5 removes that
need by construction, so the mirror under `template/`, `template_drift.py`,
`adopt_agent_process.py`, `check_consumer_test_collision.py` and `tests/publisher/*` go
with it. ADR 0018 taught the "reserved paths, never consumer configuration" rule; DIST-5 is
the same rule with the copy step removed. ADR 0011's layered split survives in a thinner
form: the Claude adapter is the plugin, the Codex adapter is the same skill directory, the
core is what both share.

Dependabot bumping the workflow tag replaces the drift check for free and is visible as a
PR instead of a failing local script.

## Non-goals

- Copier, cruft, git subtree, or any sync script.
- A pip package: the scripts have no third-party dependencies and ship with the skill.
- Live dependencies (submodule, fetch at session start).

## Open questions

- Codex CLI: confirm on the current version that user-level `~/.codex/skills` sees the
  skill's `scripts/` directory. Settled by one manual run recorded in the v2 ADR.
- Whether `init` should also enable the Codex GitHub review app or only document it.

## Traceability

- ADR 0011 (distribution mechanism) — superseded by this spec once v2 lands.
- ADR 0012 (CI logic referenced, not copied) — kept, DIST-4.
- ADR 0018, 0019 (reserved paths, single root) — lesson kept in DIST-5; mechanism dropped.
