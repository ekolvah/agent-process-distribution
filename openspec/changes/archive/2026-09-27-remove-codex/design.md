# Design

## Context

See proposal.md — Why. Today `reusable-agent-review.yml` runs `request_codex_review.py --wait
--reviewer chatgpt-codex-connector --reviewer github-actions` for up to
`inputs.codex-timeout-seconds` (600 s from the publisher caller), runs the Claude Code action
when that read exits 3 (absent), and verifies the Claude closing comment with the same script
on `--reviewer github-actions` for 60 s. `request_codex_review.wait_for_review` reads once when
the timeout is 0. The gate scripts trust thread authors
`{"chatgpt-codex-connector", "github-actions"}`.

## Goals / Non-Goals

- Goal: one carrier. No step, script, file, spec or procedure line waits for, trusts, installs
  or names Codex as a live part of the process.
- Non-goal: rewriting history — archived changes, ADRs other than 0003 and 0015, and review
  provenance in test comments (`Codex's P1 on PR 140`) stay.
- Non-goal: `.agent-process/docs/telemetry-measurement-setup.md` (telemetry left with #169).
- Non-goal: the consumer review caller `skills/agent-process/templates/agent-review.yml`
  (#215, merged in #223): it calls `reusable-agent-review.yml@v<version>`, passes no input,
  and survives this change unchanged.
- Non-goal: removing the user-scope process checkout of `init` (see D5).

## Decisions

**D1 — The review job reviews every non-release head.** Steps: detect a release PR →
`Read the Claude review of the head` (`id: review`, not on a release PR): `head_review.py
--timeout-seconds 0`, exit 0 → `absent=false`, 3 → `absent=true`, other → fail → `Claude
review` when `steps.review.outputs.absent == 'true'` → `Verify the Claude review of the head`
under the same condition, `--timeout-seconds 60` → enforce, `if: always()`. The first read
keeps issue 139's behaviour: `gh run rerun` of a reviewed head returns on its closing comment
instead of paying for a second review. The `workflow_call` input `codex-timeout-seconds`
leaves (**BREAKING** for a caller that passes it: an undeclared input fails the call); the
publisher caller drops its `with`. The consumer caller passes none and pins the release tag,
so a consumer gets this review with the release its next `init` renders.
Alternative: drop the first read and always review. Rejected: every re-run by
`resolve_review_thread` would review the unchanged head again and could add new threads.

**D2 — `request_codex_review.py` becomes `head_review.py`.** Presence is only a PR comment by
`github-actions[bot]` whose body names the head (`Reviewed head SHA: <sha>`); the Codex login,
the `**Reviewed commit:**` pattern, the native-review branch and `--reviewer` leave. The CLI is
today's minus `--reviewer`: `--wait` (still required) `--repo --pr --head-sha --timeout-seconds
--poll-seconds`, exits 0/3/2 unchanged. The workflow's two calls are coupled to that parser by
`test_review_steps_call_head_review_with_its_arguments`, which parses each step's argv with the
script's own `main` — a drift in either direction fails a test instead of every head's review. The rename
is a `git mv` of the script and its test so history follows.

**D3 — Only the review job's threads block or resolve.** `_REVIEWERS` becomes
`{"github-actions"}` in `check_blocking_review_threads.py` and `resolve_review_thread.py`.
What stops proving: a P0/P1 thread of the Codex app no longer blocks the check or resolves by
the script. Catcher: none needed — Codex is not a reviewer; a repository that keeps the
Codex app installed gets advisory threads, like a person's today
(`test_human_priority_text_cannot_block_…`). The migration tells the person to uninstall it
or turn its reviews off.

**D4 — The Codex adapter leaves.** Removed: `.codex/hooks.json`, `codex_hooks.py`,
`agent_policy.py` (imported only by `codex_hooks.py`), `check_codex_project_trust.py`,
`.agents/skills/` (the Codex copy of the OpenSpec skills), their tests and
`TestCodexHookWiring`. What stops proving: that `git push origin main`, force push and
`gh pr merge` are denied by a hook (`test_codex_hooks.py`). Catcher: the Claude Code deny-list
of `.claude/settings.json`, which no test reads today; the new
`test_delivery_gate_wiring.py::test_claude_denies_push_to_main_force_push_and_merge` asserts
its rules for those three commands. It proves the configuration, not the platform's
enforcement — the same level the removed hook test reached for Codex's loading of
`.codex/hooks.json`. `hooks.py` and `navigation_policy.py` keep their behaviour; their
docstrings stop naming the Codex modules.

**D5 — The installer targets Claude only.** `_openspec` runs `openspec init --tools claude`;
`OPENSPEC_OUTPUT` loses its seven `.agents/` paths and keeps the twelve `.claude/` files and the three `openspec/` files. Observed 2026-09-27: `npx -y
@fission-ai/openspec@1.13.0 init --tools claude --no-animation` in a fresh git repository
exited 0 and wrote exactly `.claude/commands/opsx/{apply,archive,explore,propose,sync,update}.md`,
`.claude/skills/openspec-{apply-change,archive-change,explore,propose,sync-specs,update-change}/SKILL.md`,
`openspec/changes/archive/.gitkeep`, `openspec/config.yaml`, `openspec/specs/.gitkeep` — no
`.agents/` path. The link step, `Context.link` and the link conflicts (real directory, other
target, parent file) leave; what stops proving is only that the link is correct, and nothing
reads it any more. The checkout step stays: `--confirm` of another release hands off to the
checkout's `init.py`. Existing `.agents/skills/` in a consumer and `~/.agents/skills/agent-process`
are left untouched — the installer never deletes a file it no longer owns — and the migration
names them. The release-drift message names only the plugin update.
Alternative: remove the user-scope checkout and hand off from a temporary clone, as a dry-run
does. Rejected here: it changes the confirm path and its retry tests, a separate decision.

**D6 — One carrier in the tools.** `start_change.CARRIERS = ("Claude",)`, so argparse rejects
`Codex` with exit 2 before any read; the provenance line keeps its form. The schema's
`reviewer` enum becomes `["architect-reviewer"]`; no archived review uses `self-review`.

**D7 — The procedure names one carrier.** SKILL.md: the opening line; Group 0 names `--planner
Claude --implementer Claude` and no longer asks for the planner; Architect review drops the
self-review; Delivery drops `@codex review` and the fallback, stating that the `agent-review`
check reviews every head and `wait_for_pr.py` waits for it; step "re-request" leaves; the Install
paragraph drops the Codex skill and the temporary-clone route. REVIEW_CONTRACT.md,
AGENTS.md (the `Codex adapter` section leaves; `Code review` names the Claude review job),
the `openspec/config.yaml` context, and the docstrings of `wait_for_pr.py` and
`resolve_review_thread.py` follow.

**D7a — The `roles` Purpose is edited in place.** `openspec/specs/roles/spec.md` states its
Purpose as "which carrier fills each one in Claude Code and in Codex, and how two agents share
one procedure". Observed 2026-09-27: in a scratch repository, `npx -y @fission-ai/openspec@1.13.0
archive fix -y` of a delta carrying `## Purpose` plus a MODIFIED requirement printed
`~ 1 modified`, `Specs updated successfully.` and left the target spec's `## Purpose` line
unchanged — the pinned archive applies requirements only. A Purpose is no requirement, so no
delta can carry the correction; task 4.1 edits that one paragraph to "Which roles the process
has and which Claude Code entry point carries each one." in the same PR, where the review reads
it. The rule "never a direct edit of `openspec/specs/`" governs requirements, which stay
archive-only. The `review-and-merge` Purpose names no carrier and stays.

**D8 — ADR 0033 "Claude Code is the only carrier"** records the decision, D1–D5's lost proofs
and catchers, and supersedes the two-carrier decision of ADR 0027. ADR 0003 and 0015 already chain to 0027 (`superseded by`), and a status line names one target, so neither changes.

## Risks / Trade-offs

- [A caller still passes `codex-timeout-seconds`] → its run fails at startup. Only the
  publisher caller passes it, and this change edits it; the consumer caller passes no input
  and calls a release tag, whose callee keeps the input until the consumer upgrades.
- [The Claude review is now on the path of every head] → cost and time of one review per
  push, which the fallback already paid whenever Codex was silent.

## Migration Plan

Released with a breaking note (the callee input). A consumer: reruns `init` of the
release (which re-renders its review caller at the new tag), uninstalls the Codex GitHub app or turns its reviews off, and may delete
`.agents/skills/` and `~/.agents/skills/agent-process`. Rollback: revert the PR; the publisher
caller and callee return together because the caller calls `@main`.
