## ADDED Requirements

### Requirement: Install's admin steps run as the person
`activate_protection` and `agent_identity` SHALL run each of their `gh` calls without
`GH_TOKEN` and `GITHUB_TOKEN` in its environment, except the bot-side calls of `agent_identity`, which SHALL carry the bot's token in
`GH_TOKEN`.

#### Scenario: A clone with the agent's identity
- **WHEN** `activate_protection` or `agent_identity` runs with a `GH_TOKEN` in its environment
- **THEN** every `gh` call it issues runs without `GH_TOKEN` and `GITHUB_TOKEN`, except the bot-side calls of `agent_identity`, which carry the bot's token in `GH_TOKEN`
