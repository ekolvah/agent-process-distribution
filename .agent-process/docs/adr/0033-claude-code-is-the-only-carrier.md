---
status: "accepted"
date: 2026-09-27
decision-makers: ekolvah
---

# Claude Code is the only carrier

## Context and Problem Statement

[ADR 0027](0027-v2-standards-replace-the-bespoke-control-plane.md) let two agents, Claude
Code and Codex, carry every role, and it kept
[ADR 0015](0015-owner-requested-codex-primary-with-claude-fallback.md)'s review order: a
review requested from Codex came first, and Claude reviewed only when Codex left the head
silent. Every head therefore waited up to 600 s for Codex. The installer wrote a second set of
OpenSpec skills and a user-wide skill link. The procedure also carried two entry points, a
self-review in place of the subagent, and a hook adapter with no other user (#222).

## Considered Options

* Claude Code carries every role and the review job reviews every head
* Keep Codex as an optional second carrier

## Decision Outcome

Chosen: **Claude Code is the only carrier.**

* **D1 — review.** `reusable-agent-review.yml` reads the head's review first. It runs the
  Claude review only when that review is absent, then verifies it within 60 s. A re-run of a
  reviewed head does not pay for a second review. The `workflow_call` input
  `codex-timeout-seconds` is removed, which is **breaking** for a caller that still passes it.
* **D2 — presence.** `request_codex_review.py` is renamed `head_review.py`. A head counts as
  reviewed only when `github-actions[bot]` posts a comment naming it; `--reviewer` is removed.
* **D3 — threads.** Only the review job's threads block the merge or can be resolved by the
  script. What stops being proven: that a Codex P1 blocks. No catcher is needed, because a
  Codex thread is now advisory, the same as a person's.
* **D4 — adapter.** The following are removed: `.codex/hooks.json`, `codex_hooks.py`,
  `agent_policy.py`, `check_codex_project_trust.py`, `.agents/skills/` and their tests. What
  stops being proven: that a hook denies a push to `main`, a force push and `gh pr merge`.
  Catcher: a test asserts those rules in the deny-list of `.claude/settings.json`. It proves
  the configuration, not the platform's enforcement, which is the same level the removed test
  reached.
* **D5 — installer.** `init` runs `openspec init --tools claude` (observed 2026-09-27: it
  writes no `.agents/` path). The skill link step is removed, along with its conflicts. What
  stops being proven: only the link, which nothing reads any more. The installer never deletes
  a consumer's leftover `.agents/skills/` or `~/.agents/skills/agent-process`.

### Consequences

* Good, because every head gets one review with no 600 s wait, and the procedure exists once.
* Good, because the installer no longer owns a user-wide path shared by every repository.
* Bad, because every push pays for a Claude review. The fallback already paid for one whenever
  Codex left a head silent.
* Bad, because a consumer migrates: it reruns `init`, uninstalls the Codex app or turns its
  reviews off, and may delete the two leftover paths.

ADR 0027's two-carrier decision is superseded by this ADR. The rest of ADR 0027 stays valid.

### Confirmation

The tests of task 1.1 of change `remove-codex`:

* `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
  and `::test_review_steps_call_head_review_with_its_arguments` confirm D1.
* `tests/publisher/test_head_review.py::test_presence_is_only_the_review_jobs_closing_comment`,
  `::test_rerun_reads_the_closing_comment_not_inline_nodes` and `::test_reviewer_flag_is_gone`
  confirm D2.
* `tests/publisher/test_blocking_review_threads.py::test_open_codex_p1_does_not_block` and
  `tests/publisher/test_resolve_review_thread.py::test_resolve_refuses_a_codex_thread` confirm
  D3.
* `tests/agent_process/test_delivery_gate_wiring.py::test_claude_denies_push_to_main_force_push_and_merge`
  confirms D4.
* `tests/publisher/test_init.py::test_openspec_tools_are_claude_only` and
  `::test_user_skill_path_is_left_alone` confirm D5.
* `tests/publisher/test_start_change.py::test_codex_carrier_is_rejected` and
  `tests/publisher/test_planning_workflow.py::test_roles_and_carriers` confirm that no carrier
  other than Claude is accepted.
