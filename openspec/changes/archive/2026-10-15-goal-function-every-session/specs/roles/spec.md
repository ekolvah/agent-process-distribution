## MODIFIED Requirements

### Requirement: The skill carries the principles core and harness tactics
The `agent-process` skill SHALL state the three goals and one line per principle §I–VII,
linking `principles.md` for the full text, and SHALL link the package's `always-on.md`, which
holds the full goal function and the Claude-harness token tactics.
Its tactic for a compaction
between the RED commit and GREEN SHALL recover state from the branch, the RED commit and one
`gh issue view`, and SHALL NOT ask the person to compact.

#### Scenario: A consumer reads principles and tactics from the skill
- **WHEN** a consumer session invokes the `agent-process` skill
- **THEN** the skill body names the three goals, each of §I–VII with a link to `principles.md`, and links the `#claude-harness` anchor of `always-on.md`, whose harness tactics carry the `gh issue view` recovery and no `/compact` request
