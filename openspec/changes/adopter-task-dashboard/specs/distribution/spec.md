## MODIFIED Requirements

### Requirement: Actions credentials are printed, not set
A run SHALL print, as `manual`, setting the repository secret `CLAUDE_CODE_OAUTH_TOKEN` while
the repository's secret names do not include it, and `init` SHALL issue no command that writes
a secret or a variable. The row SHALL name the repository's Actions secrets page and give the
commands `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`, with
the consumer repository substituted. A run SHALL print one `manual task-readings` row while the
repository's variable names do not include `GRAFANA_URL` or its secret names do not include
`GRAFANA_SERVICE_ACCOUNT_TOKEN`; the row SHALL name the repository's Actions variables page and
give the commands `gh variable set GRAFANA_URL -R <owner/repo>`,
`gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>` and
`agent-process dashboard <owner/repo>`, with the consumer repository substituted, and SHALL
name Grafana's dashboard import.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository without the secret
- **THEN** its output carries one `manual` row for the secret naming that repository's Actions secrets page, `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` of that repository, and no command it issued writes a secret

#### Scenario: Readings prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository with neither the variable `GRAFANA_URL` nor the secret `GRAFANA_SERVICE_ACCOUNT_TOKEN`
- **THEN** its output carries one `manual task-readings` row naming that repository's Actions variables page, `gh variable set GRAFANA_URL -R <owner/repo>`, `gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>` and `agent-process dashboard <owner/repo>` of that repository, and Grafana's dashboard import
