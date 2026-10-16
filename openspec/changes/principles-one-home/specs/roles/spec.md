## MODIFIED Requirements

### Requirement: The skill carries the principles core and harness tactics
The `agent-process` skill SHALL state the three goals and name §I–VII on one line that holds only
a link to the `#operative-principles` anchor of `always-on.md` and restates no rule. The skill SHALL link the package's `always-on.md`, which holds the full goal function, the operative principles and the
Claude-harness token tactics.
Its tactic for a compaction
between the RED commit and GREEN SHALL recover state from the branch, the RED commit and one
`gh issue view`, and SHALL NOT ask the person to compact. Its delegation tactic SHALL send a
question needing two or more lookups of material the session will not edit to the `Explore`
subagent for a `path:line` conclusion.

#### Scenario: A consumer reads principles and tactics from the skill
- **WHEN** a consumer session invokes the `agent-process` skill
- **THEN** the skill body names the three goals, and §I–VII on one line that holds only a link to the `#operative-principles` anchor of `always-on.md`; and the body links the `#claude-harness` anchor of `always-on.md`, whose harness tactics carry the `gh issue view` recovery, no `/compact` request, and the `Explore` delegation with its two-or-more trigger and `path:line` conclusion
