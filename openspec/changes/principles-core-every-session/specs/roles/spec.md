## MODIFIED Requirements

### Requirement: The skill carries the principles core and harness tactics
The `agent-process` skill SHALL state the three goals and name each principle §I–VII with a link
to `principles.md` for their detail, on one line that links `always-on.md#operative-principles`
and restates no rule. Each section in `principles.md` SHALL link that anchor for its rule. The skill SHALL link the
package's `always-on.md`, which holds the full goal function, the operative principles and the
Claude-harness token tactics.
Its tactic for a compaction
between the RED commit and GREEN SHALL recover state from the branch, the RED commit and one
`gh issue view`, and SHALL NOT ask the person to compact. Its delegation tactic SHALL send a
question needing two or more lookups of material the session will not edit to the `Explore`
subagent for a `path:line` conclusion.

#### Scenario: A consumer reads principles and tactics from the skill
- **WHEN** a consumer session invokes the `agent-process` skill
- **THEN** the skill body names the three goals, each of §I–VII with a link to `principles.md` on one line that holds only those links and a link to `always-on.md#operative-principles`; each of the seven sections of `principles.md` links the same anchor; and the body links `always-on.md#claude-harness`, whose harness tactics carry the `gh issue view` recovery, no `/compact` request, and the `Explore` delegation with its two-or-more trigger and `path:line` conclusion
