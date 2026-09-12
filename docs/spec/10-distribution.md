# Distribution

**Question this document answers:** how the process is installed into a project, how it is
updated there, what footprint it leaves, and how a project extends it without forking it.

Status: draft

## Requirements

- **DIST-1** (MUST) This repository is the single source. The process is written **once**
  as Agent Skills (`SKILL.md` plus a `scripts/` directory inside the skill) — the format
  both Claude Code and Codex read.
- **DIST-2** (MUST) Three native delivery channels:

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
  when CI runs them.
- **DIST-5** (MUST) A consumer extends the process **beside** it, never inside it: its own
  workflows, its own `ci_check`, its own rules and skills under its own paths. The process
  never edits consumer files and never requires a consumer to edit process files.
- **DIST-6** (MUST) Updating is replacement, never a merge: plugin update, `git pull`, tag
  bump. Any per-consumer value lives in a repository variable or `AGENTS.md`, not in a
  templated process file.
- **DIST-7** (SHOULD) This repository dogfoods its own plugin from a local marketplace.
- **DIST-8** (MUST NOT) No Copier, cruft, git subtree or sync script; no pip package; no
  live dependency (submodule, fetch at session start).
