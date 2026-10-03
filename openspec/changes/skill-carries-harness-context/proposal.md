## Why

A consumer's planner and implementer never see principles §I–VII. Only the
`architect-reviewer` subagent reads `principles.md` in full, and the CI review applies
two narrow §VII triggers. The Claude-harness token tactics are not in the plugin either, so
`ekolvah/kinozal_scraper` keeps them in its own always-load `.claude/rules/mindset.md`
(#315). In this repository its local rules, `AGENTS.md` and the `config.yaml` context hide
this gap.

A plugin cannot ship an always-load file. The plugin manifest reference
(https://code.claude.com/docs/en/plugins-reference, "Standard layout") says: "A `CLAUDE.md`
at the plugin root isn't loaded as context, and `claude plugin validate` warns when it finds
one. To include instructions that load into Claude's context, put them in a skill." The skill
body is therefore the one channel the plugin owns that reaches a consumer's working agent.
Task 3.3 observes this live.

The process is used with Claude Code only, both here and in a consumer, but no requirement
says so. As a result this repository keeps its conventions in `AGENTS.md`. The memory docs
(https://code.claude.com/docs/en/memory, "AGENTS.md") say: "By default, Claude reads
`AGENTS.md` only when you have no `CLAUDE.md` in your working directory or above it." They also
say: "In some sessions Claude can't read `AGENTS.md`." The consumer has no `AGENTS.md` at all:
it has `CLAUDE.md` and `.claude/rules/` (observed with
`gh api repos/ekolvah/kinozal_scraper/contents/AGENTS.md` → 404).

## What Changes

- `skills/agent-process/SKILL.md` gains two sections:
  - a `## Principles` core: the goal function and one line per §I–VII, with a link to
    `principles.md` for the full text;
  - a `## Claude harness` section with the portable token tactics that #315 lists.
- The RED→GREEN compaction tactic keeps this repository's form: after a compaction, recover
  state from the branch, the RED commit and one `gh issue view`. The consumer's "ask the
  person for `/compact` after RED" is not adopted.
- `.claude/rules/mindset.md` is deleted. Its two remaining pointers, to the two new sections
  and to `testing.md`, move into this repository's `CLAUDE.md`.
- Claude Code is the only agent here and in every consumer. Agent instructions live in
  `CLAUDE.md`, `.claude/rules/` and the plugin skill.
  - This repository's `AGENTS.md` becomes `CLAUDE.md`.
  - The review contract's policy source names `CLAUDE.md` and `.claude/rules/`.
  - The review prompt and tests stop naming `AGENTS.md`.
- Consumer follow-up, outside this repository: after the release, `kinozal_scraper` deletes
  its `.claude/rules/mindset.md`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `roles`:
  - "Claude Code carries every role" now covers every consumer and names the instruction
    channels, with no `AGENTS.md`;
  - a new requirement makes the skill carry the principles core and the harness tactics.

## Impact

- Edited:
  - `skills/agent-process/SKILL.md`
  - `.agent-process/REVIEW_CONTRACT.md`
  - `.github/workflows/reusable-agent-review.yml` (prompt text only)
  - `tests/publisher/test_plugin.py`
  - `tests/publisher/test_reusable_workflows.py`
  - `tests/publisher/test_planning_workflow.py` (comment and absent-token list)
  - `tests/publisher/openspec_cli.py` (message)
  - `tests/publisher/test_pr_delivery.py` (docstring)
  - `openspec/specs/roles/spec.md` (through the archive)
- Moved: `AGENTS.md` → `CLAUDE.md`, with the same content plus the two pointers from
  `mindset.md`.
- Removed: `.claude/rules/mindset.md`. Historical ADRs and archived changes stay untouched.
- Consumers: on the next release the skill reaches them. Their review contract reads
  `CLAUDE.md`, which they already keep.
