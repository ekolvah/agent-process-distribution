# Proposal

## Why

The review gate — a review of the head and the blocking of unresolved P0/P1 threads — is
part of the consumer's delivery procedure: the skill's Delivery section waits on the
`agent-review` check. Yet
`init.py` installs no caller of `.github/workflows/reusable-agent-review.yml`, so its only
caller is this repository's own `agent-review.yml` (issue #215). A consumer therefore
delivers without the review its procedure waits for, and `activate_protection` requires the
review context only "when the default branch carries" a caller no installer writes.

The person decided (issue #215): the review gate is mandatory for every consumer. The
reusable/caller split then has its second caller and stays.

The person decided (2026-09-27): Codex leaves the process; Claude Code is the only carrier
for development and review, with no fallback. The consumer caller therefore depends on no
Codex input or prerequisite. Removing Codex from the callee and the process is a separate
change.

Observed: `reusable-agent-review.yml` already runs from a consumer without change — its
trusted checkout is `ekolvah/agent-process-distribution` at `github.job_workflow_sha`, the
same pattern `quality.yml` runs in consumers today, including `release_pr.py` from the
trusted source.

## What Changes

- `init.py` installs a managed `.github/workflows/agent-review.yml` whose job `agent-review`
  calls `reusable-agent-review.yml@v<version>` with the `CLAUDE_CODE_OAUTH_TOKEN` secret and
  no input, as a new `review` step after `workflow`; an existing file without the managed
  marker is a `conflict`.
- `init.py` prints a new `manual` row: set the repository secret `CLAUDE_CODE_OAUTH_TOKEN`.
  The installer still writes no secret.
- **BREAKING** `activate_protection` refuses when the default branch lacks
  `.github/workflows/agent-review.yml`, and always requires both `agent-process / quality`
  and `agent-review / agent-review`. A consumer installed by an earlier release reruns
  `init` first.
- The publisher's own `agent-review.yml` keeps calling `@main` (ADR 0012).

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the installed footprint adds the review caller; the review caller renders
  at the release tag; the review secret is printed as `manual`; protection
  activation requires the review caller and context unconditionally.

## Impact

- Added: `skills/agent-process/templates/agent-review.yml`,
  `.agent-process/docs/adr/0032-the-review-gate-is-installed-in-every-consumer.md`.
- Edited: `skills/agent-process/scripts/init.py`,
  `skills/agent-process/scripts/activate_protection.py`, `skills/agent-process/SKILL.md`
  (Install steps 4–5), `tests/publisher/init_harness.py`, `tests/publisher/test_init.py`,
  `tests/publisher/test_init_conflicts.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/test_activate_protection.py`, `tests/publisher/test_reusable_workflows.py`,
  `tests/publisher/test_plugin.py` (closed template set).
- Removed: none. `reusable-agent-review.yml` and the publisher caller are unchanged.
- Consumers: a new required check and a secret to set.
