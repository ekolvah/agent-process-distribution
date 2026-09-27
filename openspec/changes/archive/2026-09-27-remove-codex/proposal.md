# Proposal

## Why

The person decided (2026-09-27): Codex leaves the process; Claude Code is the only carrier
for development and code review, with no fallback. The process still assumes two carriers:
the review job waits up to 600 s for a Codex review the author requests with `@codex review`
before Claude reviews as a fallback, the review gate trusts threads of the Codex app, the
installer writes Codex skills and a user-wide Codex skill link, and the repository carries a
Codex hook adapter, a trust check and a `self-review` reviewer value. Every head now pays the
wait for a reviewer that no longer runs, and each Codex path is code and procedure to keep
working without a user.

## What Changes

- **BREAKING** `reusable-agent-review.yml` reviews every non-release head with the Claude Code
  action: one read of the head's closing review comment (a re-run returns on it), the action
  when it is absent, the verification, the enforcement. Its input `codex-timeout-seconds`
  leaves; the publisher caller stops passing it. Nobody requests a review.
- `request_codex_review.py` becomes `head_review.py`: presence is the closing comment of the
  workflow token's login naming the head; the Codex login, native reviews and `--reviewer`
  leave.
- `check_blocking_review_threads.py` and `resolve_review_thread.py` trust only threads of
  `github-actions`.
- The Codex adapter leaves: `.codex/hooks.json`, `codex_hooks.py`, `agent_policy.py`,
  `check_codex_project_trust.py`, `.agents/skills/` and their tests; AGENTS.md drops its
  Codex sections.
- `init.py` runs `openspec init --tools claude` and no longer links
  `~/.agents/skills/agent-process`; the release-drift message drops Codex.
- `start_change.py` accepts only `Claude` as a carrier; the architect review schema accepts
  only `architect-reviewer`.
- SKILL.md, REVIEW_CONTRACT.md, the `openspec/config.yaml` context and script docstrings name
  one carrier; ADR 0033 supersedes ADR 0003 and ADR 0015.

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: local safety is the Claude Code deny-list; the Claude review replaces the
  Codex-first review; thread trust and the contract name one reviewer.
- `roles`: one carrier per role; route selection between agents leaves.
- `planning`: the architect review is the `architect-reviewer` subagent only.
- `implementation`: the review of the head is the Claude review job's.
- `maintenance`: "Native first" names the tools without Codex.
- `distribution`: confirmation moves the process checkout only; the Codex skill link and its
  conflict leave; the drift fix names the plugin only.

## Impact

- Added: `.agent-process/scripts/head_review.py` (renamed from `request_codex_review.py`),
  `tests/publisher/test_head_review.py` (renamed from `test_request_codex_review.py`),
  `.agent-process/docs/adr/0033-claude-code-is-the-only-carrier.md`.
- Edited: `.github/workflows/reusable-agent-review.yml`, `.github/workflows/agent-review.yml`,
  `.agent-process/scripts/check_blocking_review_threads.py`, `.agent-process/scripts/hooks.py`,
  `.agent-process/scripts/navigation_policy.py` (docstrings), `.agent-process/REVIEW_CONTRACT.md`,
  `skills/agent-process/scripts/{resolve_review_thread,start_change,wait_for_pr,init}.py`,
  `skills/agent-process/SKILL.md`, `skills/agent-process/architect-review.schema.json`,
  `AGENTS.md`, `openspec/config.yaml` (context), `openspec/specs/roles/spec.md` (Purpose only, design D7a), ADR 0003 and ADR 0015 (status),
  `tests/publisher/{test_reusable_workflows,test_blocking_review_threads,test_resolve_review_thread,test_start_change,test_planning_workflow,test_init}.py`,
  `tests/publisher/init_harness.py`, `tests/publisher/test_init_conflicts.py`, `tests/agent_process/{test_delivery_gate_wiring,test_navigation_policy}.py`.
- Removed: `.codex/hooks.json`, `.agent-process/scripts/{codex_hooks,agent_policy,check_codex_project_trust}.py`,
  `.agents/skills/` (seven files), `tests/publisher/test_codex_hooks.py`,
  `tests/agent_process/test_codex_project_trust.py`.
- Out of scope: `.agent-process/docs/telemetry-measurement-setup.md` (telemetry left the process, #169);
  the consumer review caller template (#223), which passes no input;
  archived changes and ADRs other than 0003 and 0015 keep their history.
- Consumers: an existing `.agents/skills/` and `~/.agents/skills/agent-process` are left in
  place for the person to delete; a repository with the Codex GitHub app uninstalls it or turns
  its reviews off, because its threads no longer block.
