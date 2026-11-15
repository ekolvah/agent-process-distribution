## Why

Every new consumer waits on the person for `CLAUDE_CODE_OAUTH_TOKEN`: `init` only prints the
`manual review-secret` row (ADR 0032 D2), and an installation without it gets a red
`agent-review` on its first head. The agent cannot mint the token: `claude setup-token` hangs
when the agent runs it (design.md, Standard approach). The token lasts a year, so one copy per
machine can serve every repository, as the Grafana token already does (ADR 0048).

## What Changes

- `init` sets `CLAUDE_CODE_OAUTH_TOKEN` from `~/.claude/agent-process-review-token` when the
  secret is missing, before the installation branch is pushed; otherwise the
  `manual review-secret` row says why and how to create the file.
- Install's Prepare step in `SKILL.md` changes from "set the secret per repository" to "save
  the token once per machine"; step 3's hand-off asks for that file.
- New ADR 0049 records the token source and the alternatives; ADR 0032 D2 is superseded.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: requirement *Actions credentials are printed, not set* is renamed
  *The review secret is set from the machine's token* and now sets the secret from the token
  file, printing the row only when it cannot.

## Impact

- Edited: `skills/agent-process/scripts/manual.py` (shared token-file read, row text and
  reason), `skills/agent-process/scripts/readings_setup.py` (`gh_step` at module level, secret
  names passed in), `skills/agent-process/scripts/init.py` (the `review-secret` step, one shared
  secret-names read, docstring), `skills/agent-process/SKILL.md` (Prepare, Install step 3),
  `tests/publisher/init_harness.py` (`no_token`, `line` moved from the readings tests),
  `tests/publisher/test_init_readings.py` (uses them), `tests/publisher/test_init_remote.py`
  (row test).
- Added: `tests/publisher/test_init_review_secret.py`,
  `.agent-process/docs/adr/0049-init-sets-the-review-secret-from-a-machine-token-file.md`.
- Edited docs: `.agent-process/docs/adr/0032-the-review-gate-is-installed-in-every-consumer.md`
  (superseded-on-D2 note).
- No new dependency.
