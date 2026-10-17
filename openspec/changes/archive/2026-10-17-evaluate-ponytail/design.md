## Context

Ponytail at the pinned release v5.3.2 (tag `v5.3.2` → `16352ac229eb08a9598dcae48fe9f2b342567d86`,
published 2026-10-16; 14 releases since 2026-09-14) is a Claude Code plugin. It has the
`ponytail` skill and five more (`-review`, `-audit`, `-debt`, `-gain`, `-help`), plus Node
hooks on `SessionStart`, `SubagentStart` and `UserPromptSubmit` that inject the ruleset into
every session and every subagent. Its `ledger` option is on by default and writes one row per
turn to `~/.config/ponytail/band/<project>.csv`. The webhook is empty by default
(`.claude-plugin/plugin.json`).

Comparison with the current rules (acceptance criterion 1):

| Ponytail rule (`skills/ponytail/SKILL.md`) | Process rule | Relation |
| --- | --- | --- |
| Ladder: need → codebase → stdlib/platform → installed dependency → one line → minimum code | §VII; "Scripts over instructions" (standard tool first); `## Standard approach`; the review's `bespoke` class | Overlap |
| "Never add a dependency for a few lines" | §VII "ask before adding a dependency" | Compatible, §VII is stricter |
| Non-trivial logic "leaves one small test"; trivial changes need none | §I: every behavioural change starts with a failing test | Conflict: test after code and fewer tests |
| `shortcut: <the limit>, <when to upgrade>` code comment | §V: no workaround until the cause is named or a mitigation links its issue | Conflict: the comment does not link an issue |
| Bug fix: grep every caller, fix the root cause once | §V | Overlap |
| `ultra` questions the request | Proposal: ask the person when a scope decision is theirs | Overlap |
| `ponytail-review`, `ponytail-audit` | `/simplify`, the architect review | Overlap |
| Hooks inject the ruleset every session and subagent | Goal 2 (runtime tokens; ADR 0043 weighed about 600 tokens for `always-on.md`) | Cost to measure |
| `ponytail-subagent.js` swallows its errors ("Silent fail") | §IV | Conflict: a failed hook leaves a session without Ponytail, and nothing shows it |
| Per-turn ledger outside the repository | Task readings in the repository's own stack (ADR 0041) | Overlap |
| Node runtime for the hooks | §VII: a new dependency needs the person's approval | Cost on adoption |

The overlap leaves the pilot one question: does Ponytail change what the process delivers
when §VII and the review already apply?

## Goals / Non-Goals

**Goals:** a decision recorded in an ADR and on tracking issue 9, from the paper gate and,
when that passes, pilot readings.

**Non-Goals:** shipping Ponytail to consumers before the decision; code size alone as a
quality metric; a new script, script option or eval harness for the pilot.

## Decisions

### 1. Historical arm A, one new arm B per task

Arm A is a recently merged change delivered without Ponytail: its PR, its archived
`architect-review.json` and `sessions`, and its transcripts. Arm B runs the same task once with
Ponytail: `/opsx:propose` → `/opsx:apply` to a settled PR, from A's base (the parent of A's
`chore: plan <change>` commit), in A's session structure (one session or one per phase, as
A's `sessions` file and transcripts show), in the CLI with `--model claude-opus-5-5`, A's model.

A task qualifies when its PR changes code with tests and its transcripts are still on disk
with `claude-opus-5-5`. Proposed: per-task-rates (#448) and planning-standard-first (#454), both
reviewed under the current `agent-review` contract; prune-merged-branches (#440), reviewed under
an earlier one (decision 3), is the fallback. The person confirms or swaps them.

Departures from the standard approach (Ponytail's agentic benchmark): one run per cell
instead of five, no hidden checks, and a past baseline instead of an interleaved run. In their
place come the process's own readings, which the benchmark lacks, at half the delivery cost of
a paired run. With n = 2 the readings are indicative, and the ADR states that limit.
`claude plugin eval` has the same baseline arm (tracking issue 298 records it), but it grades a
transcript and opens no PR, so architect-review, `agent-review` and CI readings would be
missing.

### 2. Arm B setup

Per task, with the person's confirmation:

- `pilot-base/<slug>`, a remote branch at A's base. B's PR targets it, so CI and `agent-review`
  (`pull_request` without a branch filter) run without A's change; a PR to `main` would
  conflict with it. A temporary ruleset on `refs/heads/pilot-base/**` carries `main`'s
  pull-request rule (one approval) and its required checks (`agent-process / quality`,
  `agent-review / agent-review`, `pr-title`) and no deletion rule, so `wait_for_pr` waits for
  `agent-review`, nothing merges B's PR, and the cleanup can delete the branch. It is
  deleted with the last `pilot-base/<slug>`.
- A pilot tracking issue with A's issue title and body, without its comments, so B neither
  reads A's provenance nor shares A's `sessions` lines.
- A detached worktree at A's base, where B's propose runs: its `skills/agent-process/scripts/`
  win over the plugin's copy (`bin/agent-process`), so B runs A's process scripts.
- Before B's apply, `git config branch.<slug>-pilot.gh-merge-base pilot-base/<slug>` and
  `gh issue develop <pilot issue> --name <slug>-pilot --base pilot-base/<slug>`. B's
  `start_change` then links that branch or names the steps left (its documented path), and B
  finishes them. B's plan commit must have A's base as its parent; a mismatch is recorded.

Ponytail loads only into B sessions, through `claude --plugin-dir <ponytail checkout>`, where
the CLI help reads "Load a plugin from a directory or .zip for this session only". That
reaches the planner, the `architect-reviewer` subagent (the `SubagentStart` hook) and the
implementer, so the pilot measures "both" roles. The checkout is `git clone --depth 1 --branch
v5.3.2` into its own empty directory outside the repository, and its `plugin.json` must read
`5.3.2`. The mode is `full`, the default. The ledger stays at its default and writes only a
local file, which is deleted after the pilot. The webhook stays empty, so nothing leaves the
machine.

The hook fails silently (§IV), so loading is checked after the fact: each B transcript, and
each of its `subagents/*.jsonl`, must hold the ruleset's opening line "You are a lazy senior
developer". A B session without it is rerun. A's result stays reachable through `origin/main`
and `gh`; a B transcript naming A's PR (`pull/<A PR>`) or A's archive path is recorded as a
leak and the ADR weighs it.

### 3. Readings per arm

The `task-readings` columns of `telemetry-measurement-setup.md` ("Per-task readings"), by its
gap and zero-versus-missing rules, taken by hand for both arms with the window ending at the
head `wait_for_pr` settled, because `task_readings.py` refuses B's unmerged PR and A's row ends
at `merged_at`. Added on top, from the issue: changed files, added dependencies and scripts
(`gh pr diff`), the architect-review and `agent-review` findings by severity, and the CI
conclusion (`gh pr checks`). For the §I and §V conflicts, which `agent-review` does not flag
(`REVIEW_CONTRACT.md` asks for a missing test, not a late one), three more: whether the RED
commit (or the `no RED:` task) precedes the first implementation commit (`gh pr view --json
commits`), the number of test functions the PR adds, and each `shortcut:` comment in the diff
with whether it links an issue.

A's readings are taken before any B run: Grafana keeps about 14 days of samples
(`telemetry-measurement-setup.md`), counted from A's sessions.

The arms differ beyond Ponytail: the Claude Code build (A's transcripts record it), the
`agent-process` plugin's own hooks (user scope, newer than A's base), the person's
interventions (user turns per session), merges of `main` into A's branch mid-delivery, and the
reviewer: `agent-review` runs `reusable-agent-review.yml@main` with no pinned model, so the
diff of `REVIEW_CONTRACT.md` and that workflow between A's merge and B's settle, and each
run's model from its log, are recorded. Each is a reading, not a control; the ADR weighs them.

B's PR is never merged. The person closes it after the readings and says whether they would
have merged B instead of A; that verdict is a reading.

### 4. Paper gate, then the pre-registered rule

Before any setup, each Context conflict needs a resolution with no edit of Ponytail's ruleset:
§I and §V take precedence over Ponytail's rule; the silent hook is covered by decision 2's
check and stays a named risk of an optional plugin. The ledger overlap is closed on adoption
by `ledger=false`. A
conflict without one decides "not planned", and the pilot is skipped.

Adopt as an optional plugin only if, in each task run, arm B has no more P0/P1 `agent-review`
findings and no more architect-review rounds than A, has green CI, keeps RED first, adds no
fewer tests, leaves no `shortcut:` comment without an issue, and costs less or changes fewer
lines. Arm B's architect reviewer also runs under Ponytail (the `SubagentStart` hook), so its
rounds are a judgement from inside the arm. The ADR names this limit. When task 1 fails this, task 2 cannot change the outcome and is not run.
Otherwise the decision is "not planned".

Adoption names the pinned tag, the install path (the marketplace `ref` pinned to that tag,
`claude plugin install ponytail@<marketplace> --scope user --config ledger=false`) and the
rollback (`claude plugin uninstall ponytail@<marketplace>`). The pin follows the observation
on record in the skill's `## Install`: "the `ref` in `.claude/settings.json` does not re-point a
marketplace the machine already knows".

## Risks / Trade-offs

- One delivery per pilot task → at most two tasks, the paper gate first, and the stop after
  task 1.
- A past baseline → the differing build, hooks and interventions are readings, and the leak
  grep of decision 2 shows whether B saw A's result.

## Migration Plan

Pilot rollback: delete the Ponytail checkout, its ledger file and the base worktrees; close B's
PRs and pilot issues as not planned; delete `pilot-base/<slug>` and the pilot ruleset with the
person's confirmation.
Adoption rollback: revert the Install row; a consumer runs decision 4's uninstall.
