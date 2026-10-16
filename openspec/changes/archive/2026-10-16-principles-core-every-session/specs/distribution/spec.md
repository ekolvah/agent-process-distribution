## MODIFIED Requirements

### Requirement: An installed repository's sessions carry the goal function
A confirmed installer run SHALL write the managed `.claude/rules/agent-process.md`: the line
`# agent-process:managed`, a blank line, then the installing release's
`skills/agent-process/always-on.md`, which holds the `## Goal function`,
`## Operative principles` and `## Claude harness` sections and no `paths` frontmatter.
`## Operative principles` SHALL state each of §I–VII, and every `§` reference in the file SHALL
name one of them. An existing file without that first line SHALL be a `conflict`.

#### Scenario: Rules file written
- **WHEN** a confirmed run installs into a fresh repository, and again into one that carries another release's rules file
- **THEN** `.claude/rules/agent-process.md` is the marker line, a blank line and the release's `always-on.md`, and that text starts with no `---` frontmatter, holds `## Goal function`, `## Operative principles` and `## Claude harness`, and `## Operative principles` states each of §I–VII, the only principles its `§` references name

#### Scenario: Unmanaged rules file
- **WHEN** a dry-run meets a `.claude/rules/agent-process.md` whose first line is not `# agent-process:managed`
- **THEN** it prints `conflict` for `rules`, exits non-zero, and no consumer file has changed
