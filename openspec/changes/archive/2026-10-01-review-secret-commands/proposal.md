## Why

`agent-process init --dry-run` (3.2.2) on `ekolvah/agent-process-sandbox-4` printed

```
manual review-secret: https://github.com/ekolvah/agent-process-sandbox-4/settings/secrets/actions -- set CLAUDE_CODE_OAUTH_TOKEN, the token the review caller passes to the review
```

and the person had to ask where the token comes from before acting on the row (#288).
Root cause: the row (`skills/agent-process/scripts/manual.py:89-92`) and Install step 3 of
`skills/agent-process/SKILL.md` name the secret and the page that stores it, never the
command that issues its value; the `plugin-channel` row beside it already gives commands.

Observed sources the fix rests on:

- `claude setup-token --help` (Claude Code 2.1.283): `Set up a long-lived authentication
  token (requires Claude subscription)`.
- `anthropics/claude-code-action` `docs/setup.md`: "Name: `CLAUDE_CODE_OAUTH_TOKEN`, Value:
  Your Claude Code OAuth token (Pro and Max users can generate this by running `claude
  setup-token` locally)".
- `gh secret set --help` (gh 2.87.3): `-b, --body string  The value for the secret (reads
  from standard input if not specified)`, and the example `# Paste secret value for the
  current repository in an interactive prompt` / `$ gh secret set MYSECRET`; `-R, --repo
  [HOST/]OWNER/REPO` selects the repository.

## What Changes

- The `review-secret` row keeps the secrets-page URL and gives the two commands with the
  consumer substituted: `claude setup-token`, then
  `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`, pasting the token at its prompt
  (design D1).
- Install step 3 of SKILL.md names the same two commands and that the person runs them,
  not the agent, so the token never enters the chat.
- `init` still writes no secret; the row's presence condition is unchanged.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the requirement "The review secret is printed, not set" names the commands
  the row carries.

## Impact

- Edited: `skills/agent-process/scripts/manual.py`, `skills/agent-process/SKILL.md`,
  `tests/publisher/test_init_remote.py`.
- Added: `openspec/changes/review-secret-commands/` (archived into
  `openspec/specs/distribution/spec.md` on delivery).
- ADR 0032 is not edited: its D2 decision — `init` never writes the secret and prints a
  `manual review-secret:` row — stands; the row's wording is the spec's.
