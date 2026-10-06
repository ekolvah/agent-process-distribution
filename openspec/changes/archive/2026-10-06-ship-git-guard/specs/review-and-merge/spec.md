## MODIFIED Requirements

### Requirement: Local safety in Claude Code
Push to `main`, force push and `gh pr merge` SHALL be denied locally by the
plugin's git guard (distribution requirement "The plugin ships the git guard") in a repository
carrying `.github/workflows/agent-process.yml`. Merging is the person's, except the release PR,
which the platform's auto-merge merges once its required checks pass.

#### Scenario: Push to main from Claude Code
- **WHEN** an agent runs `git push origin main`, `git push --force` or `gh pr merge` in Claude Code in an adopted repository
- **THEN** the plugin's git guard denies it and names the alternative
