# Agent development process

**Question this document answers:** How roles, artifacts, gates, and adapters
work together when planning and implementation use different agents.

This document is the canonical, agent-neutral development process. An agent is
an implementation detail; a role is a contract. The current default adapters
are Claude for `planner` and `reviewer`, and Codex for `implementer` and
`fixer`, but any adapter that satisfies the contract may be substituted.

## Roles and hand-offs

| Role | Required input | Required result | Next role |
| --- | --- | --- | --- |
| `planner` | The person's request, repository context, and user decisions | A validated OpenSpec change (`openspec/changes/<name>/`) with its architect review; the tracking issue is created by the first delivery task when absent | human approval, then `implementer` |
| `implementer` | The approved change | Focused branch, RED evidence, implementation, docs, PR; the change archived on the PR | `reviewer` |
| `reviewer` | Plan, diff, and checks | Visible, actionable findings or an explicit clean result | `fixer` or human |
| `fixer` | Review or CI finding | Minimal correction with passing relevant checks | `reviewer` or human |

The artifact, not an agent report, authorizes a hand-off. A plan is the change
directory (`openspec validate --strict` is the only automated check on it; the
person approves by running the apply command); an implementer must use
`python .agent-process/scripts/check_red.py` for RED and
`python .agent-process/scripts/ci_check.py` before delivery. GitHub branch
protection and required checks are the final delivery gate.

## Planning

Planning is the OpenSpec propose workflow (`/opsx:propose` in Claude Code,
`$openspec-propose` in Codex) with the `agent-process` schema
(`openspec/schemas/agent-process/`): proposal → spec deltas → design →
tasks → architect review, the last artifact before the person approves
(`apply` requires both). What this project adds to every artifact is the
`rules:` of `openspec/config.yaml` — the `proposal` rule (read before
writing, ask instead of guessing, a bug records its reproduction and root
cause before the design), the `architect-review` rule (principles §I–VII;
a scenario missing from the scenario → test map is a finding) and the
`tasks` rule, which is the delivery flow below as tasks of the change
(`no RED: <reason>` when the map names no test). `openspec/specs/` is what the
process does today; `openspec/changes/` what is pending.

## Issue contract

The GitHub issue tracks a change: title, the change name and the Project
fields (Status, Priority — `python .agent-process/scripts/set_status.py <N>
"<Status>" [--priority <name>]`). The plan lives in the change directory,
not in the issue body.

**`## Out of scope`** is machine-read on the delivery PR, not prose-only: a
top-level bullet that begins with the literal marker `deferred:`, carries a
`#N` reference, and is not a `wontfix`/`won't fix`/YAGNI rejection is exported
by `open_pr.py`/`update_pr_body.py` into the PR body's generated
`## Deferred scope` section, which the required `pr-link` check verifies
against this issue and which `REVIEW_CONTRACT.md` lets a reviewer use to
downgrade a matching finding by one severity step (ADR 0020). The `#N` must
sit on the **top-level** bullet — `check_orphan_scope.top_level_bullets`
cannot see one nested under it. An issue number mentioned without the
`deferred:` prefix is never exported; opting in is a deliberate marker, not
something a bullet triggers by accident.

Because both `REVIEW_CONTRACT.md` and the `pr-link` driver are read from the
default branch, every already-open PR picks up the new downgrade rule on its
next review and the new soundness check on its next `pull_request` event with
no PR-side action. If that check reds on an already-open PR (its generated
block is stale against an edited issue), the recovery is one re-run of
`python .agent-process/scripts/open_pr.py` (or `update_pr_body.py` for a
fixer's report update) to regenerate the block.

## Deterministic delivery flow

This is the per-change flow. It applies only after the one-time repository
[installation and activation](agent-process-installation.md) are complete.

1. Before creating an issue, fetch `origin/main` and check recent closed
   issues and merged PRs for semantic duplicates. Ask the user for priority.
2. The planner writes the change (§Planning); the person approves it by
   starting the apply workflow (`/opsx:apply <change>`,
   `$openspec-apply-change`).
3. The delivery steps are tasks of the change, put there by the `tasks` rule
   of `openspec/config.yaml`: tracking issue and priority, the linked branch
   (`gh issue develop -c <N> --name <change>`), Status `In Progress`, RED
   first (`check_red.py`), implementation, `ci_check.py`, the archive
   (`archive_change.py <change>`, before the PR so the reviewed head is the
   archived one), the PR (`gh pr create --body-file <report>`), and the review
   loop (`request_codex_review.py --request <PR>` after every push,
   `wait_for_pr.py <PR>`, at most three rounds). On an
   `issue-*` branch of a repository still on the v1 issue contract, the v1
   steps below apply instead.
4. Create the PR only with `python .agent-process/scripts/open_pr.py --body-file <report>`;
   a substantive UTF-8 report verifies the issue closing reference. Replace an
   existing PR body only with
   `python .agent-process/scripts/update_pr_body.py <PR> --body-file <path>`. Fix CI
   findings for up to three iterations, then loop: after creating the PR and
   after every successful push run
   `python .agent-process/scripts/request_codex_review.py --request <PR>` through the local
   authenticated PR-author session. If that push addressed a BLOCKING review
   thread, resolve it now — before the `agent-review` run on this head reaches
   its last step — with `python .agent-process/scripts/resolve_review_thread.py
   --repo OWNER/REPO --pr <PR> --thread <node-id>` (`--list` prints every open
   BLOCKING thread and its node id); CI never infers a thread's disposition
   (ADR [0022](../adr/0022-the-fixer-resolves-the-thread-its-correction-addresses.md)),
   so nothing else will. Resolving after that run has already read a red check
   on this head is a no-op — if the window is missed, re-run the completed
   `agent-review` run on the unchanged head instead of pushing again, spending
   no fixer budget. Then run `gh pr checks <PR> --watch`,
   inspect a failed run with
   `gh run view <run-id> --log-failed`, and ask
   `python .agent-process/scripts/review_gate.py <PR>` whether to continue — its verdict
   decides, not the agent's own reading. `should-fix` findings are the
   maintainer's call and don't gate the loop. A PR is ready once the
   current head has no blocking finding and every required check passes.

A delivery is **terminal** once `review_gate.py` reaches `ready-for-human` or
`escalate` on the current head; every other state — no CI stamp, no PR yet, a
`fix-blocking`/`review-pending`/capture-failure verdict, or a verdict recorded
against an older head — is progress, not a stopping point. A turn-boundary gate
enforces this instead of the agent's own reading of the loop: on an issue
branch, the end of an agent turn is a gated event (ADR
[0021](../adr/0021-the-end-of-an-agent-turn-is-a-gated-event.md)), blocking the
turn while the delivery is non-terminal and naming the exact next command,
bounded so an unchanged state escalates with a visible marker rather than
trapping the session. Both carriers wire this to their `Stop` hook
(`hooks.py stop`, `.agent-process/scripts/delivery_state.py`): Claude via
`.claude/settings.json`, Codex via `.codex/hooks.json`'s `Stop` group
(`codex_hooks.py stop`). Codex only loads `.codex/hooks.json` for a project
the operator has recorded as trusted; confirm that with
`check_codex_project_trust.py` per
[the installation guide](agent-process-installation.md#installation-order)
before relying on this gate on the Codex adapter — that preflight covers
project trust only, and Codex separately requires per-hook trust before it
will run one, which the installation guide's hook-trust note covers.

One PR is one logical unit. Do not bypass hooks, push to `main`, force-push,
reset hard, delete branches forcefully, self-merge, or replace these gates
with an agent assertion. GitHub branch protection is authoritative; a
review check that is skipped, missing, malformed, or still pending leaves
the PR `not ready`.

### Review-gate verdicts

`python .agent-process/scripts/review_gate.py <PR>` reads the live PR — required contexts on
the current head, and how many distinct heads `agent-review` has reviewed. It
records its verdict for the judged head to `.review_gate_stamp`, for the
turn-boundary gate above to read, but changes nothing and posts nothing **on
the PR**.

| Verdict | Exit code | Meaning |
| --- | --- | --- |
| `ready-for-human` | `0` | Loop over. Report the PR ready; remaining findings are the maintainer's call. |
| `fix-blocking` | `10` | One minimal fixer commit, push, resolve any BLOCKING thread it addresses, run the gate again. |
| `escalate` | `20` | Loop over with a named anomaly: the fixer budget is spent. |
| `review-pending` | `30` | Evidence is not final. Wait once with `gh pr checks <PR> --watch`, then re-run the gate; a second `review-pending` goes to the maintainer, never a polling loop. |

Exit `2` is not a verdict — a `gh`, argument, or capture failure, leaving
the PR `not ready`. The fixer budget is `fixer.max_runs` in the role
catalogue: distinct heads reviewed minus the first, so a re-run on an
unchanged head spends none of it. The verdict goes into `## Agent record`.

## Review outcome enforcement

`clean` and `rework` outcomes pass; `blocking`, empty, or malformed outcomes
red the check. The workflow replies to every Codex finding with the user-facing
merge class **BLOCKING** or **NON-BLOCKING**. An open BLOCKING conversation
independently fails the same required check until it is resolved; an open
NON-BLOCKING conversation is advisory. CI never infers whether a finding was
addressed — no isOutdated skip, no self-resolution from this workflow; the
fixer that pushed the correction resolves the thread itself, from its own
authenticated local session, with `resolve_review_thread.py`, and may not
resolve a thread reported against the PR's current head (ADR
[0022](../adr/0022-the-fixer-resolves-the-thread-its-correction-addresses.md)). A valid result has an explicit empty
finding list for `clean`, or one or more severity-, confidence-, and
summary-bearing findings for `rework` or `blocking`; the workflow writes that
validated evidence and the reviewed head SHA to its check summary. When the
Claude fallback carrier is the one that ran, that same validated evidence is
also published as a plain PR-conversation comment — never a review state —
so a fallback verdict is not visible only in the Actions run summary; the
Codex primary path is unchanged, since it already leaves its own native
review. A present-but-invalid Claude fallback payload (output that arrived but
does not fit the schema above) still reds the check, but is not silently
dropped either: it publishes an explicitly **unvalidated** block — a
human-readable rejection reason, the reviewed head SHA, a run pointer, and a
best-effort render of whatever fields the payload does contain — through the
same two surfaces, so a schema violation stays inspectable instead of visible
only in the raw Actions job log. It never authorizes a merge. A collision on
one head SHA in the sticky PR comment resolves by precedence, not equality: a
validated block always replaces an unvalidated one for that head, and an
unvalidated block never overwrites a validated one. Once the
reusable review workflow is invoked, it reads its
verifier from the default branch and current PR body/head from the live API, so
the reviewed worktree cannot alter its own verifier. This does **not**
authenticate the thin caller workflow: a PR can replace a name-only required
context's caller before GitHub runs it. Treat the context as authoritative only
after an external workflow-definition trust anchor is active; see the
installation guide. That guide's credential preflight establishes the two
carrier prerequisites before these workflows are merged; it verifies presence,
not whether the carrier-1 token is still valid. Keep the controller to direct
tests and docs; never disable the required context or treat the PR body as
merge authority.

The target's thin caller invokes the publisher's pinned
`reusable-agent-review.yml`. The authenticated PR-author session starts the
Codex primary with `@codex review`; the workflow never posts that command or
enables Automatic reviews. It waits for Codex's normal GitHub review on the
current head, then translates the integration's native P0/P1/P2/P3 metadata into the gate outcome
and adds the plain-language merge-class reply. When Codex
leaves no valid evidence, Claude runs as the structured-output fallback. A
valid verdict from either carrier is final for that head; changing agent-process
policy files does not require both carriers.
The workflow keeps an isolated checkout of the publisher's default branch in
`trusted/` for the adapter, evidence validator, and enforcement script, while
the adapter reads the standard review from the PR's live GitHub API records.
The Claude fallback reads both `trusted/AGENTS.md` and
`trusted/REVIEW_CONTRACT.md`; scoped `AGENTS.md` files in the PR worktree are
reviewed as untrusted data and cannot redefine fallback policy.
The one transition PR that introduces this adapter uses a visible bootstrap
fallback when the default branch lacks its parser marker; its evidence is still
validated by the default-branch validator. The manual owner request is review
evidence, not a replacement for the platform workflow-definition trust anchor.

## Test suite ownership

Every process-related test is either **publisher-only** or **consumer**, by one
reviewable rule: publisher-only when it proves the template source, a reusable
workflow, publication, self-application, or generic implementation behaviour;
consumer only when it proves a rendered answer or a contract that depends on
the target repository's own files, configuration, or local integration. A
copied production script is not by itself justification for copying all of
its publisher unit tests.

Publisher-only tests live under `tests/publisher/`; consumer tests live under the
reserved `tests/agent_process/` subtree — the only path a process test may occupy
in a consumer's `tests/` root.

Run either suite independently — `python -m pytest tests/publisher` or
`python -m pytest tests/agent_process` — or both together with the documented
full command, `python -m pytest` (also what `python .agent-process/scripts/ci_check.py`
runs).

## Governance conventions

1. Create issue branches only with `gh issue develop -c <N> --name <change>` from fresh
   `origin/main` (Group 0 of the `tasks` rule); the linked branch closes the issue on
   merge, so the PR body names the issue as a plain reference, never `Closes`.
2. Keep one PR to one logical unit. A temporary CI unblock for an unrelated
   failure may accompany the blocked change only with a tracked follow-up for
   the root cause.
3. Assign exactly one type label: `bug` for broken behaviour; then
   `perf`/`security`/`enhancement` for user-visible work; otherwise
   `refactor`, `testing`, `ci`, `documentation`, or `chore` by changed area.
4. Ask the person for issue priority (High for user-facing bugs and process work,
   Medium for agentic capability work outside the process, Low otherwise; name
   the rule used) and write it with
   `python .agent-process/scripts/set_status.py <N> "<status>" --priority <High|Medium|Low>`.
5. The process writes one board Status itself: `In Progress`, from `set_status.py`
   in Group 0 of the `tasks` rule. `Todo` and `Done` belong to the built-in Project
   automations. The v1 scripts `issue_branch.py`, `set_issue_priority.py` and
   `set_issue_status.py` are not part of the delivery flow; they go with the
   control plane in `v2-4`/`v2-5`.
6. If a `requirements*.in` file changes, run `pip-compile` for its matching
   lockfile in the same commit.
7. Trivial non-behavioural one-line changes may skip the issue workflow only
   with explicit rationale recorded in the issue or PR.

## Agent records and adapters

The PR template records implementer/reviewer, CI evidence, route, invocation
counts, fixer revisions, and skips/escalations. `roles.yaml` is the catalogue;
`python .agent-process/scripts/agent_orchestrator.py <state.json>` is read-only advice, never
authorization: it does not replace deterministic CI or branch protection. Its default route is discovery → planner → architect review →
implementer → CI → PR review → fixer → human merge; an exhausted cap escalates.
Copy `.agents/orchestration/state.example.json` for a local decision.

### Control-plane output contract

The CLI prints one JSON object with the resolved role/status, missing and
completed evidence, adapter/action, route, and canonical contract pointer.

| Role | Max runs | Scope |
| --- | --- | --- |
| `discovery` | 2 | per issue; the second run is the retry after a failed capture |
| `planner` | 1 | per issue |
| `architect_reviewer` | 1 | per issue |
| `implementer` | 1 | per issue |
| `pr_reviewer` | 1 | per head SHA, enforced by `reviewed_heads` |
| `fixer` | 3 | per PR review/fix loop |
| `human_merge` | 1 | terminal hand-off; descriptive, not a retry counter |

An adapter supplies only a role's interface and permissions; the contract stays
here. The catalogue declares entry points, files, route mapping, and fallback.
`run_route` is chosen by the human, `ci_failover` by the workflow, and `sole`
by nobody; unknown or unavailable routes fail visibly. To add an agent, point
its adapter here, record its role, and pass the same issue, RED, CI, PR-link,
and branch-protection gates — do not fork the workflow or issue schema.
