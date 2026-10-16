# roles Specification

## Purpose
Which roles the process has and which Claude Code entry point carries each one.

## Requirements

### Requirement: OpenSpec skills are the carriers of the procedure
The planner, implementer, and archive entry points SHALL remain the OpenSpec skills
(`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`) in Claude Code, on
the unmodified `spec-driven` schema. The portable proposal, specification, design, task,
architect-review, and delivery procedure SHALL live once in the shared `agent-process` skill.
`openspec/config.yaml` SHALL retain project context and point its artifact rules to that
skill rather than copy the procedure body. No forked schema, second procedure copy, or
second role-specific entry point SHALL exist.

#### Scenario: Procedure changes once
- **WHEN** a portable planning or delivery rule changes
- **THEN** one shared `agent-process` skill source changes and Claude Code follows it through its OpenSpec entry points without merging copied rule bodies

### Requirement: Provenance is one line in the tracking issue
"Who planned, who implemented" SHALL be one line in the tracking issue, not a catalogue file.

#### Scenario: Reading provenance
- **WHEN** a person opens the issue
- **THEN** the planner and implementer carriers are visible without opening any other file

### Requirement: Claude Code carries every role
Claude Code SHALL be the only carrier of every agent role, in this repository and in every
consumer: planner — `/opsx:propose`; architect review — the `architect-reviewer` subagent,
writing `architect-review.json` into the change directory as the last step of the propose
run, valid against `skills/agent-process/architect-review.schema.json`; implementer and
fixer — `openspec-apply-change` (`/opsx:apply`) executing `tasks.md`, whose delivery tasks
the `tasks` rule puts into every change; PR review — the `claude-code-action` workflow;
merge — the person. Agent instructions SHALL live only in Claude Code's channels:
`CLAUDE.md`, `.claude/rules/`, and the plugin's `agent-process` skill. This repository SHALL
keep no `AGENTS.md`, and the review contract's policy source SHALL name `CLAUDE.md` and
`.claude/rules/`.

#### Scenario: Another carrier named
- **WHEN** `start_change` is given a planner or implementer other than `Claude`, or an architect review names a reviewer other than `architect-reviewer`
- **THEN** the argument or the review is rejected before any branch exists

#### Scenario: Instructions live in Claude Code channels
- **WHEN** the repository root, the review contract and the review job's prompt are read
- **THEN** no `AGENTS.md` exists, `CLAUDE.md` links the review contract, and the contract and the prompt each name `CLAUDE.md` and `.claude/rules/` and neither names `AGENTS.md`

### Requirement: The skill carries the principles core and harness tactics
The `agent-process` skill SHALL state the three goals and name each principle §I–VII with a link
to `principles.md` for their detail, on one line that links the `#operative-principles` anchor of
`always-on.md` and restates no rule. Each section in `principles.md` SHALL link that anchor for its rule. The skill SHALL link the
package's `always-on.md`, which holds the full goal function, the operative principles and the
Claude-harness token tactics.
Its tactic for a compaction
between the RED commit and GREEN SHALL recover state from the branch, the RED commit and one
`gh issue view`, and SHALL NOT ask the person to compact. Its delegation tactic SHALL send a
question needing two or more lookups of material the session will not edit to the `Explore`
subagent for a `path:line` conclusion.

#### Scenario: A consumer reads principles and tactics from the skill
- **WHEN** a consumer session invokes the `agent-process` skill
- **THEN** the skill body names the three goals, each of §I–VII with a link to `principles.md` on one line that holds only those links and a link to the `#operative-principles` anchor of `always-on.md`; each of the seven sections of `principles.md` links the same anchor; and the body links the `#claude-harness` anchor of `always-on.md`, whose harness tactics carry the `gh issue view` recovery, no `/compact` request, and the `Explore` delegation with its two-or-more trigger and `path:line` conclusion

### Requirement: Plugin agents inherit the session model
Every plugin agent SHALL declare `model: inherit` and no `effort` in its frontmatter.

#### Scenario: Agent frontmatter read
- **WHEN** the frontmatter of a plugin agent is read
- **THEN** its `model` is `inherit` and it has no `effort` key
