## MODIFIED Requirements

### Requirement: Required checks protect the default branch
The default branch SHALL require `agent-process / quality` through the repository ruleset
and `agent-review / agent-review` through classic protection. Both lists are declared in the
repository. Drift between the declared and the installed classic protection SHALL block a
push before `ci_check` runs. The review gate SHALL report a head ready only when every
context of both lists is green on it.

#### Scenario: Missing required context
- **WHEN** an installed protection lacks a declared context
- **THEN** the pre-push hook reports drift and does not run `ci_check`

#### Scenario: Ruleset context red
- **WHEN** `agent-process / quality` is red on the PR head and `agent-review / agent-review` is green
- **THEN** the review gate reports `fix-blocking` and names `agent-process / quality`
