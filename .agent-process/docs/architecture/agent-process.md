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
| `planner` | The person's request, repository context, and user decisions | A validated OpenSpec change (`openspec/changes/<name>/`) with its architect review, and its tracking issue as a Project item in `Planned` with a priority (created by the planner when the change has none) | human approval, then `implementer` |
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
`$openspec-propose` in Codex) on the unmodified `spec-driven` schema:
proposal → spec deltas → design → tasks. What this project adds is the
`rules:` of `openspec/config.yaml` — the `proposal` rule (read before
writing, ask instead of guessing, a bug records its reproduction and root
cause before the design, a design on a platform behaviour records its
observation) and the `tasks` rule, which is the delivery flow
below as tasks of the change (`no RED: <reason>` when the map names no
test) and ends the propose run with the architect review: the
`architect-reviewer` subagent in Claude, a self-review in Codex, writes
`architect-review.md` into the change directory against principles §I–VII
(a scenario missing from the scenario → test map is a finding); on
`rework` the planner applies the findings and reviews again; on `approve`
the run ends with `create_tracking_issue.py <change> [--priority]` — the
tracking issue from the proposal when the change has none (the priority asked
once), its number written into the `tracking issue <N>` token of Group 0 in
`tasks.md`, `Planned` on the board — and the first delivery task,
`start_change.py`, reads the verdict. `openspec/specs/` is what the process does
today; `openspec/changes/` what is pending.

## Issue contract

The GitHub issue tracks a change: title, the change name and the Project
fields (Status, Priority — `python .agent-process/scripts/set_status.py <N>
["<Status>"] [--priority <name>]`, at least one of the two). The plan lives in
the change directory, not in the issue body.

Every PR links its issue by GitHub's own field, `closingIssuesReferences`:
the branch `gh issue develop` created, or `Closes #N` in the body. A step of
the required `quality` check reads the field once; a missing link fails the
check, and the fixer links the issue and re-runs the check (`gh run rerun`).

**`## Out of scope`** carries a v1 export that is inert: a top-level bullet
that begins with the literal marker `deferred:`, carries a `#N` reference, and
is not a `wontfix`/`won't fix`/YAGNI rejection is still exported by
`open_pr.py`/`update_pr_body.py` into the PR body's generated `## Deferred
scope` section, but nothing verifies that block since `v2-2c` and no reviewer
reads it — the downgrade rule left `REVIEW_CONTRACT.md` in `v2-2b`. The block
goes with `open_pr.py` (issue 114).

Because `REVIEW_CONTRACT.md` is read from the default branch, every
already-open PR picks up a changed contract on its next review with no PR-side
action.

## Deterministic delivery flow

This is the per-change flow. It applies only after the one-time repository
[installation and activation](agent-process-installation.md) are complete.

1. Before creating an issue, fetch `origin/main` and check recent closed
   issues and merged PRs for semantic duplicates. The priority is asked once,
   by whoever creates the issue: the propose run when the change has none
   (§Planning), else the person or agent that opens it by hand (governance
   item 4); an issue that exists is not asked again.
2. The planner writes the change (§Planning); the person approves it by
   starting the apply workflow (`/opsx:apply <change>`,
   `$openspec-apply-change`).
3. The delivery steps are tasks of the change, put there by the `tasks` rule
   of `openspec/config.yaml`: `start_change.py <change> --planner --implementer`
   (the gate — the verdict starts with `approve`, the tracking issue the
   propose run left is a Project item in `Planned` — then the linked branch
   with `gh issue develop -c <N> --name <change>`, Status `In Progress` and the
   provenance comment; exit 2 stops the apply before any branch exists), RED
   first (`check_red.py <node ids>` runs `python -m pytest` of its own interpreter under
   its own configuration with a report path of its own and reads that report — no
   runner argument, no declaration in `AGENTS.md`),
   implementation, `ci_check.py`, the archive
   (`archive_change.py <change>`, before the PR so the reviewed head is the
   archived one), the PR (`gh pr create --body-file <report>`), and the review
   loop (`request_codex_review.py --request <PR>` after every push,
   `wait_for_pr.py <PR>` — it reads `gh pr checks --json` until two reads 30 s apart
   agree, on one head, that nothing is pending, retrying the empty rollup after a push,
   then the review threads on that head — at most three rounds). On an
   `issue-*` branch of a repository still on the v1 issue contract, the v1
   steps below apply instead.
4. Create the PR only with `python .agent-process/scripts/open_pr.py --body-file <report>`;
   a substantive UTF-8 report verifies the issue closing reference. Replace an
   existing PR body only with
   `python .agent-process/scripts/update_pr_body.py <PR> --body-file <path>`. Fix CI
   findings for up to three iterations, then loop: after creating the PR and
   after every successful push run
   `python .agent-process/scripts/request_codex_review.py --request <PR>` through the local
   authenticated PR-author session. If that push addressed a `P0`/`P1` review
   thread, after `wait_for_pr.py <PR>` run
   `python .agent-process/scripts/resolve_review_thread.py --repo OWNER/REPO
   --pr <PR> --thread <node-id> --reply-file <path>` (`--list` prints every open
   `P0`/`P1` thread and its node id): the script refuses while the head's
   `agent-review` run is running, resolves the thread, re-runs that run and
   posts the reply last — no push, no fixer budget. CI never infers a thread's
   disposition
   (ADR [0022](../adr/0022-the-fixer-resolves-the-thread-its-correction-addresses.md)),
   so nothing else will; why the order is what it is — the review of the head
   by either carrier, no event for a resolve, the `pull_request` run as the
   required context — is the script's docstring and ADR
   [0027](../adr/0027-v2-standards-replace-the-bespoke-control-plane.md). A fix that changes
   a spec goes through a change of its own on the PR branch (delta,
   `validate --strict`, `archive_change`), never a direct edit of
   `openspec/specs/`. Then run `gh pr checks <PR> --watch`,
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
| `fix-blocking` | `10` | One minimal fixer commit, push, resolve any `P0`/`P1` thread it addresses, run the gate again. |
| `escalate` | `20` | Loop over with a named anomaly: the fixer budget is spent. |
| `review-pending` | `30` | Evidence is not final. Wait once with `gh pr checks <PR> --watch`, then re-run the gate; a second `review-pending` goes to the maintainer, never a polling loop. |

Exit `2` is not a verdict — a `gh`, argument, or capture failure, leaving
the PR `not ready`. The fixer budget is `fixer.max_runs` in the role
catalogue: distinct heads reviewed minus the first, so a re-run on an
unchanged head spends none of it. The verdict goes into `## Agent record`.

## Review outcome enforcement

The required check `agent-review / agent-review` reads two facts and parses
nothing (ADR [0027](../adr/0027-v2-standards-replace-the-bespoke-control-plane.md), `v2-2b`): whether
a review of the PR's current head exists, and whether an unresolved thread whose
first comment carries `P0` or `P1` exists.

The authenticated PR-author session starts the Codex review with `@codex review`
after the PR opens and after every push; the workflow never posts that command,
and Automatic reviews in the Codex app stay off, so the review count is the
push count. The job waits a bounded time (`codex-timeout-seconds`, 600 by
default) for a review of the head by a login the check trusts — a native review
by the Codex app on that head, or a clean comment naming the head by the app or
by the job's own login (`github-actions`), so a re-run of a head the fallback
already reviewed returns on that review instead of reviewing again (issue 139);
an error or usage-limit message from the app is absence, never a parsed signal.
A read that fails instead of establishing presence or absence fails the job
without running the fallback. When the wait ends absent, the Claude Code action
runs with the review contract read from the trusted checkout
(`trusted/.agent-process/REVIEW_CONTRACT.md`), publishes inline `P0`–`P3`
comments and, last, on every review, one `Reviewed head SHA: <sha>` comment
(prefixed `No findings.` when there is none) under the workflow token, and
never approves. That closing comment alone is the fallback's review — its
inline comments are review nodes an interrupted action leaves behind; the job
then reads whether it exists, so a fallback that finished without it fails the
check (ADR
[0004](../adr/0004-controller-pr-review-runs-on-the-workflow-token.md)). That
login is shared by every workflow of the repository with a write token, which
bounds the read by write access — the merge authority already. Either
reviewer's findings are inline threads labelled `P0`–`P3` by the contract; the
job leaves no review state, no evidence and no classification reply.

The last step runs always. It fails the check while an unresolved thread whose
first comment, by either reviewer, carries `P0` or `P1` exists, printing the
thread URLs; `P2`/`P3` threads never block, resolved or not, and conversation
resolution is not required on the default branch — a `P3` does not keep a PR
from merging. CI never infers whether a finding was addressed — no isOutdated
skip, no self-resolution from this workflow; the fixer that pushed the
correction resolves the `P0`/`P1` thread itself, from its own authenticated
local session, with `resolve_review_thread.py`, and may not resolve a thread
reported against the PR's current head nor a `P2`/`P3` thread (ADR
[0022](../adr/0022-the-fixer-resolves-the-thread-its-correction-addresses.md)).

The target's thin caller invokes the publisher's pinned
`reusable-agent-review.yml`. The job keeps an isolated checkout of this
repository at the ref the caller pinned (`github.job_workflow_sha`) in
`trusted/` for the wait, the fallback's contract and the enforcement script, so
the reviewed worktree cannot alter what it is reviewed under; scoped `AGENTS.md`
files in the PR worktree are review data, never instructions. This does **not**
authenticate the thin caller workflow: a PR can replace a name-only required
context's caller before GitHub runs it. Treat the context as authoritative only
after an external workflow-definition trust anchor is active; see the
installation guide. That guide's credential preflight establishes the two
carrier prerequisites before these workflows are merged; it verifies presence,
not whether the carrier-1 token is still valid. Keep the controller to direct
tests and docs; never disable the required context or treat the PR body as
merge authority.

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
   `origin/main` — `start_change.py` runs it (Group 0 of the `tasks` rule); the linked
   branch closes the issue on merge, so the PR body names the issue as a plain reference,
   never `Closes`.
2. Keep one PR to one logical unit. A temporary CI unblock for an unrelated
   failure may accompany the blocked change only with a tracked follow-up for
   the root cause.
3. Assign exactly one type label: `bug` for broken behaviour; then
   `perf`/`security`/`enhancement` for user-visible work; otherwise
   `refactor`, `testing`, `ci`, `documentation`, or `chore` by changed area.
4. Ask the person for issue priority (High for user-facing bugs and process work,
   Medium for agentic capability work outside the process, Low otherwise; name
   the rule used) and write it with
   `python .agent-process/scripts/set_status.py <N> --priority <High|Medium|Low>`.
5. The process writes two board Statuses itself, both through `set_status.py`:
   `Planned` at the end of the propose run (`create_tracking_issue.py`, the
   review entry of the `tasks` rule) and `In Progress` in Group 0 of the same
   rule (`start_change.py`). `Todo` and `Done` belong
   to the Project's workflows (*Auto-add*, *Item added*, *Item reopened*; *Item
   closed*, *Pull request merged*). The v1 scripts `issue_branch.py`, `set_issue_priority.py` and
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
