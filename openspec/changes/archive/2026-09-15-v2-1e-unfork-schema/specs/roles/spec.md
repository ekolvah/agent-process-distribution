## MODIFIED Requirements

### Requirement: OpenSpec skills are the carriers of the procedure
The planner, implementer and archive procedures SHALL be the OpenSpec skills
(`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`), identical in Claude
Code and Codex, on the unmodified `spec-driven` schema. The process SHALL extend them only
through the `rules` of `openspec/config.yaml`; no forked schema, no
second copy of the steps and no second entry point SHALL exist.

#### Scenario: Procedure changes once
- **WHEN** a planning rule changes
- **THEN** exactly one file changes (`openspec/config.yaml`) and both agents follow it

### Requirement: Roles and carriers
Roles SHALL be carried as follows: planner — `/opsx:propose` in Claude, `$openspec-propose`
in Codex; architect review — the `architect-reviewer` subagent in Claude (independent), a
self-review in Codex, both writing `architect-review.md` into the change directory as the last
step of the propose run; implementer and fixer —
`openspec-apply-change` (`/opsx:apply`, `$openspec-apply-change`) executing `tasks.md`,
whose delivery tasks the `tasks` rule puts into every change; PR review — `claude-code-action` workflow and the Codex GitHub app;
merge — the person.

#### Scenario: Codex plans a change
- **WHEN** the person runs `$openspec-propose` in Codex
- **THEN** the change carries a self-review `architect-review.md` instead of a subagent review
