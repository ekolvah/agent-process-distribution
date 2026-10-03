## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: The skill carries the principles core and harness tactics
The `agent-process` skill SHALL state the goal function and one line per principle §I–VII,
linking `principles.md` for the full text. It SHALL carry the Claude-harness token tactics.
Its tactic for a compaction
between the RED commit and GREEN SHALL recover state from the branch, the RED commit and one
`gh issue view`, and SHALL NOT ask the person to compact.

#### Scenario: A consumer reads principles and tactics from the skill
- **WHEN** a consumer session invokes the `agent-process` skill
- **THEN** the skill body names the goal function, each of §I–VII with a link to `principles.md`, and the harness tactics with the `gh issue view` recovery and no `/compact` request
