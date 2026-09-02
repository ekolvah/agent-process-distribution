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
| `discovery` | Bug issue with an unaccepted `## Evidence` block | Captured fixture in the working tree and an `## Evidence` block the `--evidence-only` gate accepts | `planner` |
| `planner` | Issue, repository context, and user decisions | Complete issue body, architect-review decision, passing issue validator | `implementer` |
| `implementer` | Passing issue body | Focused branch, RED evidence, implementation, docs, PR | `reviewer` |
| `reviewer` | Plan, diff, and checks | Visible, actionable findings or an explicit clean result | `fixer` or human |
| `fixer` | Review or CI finding | Minimal correction with passing relevant checks | `reviewer` or human |

The artifact, not an agent report, authorizes a hand-off. A planner must run
`python .agent-process/scripts/validate_issue_sections.py <N>` successfully; an implementer
must use `python .agent-process/scripts/check_red.py` for RED and `python .agent-process/scripts/ci_check.py`
before delivery. GitHub branch protection and required checks are the final
delivery gate.

## Issue contract

Substantive features and fixes start from a GitHub Issue. The nine base
headings are defined only by `REQUIRED_SECTIONS` in
`.agent-process/scripts/validate_issue_sections.py`:

1. Context / Why
2. Acceptance criteria
3. Test plan
4. Implementation outline
5. Docs to update
6. Out of scope
7. Architect review
8. ADR
9. Agent handoff

Which sections an issue must carry is **per-change-class data**:
`.agents/orchestration/change-classes.yaml` holds one row per type label,
declaring what that class `adds`/`omits` — a new class is a data edit, not
another branch inside `validate_issue_sections.py`. `bug` adds `Evidence`;
every other label adds `Prior art`. An architect review is required whenever
`Architect review` is in the resolved set, and RED whenever `Test plan` is —
both derived, never stored separately.

Exactly one type label is a gate: zero or several is a gap the **maintainer**
fixes with `gh issue edit <N> --add-label <type>` — a planner may not change
labels (§Planner runbook).

| Type label | Adds |
| --- | --- |
| `bug` | `Evidence` |
| `chore`, `ci`, `documentation`, `enhancement`, `perf`, `refactor`, `security`, `testing` | `Prior art` |

The validator derives the required set from that single type label. A change
class is catalogue data rather than a branch an agent has to remember, and a
passing issue reports whether RED and architect review are required.

**`## Evidence`** (added by `bug`) records a completed observation of the
external system, used when the plan describes how to read, parse, or classify
external data:

```md
discovery: <carrier declared for the `discovery` role in roles.yaml>
capture: `<source-specific reproducible command that writes the path below>`
path: `<repository-relative path>`
observed: <the source fact that explains the reported failure>
preserve: <the exact valid record from the same captured response that must keep working>
change: <the exact invalid record from that captured response whose behaviour must change>
boundaries: <candidate fix boundaries compared, from broad to narrow>
collateral: <whether each candidate preserves or loses that exact valid record>
reuse: <current production path traced to the existing input/fetch usable by the narrow boundary>
paired-test: <the same captured input through one pipeline run keeps the valid record and rejects the invalid record>
```

The first non-empty line is the provenance marker, resolved against
`.agents/orchestration/roles.yaml`. The capture command must write the exact
path named next, under `evidence/issue-<N>/` — working-tree-only,
Git-ignored, kept locally only until merge; the issue keeps a verified,
safe, compressed record, never the full payload.

The remaining fields make the capture a reviewable design decision: a
sibling feed, query, or source does not count as preservation, and a
candidate that loses the preserved record is BLOCKING unless the issue
records an explicit product decision authorizing the loss. Use the
narrowest read-only route below; never run a full pipeline merely to
collect evidence:

| Source | Capture route |
| --- | --- |
| Project-specific source | `<project's own read-only capture command>` |
| GitHub REST | `python .agent-process/scripts/capture_external_fixture.py github <endpoint> <path> --confirm-repository-safe` |
| Another source with a read-only CLI | `<read-only command> | python .agent-process/scripts/capture_external_fixture.py stdin <path> --confirm-repository-safe` |

The safety flag is a claim, not a sanitizer — inspect the payload and never
commit credentials or private data; each route reads without a write, a
send, or a full pipeline run.

The paired test must send the same captured input through one pipeline run and
prove that the valid record remains while the invalid record changes. Before
claiming that a narrow boundary needs a new fetch, trace the current production
path. The validator checks the command, safe path, record fields, and failed
capture output; it does not prove the source fact itself.

If no safe read-only route exists, do not improvise with a side-effecting
production entry point. A failed capture records `status: failed` with a
non-empty `output:` block; the plan stays blocked and no implementer
handoff may be recorded.

Captured bytes join `tests/fixtures/` only when a production-behaviour
regression test reads them in the same commit. For a bug with no
external-system behaviour, the fields above become `n/a: <reason>` — a
discovery **verdict**, not a silently skipped step.

**`## Prior art`** (added by every other class) records the search **outside**
this repository — the maintained library, tool, or upstream feature that may
already solve the problem — in three lines:

```md
searched: <where you looked: the queries, and the repository paths you compared them against>
candidates: <what exists, each one named and linked>
verdict: reuse|build — <why, in one sentence>
```

`verdict:` is red unless it starts with `reuse` or `build`; prose after
that word is free. The gate never judges whether the verdict is *right*.
`n/a: <reason>` is valid for a change with no ecosystem to search — abusing
the branch is a nameable architect-review finding.

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

`Test plan` names executable test nodes. `Architect review` opens with a
provenance line — `reviewer: <carrier>` or `skipped: <reason>` — followed by
findings; `ADR` contains a record link or `none: <reason>`. `Agent handoff` is
concise provenance, all four fields:

```md
planner: <agent name> [<model/version if known>]
validation: `python .agent-process/scripts/validate_issue_sections.py <N>` — passed
next role: implementer
handoff: ready
```

Do not store prompts, transcripts, secrets, or private reasoning in the
issue. `validation: passed` is not authorization by itself — every
implementer re-runs the validator. An implementer that finds `Agent
handoff`, `Evidence`, or `Prior art` missing stops and returns the issue to
a planner rather than guessing.

## Discovery runbook

Discovery runs before planning for a bug whose Evidence is unaccepted. It
returns the Evidence block to the planner, who records it in the issue, so the
producer of an observation does not also publish it. It may
use only the read-only routes above and write a working-tree fixture; it may
not edit the issue, branch, or production code. Observe the live system and
fill the Evidence fields (or record `n/a: <reason>`); retry one failed capture,
then escalate. Validate the block with
`python .agent-process/scripts/validate_issue_sections.py <N> --evidence-only --body-file <path>`.
The fixture stays untracked unless the RED test reads it. `discovery: <carrier>`
is attribution, not proof: a declared carrier can be questioned, but the gate
cannot distinguish a fabricated observation from an honest one.

## Planner runbook

These steps belong to the `planner` role, not to an adapter; an adapter adds
only its own interface.

1. Run `python .agent-process/scripts/validate_issue_sections.py <N> --mark-planned`. A
   passing issue is already planned — back-fill the board Status, report, and
   stop.
2. Use all four sources of answers: read and search the repository first;
   ask at most three clarifying questions per session about priority or
   product intent; on a `bug` issue, obtain and record the `discovery`
   role's `## Evidence` block verbatim; for every other class, search for a
   maintained library, tool, or upstream feature that already solves the
   problem before designing code, and record the search, candidates, and
   verdict in `## Prior art`.
3. Obtain the architect review below and record it in `## Architect review`;
   weave every BLOCKING finding into the other sections before writing the
   body.
4. Fill `## Agent handoff`, then write the complete body back. Never discard
   existing text — restructure and extend it.
5. Re-run `validate_issue_sections.py <N> --mark-planned` and iterate. Stop
   after three iterations; an issue still failing goes back to the user, not
   to an implementer.

`## Test plan` names executable test nodes — the RED contract. `## Docs to
update` lists documents or states behaviour does not change. `## ADR`
follows this project's own cost-of-change filter for where a decision's
rationale should live; `none: <reason>` is a routine answer, and a created
record also joins `## Docs to update`. A planner does not write implementation
code, create the branch, or change labels.

## Architect review contract

An architect review reads a plan or issue body **before** execution — a
finished diff belongs to the PR reviewer. It is read-only: it returns
findings, and the planner applies them.

Required for every substantive change; a trivial one records
`skipped: <reason>` instead. One pass, never a loop.

### Who reviewed, recorded

Where a second carrier exists, it reviews a plan it did not write;
otherwise the planning agent reviews its own plan — **legitimate but
weaker**, since it never replaces the PR review of the diff and must never
pass for independent.

The section opens with a provenance line, resolved by
[`validate_issue_sections.py`](../../scripts/validate_issue_sections.py)
against `architect_reviewer.adapter_independence` in the role catalogue —
not written by the author, so a marker cannot claim independence for a
self-review carrier:

```md
reviewer: <a carrier declared in .agents/orchestration/roles.yaml>
```

Only the **first non-empty line** counts. An unknown carrier is a gap; a
self-review passes with a non-blocking note. A section with no marker sends
the issue back to a planner rather than guessing.

The reviewer reads the [goal function](principles.md#goal-function), checks
§I–§VII, and names scope creep, unnecessary/reinvented work, an unnamed root
cause, an over-broad external-data boundary, avoidable token spend, a
test-first loophole, or a high-cost decision with no recorded rationale.

### Findings format

Grade findings; do not filter them — an unwritten finding is
indistinguishable from a review that never ran (§IV), so shorten each
finding rather than report fewer. Filtering is the planner's job.

Each finding is concrete and actionable, carrying a confidence — high,
medium, or low — wherever the reviewer is unsure of the finding itself:

- **BLOCKING** — a named §I–§VII violation, a design defect that would have
  to be redone after execution, a symptom fix over an unnamed cause, or an
  unverified assumption about an external API the plan rests on.
- **SHOULD-FIX** — a marked improvement to future support cost or token
  spend.
- **NICE-TO-HAVE** — everything below those two bars; it moves down, it does
  not disappear.
- **OK** — what the plan already gets right.

## Deterministic delivery flow

This is the per-issue flow. It applies only after the one-time repository
[installation and activation](agent-process-installation.md) are complete.

1. Before creating an issue, fetch `origin/main` and check recent closed
   issues and merged PRs for semantic duplicates. Ask the user for priority,
   then set it with `python .agent-process/scripts/set_issue_priority.py <N> <priority>`.
2. The planner researches the repository, writes the issue contract, obtains
   the architect review, fills `Agent handoff`, and validates the result.
3. The implementer validates the issue again, verifies its Project Priority
   with `set_issue_priority.py <N> --check`, then creates the branch only
   with `python .agent-process/scripts/issue_branch.py <N>` (also moves the board card to
   `In Progress`). It writes and proves failing tests, commits RED before
   production logic, implements the agreed outline, updates docs/ADRs, and
   runs the local CI gate once in the foreground.
4. Create the PR only with `python .agent-process/scripts/open_pr.py --body-file <report>`;
   a substantive UTF-8 report verifies the issue closing reference. Replace an
   existing PR body only with
   `python .agent-process/scripts/update_pr_body.py <PR> --body-file <path>`. Fix CI
   findings for up to three iterations, then loop: after creating the PR and
   after every successful push run
   `python .agent-process/scripts/request_codex_review.py --request <PR>` through the local
   authenticated PR-author session, then run `gh pr checks <PR> --watch`,
   inspect a failed run with
   `gh run view <run-id> --log-failed`, and ask
   `python .agent-process/scripts/review_gate.py <PR>` whether to continue — its verdict
   decides, not the agent's own reading. `should-fix` findings are the
   maintainer's call and don't gate the loop. A PR is ready once the
   current head has no blocking finding and every required check passes.

One PR is one logical unit. Do not bypass hooks, push to `main`, force-push,
reset hard, delete branches forcefully, self-merge, or replace these gates
with an agent assertion. GitHub branch protection is authoritative; a
review check that is skipped, missing, malformed, or still pending leaves
the PR `not ready`.

### Review-gate verdicts

`python .agent-process/scripts/review_gate.py <PR>` reads the live PR — required contexts on
the current head, and how many distinct heads `agent-review` has reviewed. It
changes nothing and posts nothing.

| Verdict | Exit code | Meaning |
| --- | --- | --- |
| `ready-for-human` | `0` | Loop over. Report the PR ready; remaining findings are the maintainer's call. |
| `fix-blocking` | `10` | One minimal fixer commit, push, run the gate again. |
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
NON-BLOCKING conversation is advisory. A valid result has an explicit empty
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

Publisher-only tests live under `tests/publisher/` and never reach a rendered
consumer. Consumer tests originate under `template/tests/agent_process/` and
render below the reserved `tests/agent_process/` subtree — the only path a
process test may occupy in a consumer's `tests/` root; a copier update never
places one elsewhere. `template-drift-allowlist.yml` declares each publisher
test file's own `root_only_paths` row with its own `reason:`, never a
directory-wide exemption, so a stray file dropped into `tests/publisher/`
still fails the drift gate (`.agent-process/scripts/template_drift.py`) as an undeclared
extra file.

Run either suite independently — `python -m pytest tests/publisher` or
`python -m pytest tests/agent_process` — or both together with the documented
full command, `python -m pytest` (also what `python .agent-process/scripts/ci_check.py`
runs). Before running `copier update` against a repository that predates this
split, run `python .agent-process/scripts/check_consumer_test_collision.py <path>` **from an
up-to-date checkout of this distribution repository**, with `<path>` pointing
at the target repository — not from inside the target repository itself,
since a pre-split consumer does not yet have this script (`copier update`
only installs it once the update completes). The check renders the current
template against the target's own recorded answers and reports, with the
exact colliding relative path, any file already occupying a location the
template's closed root set reserves for itself — `.agent-process/`, the
reserved `tests/agent_process/` subtree, and the rest of
[ADR 0019](../adr/0019-single-root-agent-process-layout.md)'s closed root
set — a case Copier's own `--conflict` handling does not catch, since it
only marks conflicts for paths it previously tracked through a prior
render's diff.

## Maintaining this distribution

This section applies only when maintaining `agent-process-distribution` itself,
not when delivering an issue in a repository that received its payload.

Edit a payload file in `template/` and re-render its root copy; never hand-edit
the generated root copy.

## Governance conventions

1. Create issue branches only with `python .agent-process/scripts/issue_branch.py <N>` (starts
   from fresh `origin/main`); never create a branch directly.
2. Keep one PR to one logical unit. A temporary CI unblock for an unrelated
   failure may accompany the blocked change only with a tracked follow-up for
   the root cause.
3. Assign exactly one type label: `bug` for broken behaviour; then
   `perf`/`security`/`enhancement` for user-visible work; otherwise
   `refactor`, `testing`, `ci`, `documentation`, or `chore` by changed area.
   The validator fails on zero or several type labels.
4. Ask the user for issue priority, then set it with
   `python .agent-process/scripts/set_issue_priority.py <N> <High|Medium|Low>`. Propose High
   for user-facing bugs and process work, Medium for agentic capability work
   outside the process, Low otherwise; name the rule used.
5. The process owns exactly two board Status transitions, written from
   scripts a role already runs: `Planned` from `--mark-planned`, `In
   Progress` from `issue_branch.py`. `Todo` and `Done` belong to the
   built-in Project automations; `.agent-process/scripts/set_issue_status.py` rejects them.
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
