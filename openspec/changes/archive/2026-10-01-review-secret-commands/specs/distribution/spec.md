## MODIFIED Requirements

### Requirement: The review secret is printed, not set
A run SHALL print, as `manual`, setting the repository secret `CLAUDE_CODE_OAUTH_TOKEN` while
the repository's secret names do not include it, and `init` SHALL issue no command that writes
a secret. The row SHALL name the repository's Actions secrets page and give the commands
`claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`, with the
consumer repository substituted.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository without the secret
- **THEN** its output carries one `manual` row for the secret naming that repository's Actions secrets page, `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` of that repository, and no command it issued writes a secret
