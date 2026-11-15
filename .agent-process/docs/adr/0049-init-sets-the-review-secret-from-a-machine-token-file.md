---
status: "accepted"
date: 2026-11-15
decision-makers: ekolvah
---

# Init sets the review secret from a machine token file

## Context and Problem Statement

[ADR 0032](0032-the-review-gate-is-installed-in-every-consumer.md) D2 left
`CLAUDE_CODE_OAUTH_TOKEN` to the person: in every new consumer they ran `claude setup-token` and
`gh secret set` before the installation PR's `agent-review` could pass. The agent cannot mint
the token: `claude setup-token` has no option but `--help` and, run from the agent's shell,
waits on a browser flow and prints nothing. The token lasts a year, so one copy per machine can
serve every repository, as the Grafana token already does
([ADR 0048](0048-init-sets-up-task-readings-from-the-grafana-mcp-config.md)).

## Considered Options

* A token file, `~/.claude/agent-process-review-token`, that `init` copies into the secret
* An environment variable holding the token
* A Console API key
* Workload identity federation for `claude-code-action`
* A GitHub organization secret
* The agent opening a real terminal for `claude setup-token`

## Decision Outcome

Chosen: **a token file, copied by a step of `init`.**

* **D1 — the source.** `~/.claude/agent-process-review-token`, read like the Grafana `_FILE`
  token: stripped, missing or blank is no token, unreadable is `(cannot read: …)`. The person
  runs `claude setup-token` once per machine in their own terminal and saves its output there.
* **D2 — a step before the push.** `review-secret` runs after the Project steps and before
  `onboarding-commit`, so the first pushed head's `agent-review` runs with the secret. It is
  `unchanged` when the secret exists, `planned` when the file holds a token, and absent when
  the names cannot be read or the file holds none; then the `manual review-secret` row names
  the one-time file step and why. The value goes on `gh secret set`'s standard input, never in
  a command line or the output.
* **D3 — a bad token.** The file replaces the person's per-repository paste. An expired,
  revoked or mis-pasted token is copied as is and caught by the `agent-review / agent-review`
  check failing authentication on the installation PR's first head. A rerun of `init` prints
  `unchanged review-secret` and repairs nothing: the person fixes the file and runs
  `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` from it.

### Consequences

* Good, because after the one-time file step a new consumer needs no hand-off for the review
  secret.
* Bad, because the file is readable by any process of the person, including the agent — the
  same exposure as `~/.claude/.credentials.json` beside it; `init` never prints it.
* Bad, because the token expires yearly; renewal is the person's, and `init` only fills a
  missing secret, never rotates one.

### Pros and Cons of the Options

* Environment variable — `CLAUDE_CODE_OAUTH_TOKEN` in the local environment outranks the
  `/login` credentials and would switch local Claude Code off the subscription login; another
  name sits in every child process's environment and in the shell history.
* Console API key — API billing instead of the subscription, and the same storage question.
* Workload identity federation — API billing, Console setup, and an `id-token` permission the
  caller must grant the reusable workflow.
* Organization secret — needs the repositories moved into an organization; a personal account
  has no account-level Actions secrets.
* A launched terminal — per-platform launch code, and the person still copies the token.

### Confirmation

`tests/publisher/test_init_review_secret.py` holds D1–D2, and
`tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed` the row without a
usable token file.
