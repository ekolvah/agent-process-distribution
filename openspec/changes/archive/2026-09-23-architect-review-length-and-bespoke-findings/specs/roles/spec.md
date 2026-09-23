## MODIFIED Requirements

### Requirement: Roles and carriers
Roles SHALL be carried as follows: planner — `/opsx:propose` in Claude, `$openspec-propose`
in Codex; architect review — the `architect-reviewer` subagent in Claude (independent), a
self-review in Codex, both writing `architect-review.json` into the change directory as the last
step of the propose run, valid against `skills/agent-process/architect-review.schema.json`; implementer and fixer —
`openspec-apply-change` (`/opsx:apply`, `$openspec-apply-change`) executing `tasks.md`,
whose delivery tasks the `tasks` rule puts into every change; PR review — `claude-code-action` workflow and the Codex GitHub app;
merge — the person.

#### Scenario: Codex plans a change
- **WHEN** the person runs `$openspec-propose` in Codex
- **THEN** the change carries `architect-review.json` whose `reviewer` is `self-review` instead of `architect-reviewer`, valid against the review schema
