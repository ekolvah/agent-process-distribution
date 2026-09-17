---
status: "accepted"
date: 2026-09-14
decision-makers: ekolvah
---

# v2: standards replace the bespoke control plane

## Context and Problem Statement

v1 of this process is a Python control plane — `agent_orchestrator.py`, `delivery_state.py`,
`roles.yaml`, a review state machine, branch-protection and Project bootstrap scripts — of
9 100 lines of scripts and 11 400 lines of tests. It is installed by copying files into
consumers through a Copier mirror (`template/`) that needs its own drift tests and a
three-way merge on every update, and the procedure is duplicated once per agent adapter
(Claude Code, Codex).

Most of that code guards the two points where a person already decides: plan approval and
merge. `delivery_state` protected nothing the person had not already decided; the review
state machine turned an advisory comment into a gate the fixer had to satisfy, and a spent
fixer budget was not surfaced, so one PR ran 16 review rounds (#106). Every new guard added
a script, a test and a template mirror, and the cost of the next change kept growing.

How does the process keep the two human decisions, work identically from both agents, and
stop growing?

## Decision Drivers

* In strict order: (1) minimize future bug-fixing and support of the process itself,
  (2) minimize token spend per change, (3) keep the process predictable and under user control.
* Targets: GitHub repositories with Actions and a GitHub Project; mixed stacks; no language
  or test-runner assumption in the core.
* Two agents, Claude Code and Codex, carry every agent role; a role never depends on a
  capability only one of them has.
* The only paid dependencies are the two agent subscriptions; no third service.
* One scenario: a person discusses a task with an agent → the agent plans → the person
  approves → the agent implements and opens a PR → the person merges.

## Considered Options

The decision that shapes all others is the carrier of specs, plans and procedure. Three
options were compared as a Kepner-Tregoe trade study; the other decisions below follow from
the winner and from the drivers.

* OpenSpec (`@fission-ai/openspec`, pinned)
* GitHub Spec Kit (`github/spec-kit`)
* The bespoke `plan-issue` / `implement-issue` runbook of v1, iterated

**MUSTs** (go / no-go)

| MUST | OpenSpec | Spec Kit | bespoke runbook |
| --- | --- | --- | --- |
| A living system spec that shows implemented vs pending | go (`specs/` + `changes/`, `archive` moves deltas) | no-go (constitution + per-feature spec/plan/tasks; no merged system spec) | no-go (plan lives in the issue, nothing accumulates) |
| Identical procedure from Claude Code and Codex | go (`init --tools claude,codex` generates both) | go | go (adapters written by hand) |
| No third paid service; GitHub + `gh` only | go (Node via `npx`) | go | go |

**WANTs** (weight 1–10 from the drivers; score 1–10)

| WANT | w | OpenSpec | Spec Kit | bespoke runbook |
| --- | ---: | ---: | ---: | ---: |
| Maintained by a team other than us (driver 1) | 10 | 9 | 9 | 1 |
| Tokens per change: generated skills, artifacts read per step (driver 2) | 8 | 6 (~17k-token skills, loaded about once per change) | 6 | 8 |
| Fits the issue → branch → PR flow without a wrapper (driver 3) | 7 | 8 (`config.yaml` rules, forked schema) | 5 (own slash commands and `specify` layout) | 9 |
| Archive step keeps the system spec current | 9 | 9 | 2 | 1 |
| Weighted total | | **275** | 191 | 146 |

Spec Kit fails the first MUST; the bespoke runbook fails the first MUST and loses the
maintenance WANT decisively — it is the same loop OpenSpec runs, iterated by one team instead
of many. OpenSpec is chosen.

## Decision Outcome

Chosen option: **OpenSpec as the spec, plan and procedure carrier, and standards instead of
bespoke code wherever a standard exists.** The v2 target is the set of decisions below,
delivered by the changes `v2-1` … `v2-6` (#107); until each archives, v1 stays the enforced
process.

* **Specs and planning = OpenSpec.** Living spec in `openspec/specs/`, changes as deltas
  with scenarios, `/opsx:propose` as the planner, `/opsx:apply` inside the implementer,
  `openspec archive` inside the implementing PR before merge; project rules in
  `openspec/config.yaml`; the architect review is an artifact of a forked schema.
* **Delivery = Claude Code plugin + Codex skills + reusable workflows; no file copy.**
  Copier (drift tests, three-way merges), a pip package (Python-only) and a submodule (live
  dependency) were rejected.
* **The procedure is written once as Agent Skills**; agent adapters are entry points only.
* **The person is the only gate.** Plan approval and merge are human; validators check
  structure only.
* **Merge protection is a GitHub ruleset** installed once from JSON kept in this repository.
* **Review is advisory; coverage is a check.** Reviewers (`claude-code-action`, the Codex
  app) comment; conversation resolution makes a comment blocking by the person's choice.
  Scenario coverage is deterministic, so it is a required check, not a review comment.
* **State lives in the GitHub Project.** The built-in `Status` field is the only delivery
  state (ADR 0024); `set_status` resolves IDs by name at run time.
* **Telemetry is owner-side.** OTLP from both agents through one collector with
  project/task/attempt labels; comparisons per merged PR.

Two rules bind every later addition to the core; they enter `openspec/specs/maintenance/`
with this record: a process script exists only when GitHub, `gh`, OpenSpec, Claude Code or
Codex are shown not to do the job (its ADR carries *Native alternatives considered*), and
every ADR that adds to the core states its *Deletion condition*.

### Consequences

* Good, because `v2-1` … `v2-5` delete the control plane, the Copier mirror, the review
  state machine and their tests; each PR deletes more than it adds.
* Good, because a consumer update is a plugin or tag bump, never a three-way merge of
  process files.
* Good, because the procedure exists once; a Codex/Claude divergence is a bug in one file.
* Bad, because consumers need Node (`npx`) for OpenSpec; GitHub runners have it.
* Bad, because the OpenSpec-generated skills are ~17k tokens per invocation.
* Bad, because Codex has no hooks and no independent subagent: `wait_for_pr` is the only
  end-of-run guard there, and its architect review is a self-review artifact. The person
  approves the plan either way.

### Confirmation

v2 is accepted as a whole when: the size budget of `openspec/specs/maintenance/` holds; a new
project is installed in ≤ 10 minutes; an update never needs a three-way merge of process
files; the `telemetry` metrics are no worse than v1 on the same task types. Structure is
guarded by `test_adr_records` and `openspec validate --strict`.

## Native alternatives considered

Scripts v2 keeps or adds, and why the native feature falls short:

| Script | Native feature tried or ruled out | Why it falls short |
| --- | --- | --- |
| `check_red` | `pytest` JUnit report; a Claude Code `PreToolUse` hook | The report proves a failure, not that it preceded the code; a hook exists in Claude Code only |
| `set_status` | `gh project item-edit`; Project built-in workflows | `item-edit` needs field and option IDs, not names; built-in workflows set Todo/Done only, never Planned/In Progress |
| `wait_for_pr` | `gh pr checks --watch` | Watches checks only; review threads and the review apps are GraphQL-only |
| `finish_change` | `openspec archive` + `git push` + `gh pr checks --watch` | The sequence must be the last task in both agents identically; OpenSpec has no post-archive hook |
| `check_coverage` | `openspec validate`; a required check | `validate` knows scenarios, not test results; the check needs the scenario → test mapping |
| `init` | `openspec init --tools claude,codex`; `/plugin`; `gh api` rulesets; `gh secret set` | Each step is native; the script is the one-command composition a ≤ 10-minute install needs |

## Deletion condition

* OpenSpec abandoned upstream → `openspec/specs/` stays as plain Markdown specs; `/opsx:*`
  is replaced by the `plan-issue` runbook kept in git history; `finish_change` loses its
  archive step.
* Codex ships hooks and subagents as stable → the Codex-specific self-review artifact and
  the `wait_for_pr`-only guard are removed; hooks are restored from v1 (`codex_hooks`).
* GitHub Projects gain a native Planned/In Progress trigger → `set_status` is deleted.
* `gh pr checks --watch` learns review threads → `wait_for_pr` is deleted.
* `openspec validate` learns test results → `check_coverage` is deleted.
* Telemetry shows v2 no better than v1 on the same task types after the minimum comparable
  sample (`v2-6`) → the decision is revisited in a new record, not patched here.

## More Information

Superseded records and what replaces each:

* ADR 0011 (Copier + marketplace distribution) → plugin + skills + reusable workflows (`v2-2`).
* ADR 0013 (`docs/adr/`, self-applied root gated against a working-tree render) → no mirror,
  nothing to gate (`v2-0b`, pulled forward from `v2-2`).
* ADR 0015 (owner-requested Codex review with Claude fallback) → Codex on its own, Claude as
  fallback; `P0`/`P1` threads block through the label-reading check, no classification
  reply (`v2-2b`).
* ADR 0019 (every process-owned path under `.agent-process/`) → no rendered payload in
  consumers (`v2-2`).
* ADR 0021 (the end of an agent turn is a gated event) → `wait_for_pr` as the skill's last
  task; the person is the gate (`v2-1`).
* ADR 0022 (the fixer resolves the thread its correction addresses) → the fixer still
  resolves the `P0`/`P1` thread its push addressed; the check reads the label and the
  resolved state of either reviewer's thread, no classification reply (`v2-2b`).
* ADR 0023 (process contexts are an additive branch-protection minimum) → one ruleset from
  JSON (`v2-2`, `v2-4`).

The other ADRs stay as history without edits.

Lessons from v1 that the specs do not repeat:

* Code at a point where the person already decides is support cost without protection.
* A guard that escalates to nobody is not a guard (16 rounds on one PR).
* A mirror of files needs a mirror of tests; deliver by reference, not by copy.
* A procedure written per adapter diverges; write it once and let adapters call it.
* Open questions are settled by observation in the step that touches them, and recorded
  here — not by reading vendor docs ahead of the step.

Observations from v2-0b (`v2-0b-delete-copier-mirror`, #119):

* The Copier render had exactly one consumer — this repository. Deleting the mirror before
  `v2-1` instead of inside `v2-2` turned every later step into a root-only change; the cost
  of one PR (114 deleted files, 5 edited tests) against the doubled diff of two steps.
* Between `v2-0b` and `v2-2` the repository has no installation path. The three
  `distribution` requirements that survive (`CI runs the trusted driver`, `The process
  footprint is one root`, `This repository dogfoods its own process`) keep scenarios worded
  around a render that no longer exists; they are restated by the `v2-2` delta together
  with `init` rather than reworded twice.
* One test outside the render suite depended on the mirror as data, not as a subject:
  `test_issue_branch.py` loaded the template's pristine `project_settings.py` as its
  "unconfigured" fixture. A mirror is a hidden fixture for tests that never mention it.

Observations from v2-1 (`v2-1a-delivery-scripts`, `v2-1b-planning-schema`,
`v2-1c-remove-v1-planner`; #111), answering the seven open questions
of its brief in the brief's order:

* Auto-close of the issue from a `gh issue develop` branch in a private repository: not
  observable here — this repository is public. Recorded for the consumer migration (#117).
* `wait_for_pr` polls checks and review threads only. A pending Codex review is invisible in
  `reviewRequests`: it is requested by comment and the v1 `agent-review` required check waits
  for it before it concludes, so "a check is still running" is "a review is pending" and
  threads are read only after every check concluded. Observed on the PR of this change:
  the rollup of a new head is empty for a few seconds, then every workflow run attaches
  queued at once; required contexts are not readable without admin rights, so the script
  trusts a concluded rollup only when two consecutive polls list the same checks. Stays
  until `v2-4` reworks review.
* Plan approval has no durable GitHub artifact. The person approved by invoking `/opsx:apply`
  in chat after reading the change on its branch; the commit of the artifacts on the branch
  is the only trace, and the first delivery task does not gate on it. A marker (Project status,
  label) is added only after a run is observed to apply an unapproved change.
* Instruction size: `openspec instructions proposal --json` is 6 829 bytes with the current
  `context` (1 273 bytes); 20 695 bytes with the whole `principles.md` appended (14 859 bytes
  of `context`, under the 51 200-byte cap). `context` stays minimal with a one-line pointer to
  the principles: every planning artifact would otherwise carry the full text on every call,
  while only the architect review reads them in full — and its adapter reads the file itself.
* The archive lock is an upstream defect, not an abort trace. A fresh `openspec init`, one
  change and `archive -y` on Windows (OpenSpec 1.13.0, Node v22.14.0) leave
  `openspec/changes/archive/.openspec-archive.lock` after a successful archive:
  `releaseArchiveClaim` compares the `dev`/`ino` of the open handle with `fs.lstat` of the
  lock path, `fs.lstat` reports `dev = 0` on Windows, the identities differ and the unlink is
  skipped silently. Upstream fix: Fission-AI/OpenSpec pull request 1769 ("fix: release
  archive lock on Windows", open). `finish_change` removes the lock a successful archive
  leaves behind and refuses to archive over a pre-existing one; the removal branch is deleted
  once the pinned OpenSpec release contains that fix.
* Dropped delivery tasks: not observed. This change's own apply run walked `tasks.md` from
  the tracking issue to `finish_change` with the `tasks` rule and the self-review as the only
  guard; `check_tasks` stays unbuilt until a run drops a task.
* Review budget: the three-round cap lives in the `tasks` rule as prose. The first PR of
  this change hit the cap (15 threads over four rounds, nine of them on the `tasks` rule
  text) and was split into three stacked PRs — scripts, schema and rules, removal — each
  with its own change and archive. A counter in `wait_for_pr` waits for an observed overrun.

Further observations of the same run:

* Claude ran the whole delivery on a `v2-1-planning-workflow` branch, not `issue-*`:
  `open_pr.py`, the Stop hook and `verify_pr_link` were inert, the PR was opened with
  `gh pr create --body-file` and `wait_for_pr` was the only end guard — the ADR 0021
  supersession, observed rather than promised.
* `agents/architect-reviewer.md` is a plugin agent (`.claude-plugin/plugin.json`), available
  as a subagent only where the plugin is installed. In this repository's own session it is
  not, so the architect review of `v2-1` was a self-review by the planning session — the
  Codex route by construction. The Claude route with a fresh-context reviewer is observed
  first on a consumer project (#117).
* `set_status.py` duplicates the `gh` helpers of the v1 scripts on purpose: the v1 scripts
  are deleted in `v2-4`, and a shared module would tie the new script to files that go.
* A post-archive push cost a review round on every PR of #111 (#122–#124): the archive was
  the last task, its push moved the head the `agent-review` check binds to, and one more
  `request_codex_review.py --request` waited on a mechanical `openspec archive -y` (on #124
  ~30 min for the workflow to start); the reviewer never saw the archived `tasks.md` with
  its Deliver ticks. `v2-1d` (#125) moves the archive before the PR — `finish_change.py`
  becomes `archive_change.py`, the review loop is the last Deliver task. The first review
  of that PR (#127) caught the remainder: a tick of the last task pushed after the last
  round is the same extra head, and `/opsx:apply` cannot re-enter an archived change — so
  the tasks after the archive leave no tick (the PR is their record) and an interrupted
  run resumes from `gh pr view <change>`.
* The forked schema of `v2-1b` is rejected in `v2-1e` (#126). `openspec schema` is
  `[experimental]` in 1.13.0 and has no `extends`, so the fork was a full copy (230 of its
  269 lines identical to `spec-driven`) that `openspec update` no longer follows; its one
  addition, the `architect-review` artifact, gated nothing — artifact status is file
  existence. The same gate is now the last entry of the `tasks` rule of
  `openspec/config.yaml` and the first delivery task, which reads the verdict; because the
  stock propose skill reports the plan ready as soon as the last schema artifact exists, the
  run-level `context` (loaded before the first artifact) names the review as the end of the
  propose run — the finding of the first review of this PR (#128); planning runs
  on the unmodified `spec-driven` schema, and the review file still archives with the change
  because `openspec archive` moves the directory.

Observations from v2-2a (`v2-2a-board-template`, tracking issue #129):

* `gh project copy 4 --source-owner ekolvah --target-owner @me` (gh 2.87.3) carries the
  whole template: the fields (`Status` with `Todo`, `Planned`, `In Progress`, `Done`;
  `Priority` with `High`, `Medium`, `Low`; the 12 built-in fields), both board views
  (`high`, `Medium`) and the six workflows enabled on the source, all still enabled on the
  copy. The copy lacks nothing the template has, but it is private and is not linked to
  any repository: `init` (#112) links it and prints the visibility as the checklist.
  Items are not copied (0 of the source's).
* Project 4 before this change: private; enabled workflows *Auto-add sub-issues*,
  *Auto-close issue*, *Item added to project*, *Item closed*, *Pull request linked to
  issue*, *Pull request merged*. After the owner's four UI edits: public; *Auto-add to
  project* (this repository, `is:issue,pr is:open`) and *Item reopened → Todo* enabled in
  addition. Workflows are read-only in the API (`ProjectV2.workflows { name enabled }`, no
  mutation, no `gh` command), so those edits are the person's and the agent's part is
  the read before and after.
* `gh repo view --json projectsV2` prints the linked Projects under `Nodes` — capital N,
  unlike every other list gh prints; `set_status.py` accepts both spellings. With
  *Auto-add* on, every issue of the repository is an item of the linked Project, so the
  membership branch of `set_status` (an issue on a foreign board, compared by Project id)
  guards a case that no longer arises and is deleted with its two tests: the board is the
  single Project linked to the repository, zero or several is exit 2 naming them.
* `markProjectV2AsTemplate` is an organization mutation; a user Project cannot be marked
  as a template and is copied as is by `gh project copy`, which reads it only when public.
* The built-in *Pull request linked to issue* workflow sets `In Progress` when a PR links
  the issue, at PR time — after the whole delivery, since the PR opens on the archived
  head. The process needs `In Progress` at delivery start, so the deletion condition of
  `set_status` (a native trigger at that point) is not met; `set_status` writes two
  statuses, `Planned` and `In Progress`, and the Project's workflows write `Todo` (added,
  reopened) and `Done` (closed, merged).
* The owner keeps `Planned` (solution review, 2026-09-16), reversing the v2-1 note that
  it would return only after an incident: the column is visibility of the queue — what
  has a reviewed plan and waits for a carrier — not a gate (`/opsx:apply` by the person is
  still the approval and task 0.1 still reads the verdict file). It is written at the end
  of the propose run by the review entry of the `tasks` rule, the extension point
  `openspec update` keeps; a Claude hook (Claude-only) or a schema fork (`v2-1e`) would not
  be. The propose run creates the tracking issue when the change has none, asking the
  priority once, so no delivery task prompts.

Observations from v2-2b (`v2-2b-review-by-apps`, tracking issue #130), answering the
questions of #114 in its order:

* Codex's automatic reviews: closed by the owner's decision (solution review, 2026-09-17),
  not by observation. The Codex app settings offer *On PR open* and *On every push*;
  the first would hand every later push of a PR to the Claude fallback, the second reviews
  exactly as often as the Deliver step already requests (`@codex review` after the PR and
  after every push) while moving the count out of the agent's hands. Not enabled; the
  request stays the rule's, the review count stays the push count.
* The same review decided one reviewer per head: Codex primary, Claude only when no Codex
  review of the head exists after the bounded wait (`codex-timeout-seconds`, 600 s). An
  error or usage-limit message from the app is the absence of a review, not a parsed
  signal — the parser (`check_agent_review_outcome.py`, the JSON schema, the evidence
  publication, ADR 0020's downgrade rule) is deleted with this change; nothing of ours
  reads what a review says.
* A `P0`/`P1` thread blocks through the required `agent-review / agent-review` check,
  whose last step reads the label of a thread's first comment and its resolved state for
  either reviewer login (`chatgpt-codex-connector`, `github-actions`), replies to nothing.
  `required_review_thread_resolution` was rejected: it treats a `P3` nit like a `P0`.
  Branch protection unchanged.
* The first PR (#136) is reviewed by the v1 workflow on `main` (the caller pins `@main`):
  Codex reviewed its first head within the run's four minutes, the Claude step was
  skipped, and the v1 evidence publication left a `github-actions[bot]` review on the
  head — the login the check reads for the Claude job. The new job's fallback is first
  observable on the second PR: whether it ran on any head, why (Codex silent, out of
  quota, erroring) and what it cost: <observed on the second PR>.
* The first Codex review of #136 found the gap of a fallback that finishes green without
  publishing (ADR 0004 records the action doing so): the job gained a sixth step, the
  same presence read on the workflow token's login (`request_codex_review.py --wait
  --reviewer github-actions`), which fails the check when the fallback published
  nothing on the head. The login on Claude's inline comments, if the fallback runs:
  <observed on the second PR>.
* Its third review asked to bind that presence read to the invocation (a run id in the
  publication, or the action's own log) or to a dedicated app identity, since
  `github-actions[bot]` is shared by every workflow of the repository with a write token.
  Accepted as is by the owner (2026-09-17, recorded on #130): what can publish under that
  login is a workflow of this repository with a write `GITHUB_TOKEN`, i.e. a collaborator
  with write access — the merge authority already; a fork PR runs read-only and a human
  comment carries a human login. Binding the evidence to the run is the parser coming back
  under another name; a dedicated app identity is a repository setting and a secret, and
  stays the person's call if a case shows the need.
* `pull_request_review_thread` does not exist as a trigger any more: the first push of the
  second PR (#137, `397c54f`) produced no `agent-review` run at all — GitHub reported
  `Invalid workflow file (Line: 10, Col: 3): Unexpected value 'pull_request_review_thread'`
  and the event is gone from the "Events that trigger workflows" reference. The caller
  keeps `pull_request_review: [submitted]` only. A check run started by a `pull_request_review` event is listed
  for the head: on #137, head `cb6ffe9`, Codex's review at 17:01:07Z started run
  `35250133503` (`event: pull_request_review`, 11 s) four minutes after the
  `pull_request` run `35249657967` of the same head; `gh pr checks 137` lists both under
  `agent-review / agent-review`. The inference drawn then — that the required context
  follows the later run — was wrong; see the last bullet of this section. That run had skipped the wait and the fallback
  (enforcement only, as designed) — which Codex's third review of #137 showed to be a
  hole: any submitted review, a human's or one of an older commit, starts such a run
  while the `pull_request` run is still waiting, and with no thread yet it passes and
  becomes the required context for a head nobody reviewed. A skipped job passes a
  required check as well, so no `if` can filter the event; the callee now runs the same
  path on every event, and a review-event run's conclusion derives from a review of the
  head. Cost accepted: a human review on a PR Codex left silent starts a second wait and
  a second Claude review.
* A reply on a review thread is a submitted review: the fixer's REST reply on #137 became
  a `COMMENTED` review by the author and started run `35251460261` on head `b6858f8`
  (17:14:00Z, `event: pull_request_review`) — which, running the `@main` callee of that
  hour, skipped the wait and the fallback and passed on enforcement alone, four minutes
  before Codex's review of the head arrived with a `P1`: the hole of the previous bullet,
  observed live. The rule orders the loop around it: resolve once the review of the new
  head is in, reply after the resolve — a resolve is never the last write on a thread.
  Codex's P1 on `8f272f3` (the sixth review of #137): the rule's wait had read "the Codex
  review of the new head", a condition never true on a head Codex left silent, where the
  check ran the fallback and the head is reviewed all the same — an addressed thread could
  not be resolved on that path and the check stayed red. The wait is keyed to the concluded
  check of the head, whichever carrier reviewed it (`wait_for_pr.py` returns on it either
  way; `v2-2b-any-carrier`). The caller pins the callee `@main`, so #137 exercises none of its own callee
  changes; the same-path run is first observed on the PR after its merge:
  <observed on the next PR>.
* Fork PRs and the secret (2026-09-17, on the fourth and fifth Codex reviews of #137).
  Codex asked whether a review event on a fork PR reaches the Claude step with the
  repository's secret, and then noted that the caller YAML of a `pull_request_review` run
  is read from the PR merge ref, so a fork can rewrite it and no condition in callee or
  caller can protect the secret. Round 4 had answered the first with a guard on the
  Claude step (`head.repo.full_name == github.repository`); the second showed the guard
  protects nothing, and the platform documentation, read then instead of before round 4,
  settles both: the events reference lists `pull_request_review` and
  `pull_request_review_comment` under the same fork restriction as `pull_request` — every
  secret but `GITHUB_TOKEN` is withheld from a run of a fork PR, the token is read-only
  (observed in the wild: aws-actions/configure-aws-credentials#416, credentials absent on
  `pull_request_review` from a fork). The guard was code for what the platform does and
  is removed (`v2-2b-fork-policy`); the control that adds something is the repository
  setting "Require approval for all external contributors"
  (`PUT /repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval`,
  `approval_policy: all_external_contributors`, set on 2026-09-17 from
  `first_time_contributors`): a run of a fork PR by a non-member does not start until the
  person approves it, on every event but `pull_request_target`, which the process does not
  use. A run of a fork PR holds no secret and is red on the missing Claude review unless
  Codex, requested by a member, reviewed the head. Deletion condition: none; the
  setting is the platform's, and a change of the event set of the caller re-reads the same
  reference page.
* Resolve-then-reply observed on #137, head `26bc2da`, before the rule relied on it (Codex's
  P1 on that head asked for exactly this): thread `PRRT_kwDOUAa7yM6jdmmL` resolved at
  18:04:21Z, replied to at 18:04:22Z; the reply started run `35256579419`
  (`pull_request_review`, 18:04:23Z) on the unchanged head, whose enforcement listed the two
  open threads of the newer review only — the resolve held and the run read it. The event
  and the thread state are the platform's, independent of which callee the run executes,
  so the observation stands for the merged one.
* The review-event trigger is withdrawn (owner's decision, 2026-09-17): every event is a
  required context of its own. On head `a1d0bad` of #137 the `pull_request` run
  `35262221116` concluded red at 19:04Z while the `P1` thread was open; the resolve and
  three replies started three `pull_request_review` runs that concluded green at 19:06Z,
  and the PR stayed `mergeStateStatus: BLOCKED` — the branch protection's `statusCheckRollup`
  listed the `pull_request` run as a required context of its own with `FAILURE` beside the
  green review-event runs (the UI: two lines under `agent-review`, `(pull_request)` and
  `(pull_request_review)`, both "Required"). `gh run rerun 35262221116` re-executed that
  run on the same payload, its enforcement read the resolve, and the PR went `CLEAN`.
  So a review-event run re-runs a check but never the required one: the design D6 of
  `v2-2b` (a resolve needs no rerun by hand because the reply re-runs the check) is
  false, and what the trigger adds is a second required line, a run — a wait and, on a head
  Codex left silent, a Claude review — per reply, and the fork and `last: 30` questions of
  the fourth and fifth Codex reviews. The caller runs on `pull_request` alone again; the
  rule and step 4 read resolve → `gh run rerun <run-id>` → reply, the rerun being the
  deterministic step a resolve needs (`v2-2b-push-only`). What #137 keeps: the callee on
  one path for any event a caller may send, the resolve-after-wait and reply-after-resolve
  order, the spec-fix rule, the fork setting. Lesson for the planner, as an issue of its
  own: a platform behaviour a design rests on is verified on the platform before the
  proposal, not inferred from a listing.
* Review fixes of #137 (rounds 3–4) had edited `openspec/specs/` directly: the PR's change
  was archived before the PR opened, as the process orders, and nothing described the new
  behaviour as a delta. Owner's decision (2026-09-17, on Codex's P1 of `26bc2da`): a review
  fix that changes a spec goes through a change of its own on the PR branch — delta,
  `validate --strict`, `archive_change` — never a direct edit; the archive is the one path a
  spec takes. `v2-2b-review-events` is that change for #137: the direct edits reverted, the
  same text carried as a delta, the rule sentence with its assertion; no new issue or
  branch, since it is the delta of the PR's own fixes.
