## RENAMED Requirements

- FROM: `### Requirement: Actions credentials are printed, not set`
- TO: `### Requirement: The review secret is set from the machine's token`

## MODIFIED Requirements

### Requirement: The review secret is set from the machine's token
While the repository's secret names can be read, a run SHALL print the transition
`review-secret` before `onboarding-push`: `unchanged` when the names include
`CLAUDE_CODE_OAUTH_TOKEN`, otherwise `planned` when `~/.claude/agent-process-review-token`
holds a non-blank token, which a confirmed run SHALL set as that secret with surrounding
whitespace removed. The token SHALL NOT appear in a command line or the output. A failed write
SHALL print an error naming `review-secret` and exit 1 before the push. `init` SHALL write a
secret or a variable only through a transition it printed.

While the secret is missing after the run and no `review-secret` transition was planned, the
run SHALL print one `manual review-secret` row naming the repository's Actions secrets page,
`claude setup-token` run in the person's own terminal, and saving the printed token to
`~/.claude/agent-process-review-token`, ending with
`(not found: ~/.claude/agent-process-review-token)` when the file is missing or blank, or
`(cannot read: <file>: <reason>)` when it cannot be read, in which case no step is planned.

#### Scenario: Secret set from the token file
- **WHEN** a confirmed run meets a repository without the secret and a token file holding a token
- **THEN** it prints `written review-secret` before `onboarding-push`, the secret's value is that token, no command line or output line carries the token, and no `manual review-secret` row is printed

#### Scenario: Secret planned
- **WHEN** a dry-run meets a repository without the secret and a token file holding a token
- **THEN** it prints `planned review-secret`, issues no command that writes a secret, prints no `manual review-secret` row, and no command line or output line carries the token

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run meets a repository without the secret and no token file, a blank one, or one that cannot be read
- **THEN** it prints no `review-secret` transition, issues no command that writes a secret, and prints the `manual review-secret` row ending with `(not found: ~/.claude/agent-process-review-token)`, or `(cannot read: …)` for the unreadable file

#### Scenario: Readings prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository with neither the variable `GRAFANA_URL` nor the secret `GRAFANA_SERVICE_ACCOUNT_TOKEN`, on a machine whose `~/.claude.json` configures no `grafana` MCP server and with no `~/.claude/agent-process-review-token`
- **THEN** its output carries one `manual task-readings` row naming that repository's Actions variables page, `gh variable set GRAFANA_URL -R <owner/repo>`, `gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>`, `agent-process dashboard <owner/repo>` of that repository, Grafana's dashboard import and `(not found: grafana MCP server in ~/.claude.json)`, and no command it issued writes a secret or a variable

#### Scenario: Secret already set
- **WHEN** a run meets a repository whose secret names include `CLAUDE_CODE_OAUTH_TOKEN`
- **THEN** it prints `unchanged review-secret`, nothing writes the secret, and no `manual review-secret` row is printed

#### Scenario: Secret write fails
- **WHEN** a confirmed run's `gh secret set` of the review secret fails
- **THEN** it prints an error naming `review-secret`, exits 1, and pushes no installation branch
