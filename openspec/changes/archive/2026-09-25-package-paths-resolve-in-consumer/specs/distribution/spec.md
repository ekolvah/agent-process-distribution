## ADDED Requirements

### Requirement: Package paths resolve in a consumer
A file of the package — the skill directory, `agents/`, and `commands/` — SHALL NOT name a
path under the publisher's `.agent-process/` root, and no relative Markdown link of a skill
file SHALL leave the skill directory. The principles the architect review applies SHALL be a
file of the skill directory. A plugin agent SHALL name each package file by its path in the
skill directory, from the repository root, and SHALL name `${CLAUDE_PLUGIN_ROOT}` as the root
where the repository has no skill directory.

#### Scenario: Publisher-only path in the package
- **WHEN** a package file names a `.agent-process/` path, a skill file links a relative target outside the skill directory, or a plugin agent names a path in the skill directory that is not a package file or names no `${CLAUDE_PLUGIN_ROOT}` fallback
- **THEN** the publisher tests fail and name that file and path
