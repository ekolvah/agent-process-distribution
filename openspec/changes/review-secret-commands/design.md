## Context

See proposal.md — Why. The row is built in `manual.rows` from `t.repo`; Install step 3 of
SKILL.md tells the agent to have the person set the secret before the confirm question.

## Goals / Non-Goals

**Non-Goals:** `init` running either command; any change to when the row is printed or to the
`(cannot read: <reason>)` suffix.

## Decisions

- **D1 — the URL stays as `<where>`, the commands follow ` -- `.** The row becomes
  `manual review-secret: https://github.com/<owner/repo>/settings/secrets/actions -- claude
  setup-token, then gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo> and paste the token
  at its prompt; the review caller passes it to the review`, the `<where> -- <what>` shape of
  every other row. Alternative: commands only. Rejected: `gh secret set` needs a token that
  may write secrets, and a person whose `gh` lacks it already sees this row as
  `(cannot read: HTTP 403)` (`test_init_remote.py` case `secret-403`); the page is their route.
  ADR 0032 D2 ("naming the repository's secrets page") therefore stays true.
- **D2 — the value goes through `gh`'s prompt, not `--body`.** Without `--body` `gh secret
  set` reads the value interactively (proposal, observed help), so the token stays out of
  shell history and out of the agent's transcript. Install step 3 says the person runs both
  commands; the agent never asks for or handles the token.
- **D3 — no new check.** The text is the fix; the existing `test_review_prerequisites_are_printed`
  is extended to assert both commands with `{CONSUMER}` substituted.

## Risks / Trade-offs

- [`claude setup-token` requires a Claude subscription] → the same precondition as the
  token itself (claude-code-action setup doc); an API-key consumer is out of scope, as the
  review caller passes only `CLAUDE_CODE_OAUTH_TOKEN`.
- [A future `gh` drops the interactive prompt] → the row still names the right secret and
  repository; `gh secret set --help` is the reference to re-check.

## Migration Plan

Text only: the next release prints the new row; rollback is a revert of the PR.
