## Context

`init` already copies one credential into a repository secret; `readings_setup.steps` sets
`GRAFANA_SERVICE_ACCOUNT_TOKEN` from the machine's MCP config on `gh`'s standard input
(ADR 0048), through its local `gh_step`. Before the writes `manual.readings` reads
`gh secret list`; after them `manual.rows` reads it again for the rows. The review caller needs
the secret on the first pushed head, so the step must run before `onboarding-push`.

## Standard approach

- `claude setup-token`: "opens the same browser authorization flow as `/login`, and the token
  prints to the terminal after you approve access in the browser. It does not save the token
  anywhere"; the token is one-year and "can only make model requests" —
  https://code.claude.com/docs/en/authentication.md#generate-a-long-lived-token. Observed
  2026-11-15 on Claude Code 2.1.296: `claude setup-token --help` lists no option but
  `-h, --help`; run from the agent's Bash during the `ekolvah/trailer-search` install it
  printed nothing for 4 minutes until interrupted.
- `/install-github-app` "adds your authentication secret" through an interactive wizard, one
  repository at a time; headless use is not documented —
  https://code.claude.com/docs/en/github-actions.md.
- The `/login` credential (`~/.claude/.credentials.json`) is short-lived: its `expiresAt`, read
  2026-11-15, lies within hours of issue; the docs do not support it as
  `CLAUDE_CODE_OAUTH_TOKEN` — https://code.claude.com/docs/en/authentication.md#credential-management.
- `CLAUDE_CODE_OAUTH_TOKEN` in the local environment outranks the `/login` subscription
  credentials — https://code.claude.com/docs/en/authentication.md#authentication-precedence.
- `gh secret set` reads the value from standard input when `--body` is absent —
  https://cli.github.com/manual/gh_secret_set. Secret values are never returned by the API,
  and a personal account has no account-level Actions secrets —
  https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions.
- Secret-free alternative: workload identity federation for `claude-code-action`
  (`anthropic_federation_rule_id`, `id-token: write`) —
  https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md.

## Goals / Non-Goals

**Goals:** no per-repository hand-off for the review secret once the machine holds a token.

**Non-Goals:** rotating an expired secret in repositories that already have one (the step only
fills a missing secret); minting the token without the person (no documented way).

## Decisions

- **D1 — a token file, not an environment variable.** Source:
  `~/.claude/agent-process-review-token`, read by the same helper as the Grafana
  `_FILE` token, extracted from `manual._mcp_grafana`: stripped, missing or blank is no token,
  unreadable raises `Unreadable`. An environment variable under the action's name would switch
  local Claude Code off `/login` (precedence above); another name would sit in every child
  process's environment and in the shell history of the command that sets it.
  Alternatives: Console API key — API billing instead of the subscription, same storage
  question; workload identity federation — API billing, Console setup, and an `id-token`
  permission the caller must grant the reusable workflow; a GitHub organization secret —
  moving the repositories into an organization; the agent opening a real terminal window —
  per-platform launch code, and the person still copies the token.
- **D2 — a step of `init`, before the push, on shared helpers.** `review-secret` sits between
  the Project steps and `onboarding-commit`, so the first head's `agent-review` runs with the
  secret. `readings_setup`'s `gh_step` moves to module level and builds it; `_run` reads the
  secret names once (`manual._kept(lambda: manual._names(t, "secret"))`) and passes them to
  this step and to `readings_setup.steps`, which forwards them to `manual.readings` (it already
  takes them). Unreadable names plan no step; the row keeps `_outstanding`'s `(cannot read: …)`.
  The row prints only while no step is planned, as `_readings_row` does, so a dry-run that plans
  the write asks nothing of the person. No new script: the problem is the hang above, and the
  standard (`gh secret set` on stdin) is what the step calls.
- **D3 — the token file's failure modes.** The file replaces the person's per-repository paste;
  what that paste proved, a working token in that secret, now has these catchers:
  - missing or blank → no step; the row ends `(not found: …)`
    (`test_review_prerequisites_are_printed`);
  - unreadable (a directory, bad encoding, permissions) → no step; the row ends
    `(cannot read: <file>: <reason>)` (same test, directory case);
  - expired, revoked or mis-pasted token → copied as is; caught by the `agent-review /
    agent-review` check failing authentication on the installation PR's first head. A rerun of
    `init` prints `unchanged review-secret` and repairs nothing: the person fixes the file and
    runs `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` from it. ADR 0049 records this.

## Risks / Trade-offs

- [The token file is readable by any process of the person, including the agent] → same
  exposure as `~/.claude/.credentials.json` beside it; `init` never prints it. The token
  expires yearly; renewal is the person's, rotation a non-goal.

## Migration Plan

Takes effect with the release; a machine without the file sees today's row, plus the reason.
Rollback: revert the release; secrets already set stay valid.
