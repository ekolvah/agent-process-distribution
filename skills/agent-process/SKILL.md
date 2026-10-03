---
name: agent-process
description: Plan, implement, review, and deliver the shared GitHub agent development process.
---

# Agent process

Use this procedure with Claude Code. Repository-specific facts remain in
`openspec/config.yaml`; this skill owns the portable planning and delivery procedure. Run
repository operations, and every command printed below, through the Bash tool from the
repository root. `agent-process`, the first word of each script command, is the plugin's
launcher of this skill's scripts, on the Bash tool's `PATH` while the plugin is enabled.

## Principles

[`principles.md`](principles.md#goal-function) binds every role. Its goals, in strict order:

1. Minimize future bug-fixing and support.
2. Optimize token spend, in development and at runtime.
3. Preserve predictability and user control.

- [§I](principles.md#i-test-first-non-negotiable): a failing test precedes every behavioural change.
- [§II](principles.md#ii-protocol-boundaries-with-dependency-injection): each external service sits behind an injected `typing.Protocol`; tests use in-memory doubles, not mocks of internal logic.
- [§III](principles.md#iii-delivery-truthfulness): user-visible data is never lost silently; a failed delivery turns the run red.
- [§IV](principles.md#iv-visibility-over-silence): a degraded item reaches the user with a gap marker; no swallowed error or fail-open branch.
- [§V](principles.md#v-root-cause-before-fix): reproduce and locate the failure, observing the live system when it is the subject, before any change; no shim.
- [§VI](principles.md#vi-fail-fast-configuration): configuration is validated at load time.
- [§VII](principles.md#vii-simplicity-first): the minimum diff for the stated task; no speculative feature or single-caller abstraction.

On any conflict, the full text of `principles.md` decides.

## Claude harness

- Read narrowly: a search or an `offset`/`limit` read before a whole file. When a navigation
  hook denies a command, take the call it names; never route around it.
- Spawn a subagent only for independent work, or for research that needs more than three
  round trips.
- Be concise by default, in replies and in files.
- Wait for a long command with one foreground call and a raised `timeout`, never a `sleep` or
  re-read loop.
- After a compaction between the RED commit and GREEN, recover from the branch
  (`git branch --show-current`), the RED commit and one `gh issue view <N>`; do not re-read
  what the RED commit records.

## Proposal

- Read the code and prior art before writing. Ask the person when a scope decision is theirs.
- For a bug, record the reproduction — the failing test, or the exact observation when a test
  needs project-specific capture — and the root cause under **Why** before any design.
- **Impact** lists every file added, edited, and removed; keep doc-only work separate.
- When a design rests on platform behaviour — an event, a permission, a merge rule, a token
  scope, a CLI flag — verify it before the proposal and record the observation, not the
  inference, under **Why** or in `design.md` beside the decision: cite the reference page and
  sentence, or a run id or exact command output — a run of a standard checker counts, a listing, a name or an inference from
  another behaviour does not. Point to an observation already on record instead of repeating it.

## Specifications

- Specs contain requirements and scenarios only. Put rationale, alternatives, non-goals,
  and open questions in `design.md` or an ADR.
- Keep requirement titles short and stable. A rename is a RENAMED delta plus the matching
  test rename in one change.
- Each scenario names an observable outcome using the stock OpenSpec structural headings
  and SHALL/MUST keywords in English.

## Design

- Record decisions, alternatives, risks, and the migration and rollback boundary.
- A new script or check has a decision naming the problem it closes — an issue, PR or run
  when one exists — and the standard for its job and why it does not fit.
- A design that replaces a project-declared input with one the caller supplies, or drops a
  guard, lists beside the decision the new input's failure modes, what stops proving, and for
  each lost proof the catcher that is actually reached: which script, which run, on which head,
  not a role or the platform in general.

## Tasks

Write these groups in order and end `tasks.md` with `## Scenario → test map`, mapping every
delta scenario to a named test or `n/a: <reason>`.

1. Group 0 — Delivery start: one task runs
   `agent-process start_change <change> --planner Claude --implementer Claude`; the issue records them as provenance. Its text carries `tracking issue <N>`: the number of
   the issue the change is planned from, else the placeholder, which the propose tail
   replaces; both scripts read the token there. The script validates the
   architect review, reads its verdict and the Status of the issue, removes the clean
   worktrees of merged changes, creates the linked branch from `origin/main` in its own
   worktree `.claude/worktrees/<change>`, moves the change's files there, ticks its task and
   commits the plan there (not pushed), sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` (its `path`) and
   run every later task there; a run interrupted before the archive resumes by entering the
   same worktree. On `rework`, apply
   the findings and run the review again. It prints `propose run not finished` and exits 2
   while the token still carries `<N>` or the issue is not a Project item in the Status the
   propose run leaves it in: nothing is asked and nothing is created there.
2. Group 1 — RED first: write the tests in the scenario-to-test map and run
   `agent-process check_red <node ids>`. It runs `python -m pytest` of its own interpreter under its own configuration, with a report path of its own and the node
   ids, and takes nothing else. It exits 2 until `.github/agent-process-quality.json` declares
   a `test`, so the change that brings the first tests declares it. Commit RED with the
   Group 1 ticks, on top of the plan commit, before implementation. When
   the map names no test for docs-only, `skip_specs`, or a rename, record
   `no RED: <reason>` as the task.
3. Implementation groups: one task per scenario, design decision, or review finding, each
   with its verification command. End each coherent group with a commit that carries its
   ticks.
4. Verify: run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and the `test`
   that `.github/agent-process-quality.json` declares; their ticks ride in the archive commit.
5. Deliver using the procedure below; the Deliver task titles the PR `<type>: <change>` with
   the Conventional Commit type the planner chose — `feat` or `fix` when behaviour changes,
   otherwise `docs`, `test`, `refactor` or `chore`. The person merges.

## Architect review

After `tasks.md`, review proposal, specifications, design, and tasks against principles
§I–VII by invoking the `architect-reviewer` subagent. It writes
`architect-review.json`, valid against `skills/agent-process/architect-review.schema.json`.

Findings point at artifacts instead of restating them. On `rework`, answer every finding and
review again. The propose run ends on `approve`: if the change has no issue, choose the area
that fits the change from the Project's `Area` options and run
`agent-process create_tracking_issue <change> --area <name>` (without
`--area` it lists the options); otherwise run it without area. It validates the review
first; send its errors back to the reviewer. The issue must be `Planned` before the
plan is ready. Then explain the plan in plain words — what changes, why, what the person
decides — as a page linked in the final message, or in that message when the carrier cannot
publish one. Artifact status is file existence only: the verdict is the gate, and Group 0
reads it.

## Delivery

Start from a worktree clean but for the change's own `tasks.md`. Run `agent-process archive_change
<change>` before `gh pr create --title "<type>: <change>" --body-file <report>`. The report names the
tracking issue as a plain reference, never `Closes`, and carries the scenario-to-test map and
deferrals. The archive is the head the PR opens on.

The `agent-review` check reviews every head with the Claude review job. After creating the
PR and after every corrective push, run `agent-process wait_for_pr <PR>`;
it waits until two reads 30 seconds apart agree that all checks on one head concluded, then
reads unresolved threads on that head.

Apply findings and repeat at most three rounds; the fourth leaves the rest to the person with
a reply. After a push, run `wait_for_pr.py` again. A P0/P1 thread the push addressed may be resolved only after the
settled review: `agent-process resolve_review_thread --repo
<owner/repo> --pr <PR> --list` prints the open threads with the `<id>` of each, then
`agent-process resolve_review_thread --repo <owner/repo> --pr <PR>
--thread <id> --reply-file <path>` closes one; the script
refuses a thread reported against the current head and refuses while the head's check is
still running, then resolves, re-runs that check and replies last. A P2/P3 thread is
answered, never resolved by the process. A spec correction goes through a change of its own on
the PR branch — `npx -y @fission-ai/openspec@1.13.0 new change <name>`, the delta under its
`specs/`, `validate --strict`, then `agent-process archive_change
<name>` — never a direct edit of `openspec/specs/`. A changed design decision amends the archived
`design.md` and scenario map in the same push. A finding on script behavior must be closed by its class:
test the violated invariant, the other inputs that violate it from the tool's own
documentation, and what each switch takes away; test the class, not the reviewer's example.

Stop once `wait_for_pr.py` settles a head with no open P0/P1 thread, or at the three-round
escalation, then explain the delivered change in plain words as a page linked in the final
message, or in that message when the carrier cannot publish one. Tasks after archive leave
no tick in the repository because a pushed tick would move the reviewed head. If interrupted after archive,
resume from `gh pr view <change>` — open the PR when there is none — not OpenSpec apply.

## Install

Run from the consumer's root:

1. Ask for no quality command. A run that creates `.pre-commit-config.yaml` seeds a baseline
   Python toolchain there — ruff with complexity limits, mypy, a module-size limit,
   detect-secrets, pip-audit, pytest — and `.github/agent-process-quality.json`, whose `test`
   runs it; otherwise the change that adds the first tests declares it. In a repository with
   code of its own the installation PR's `agent-process / quality` then runs the baseline over
   that code: tell the person before `--confirm` that a failure there is fixed by a commit on
   that PR — narrowing the baseline, listing a library's types in mypy's
   `additional_dependencies`, or fixing the findings. `gh` must be authenticated with the
   `project` scope: even the dry-run reads the repository's Projects.
2. Run `agent-process init --dry-run` (add `--version <x.y.z>` when given) and show its
   whole output. A
   `conflict` line names a path or Project the installer does not own: the person resolves
   it, then the dry-run runs again.
3. When the dry-run prints the `review-secret` row, have the person do it before asking, so
   the first pushed head's `agent-review` runs with the secret: they run `claude setup-token`,
   then `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` and paste the token at its
   prompt, which keeps the token out of the chat. Ask once; on yes run the same command with
   `--confirm` instead of `--dry-run`.
4. The confirmed run commits the files on the installation branch, pushes it, and opens the
   installation PR, linked to its issue; it prints the PR and leaves the checkout on that
   branch. Its output ends with the `manual` rows still outstanding; a row with
   `(cannot read: <reason>)` is one `init` could not check. Tell the person to do those rows —
   the `project-*` rows in the Project's UI, the `plugin-channel` row, once per machine and
   outside any project, and the `pre-push` row, printed only when `init` could not install the
   hook in this clone and naming why — then
   to review and merge the PR, switch to the default branch and pull. In another clone, each
   Claude session start reports the missing pre-push hook until its person runs the two
   commands it names.
5. Once that PR shows `agent-process / quality` and `agent-review / agent-review` green and
   the person has merged it, run `agent-process activate_protection --pr <N> --dry-run` with
   its number (admin rights on
   the repository) and show its whole output. Ask once; on yes run it with `--confirm`
   instead of `--dry-run`. It makes the check required through one ruleset and never
   writes classic branch protection.

The plugin is installed at user scope, once per machine, by the `plugin-channel` row (`claude
plugin install agent-process@agent-process-marketplace`), and applies in every project with no
project setting: a project that enables it gets a project-scope install per spelling of its path
(#256). Claude runs the release the machine last fetched for the marketplace name: the `ref` in
`.claude/settings.json` does not re-point a marketplace the machine already knows (#184). The
marketplace follows the branch `stable`, which each release fast-forwards, with auto-update on,
so a machine that did the `plugin-channel` row gets a release within a session. The plugin's
tool hooks act only in a repository carrying `.github/workflows/agent-process.yml`. At session
start it installs its own Python dependencies, once per machine and pin set; a failure prints
`agent-process plugin environment not installed` with the cause. Its navigation
hooks deny shell file reads and over-budget whole-file `Read`, naming the cheaper call; a
`permissions.deny` rule matching the same command blocks first, so their message never reaches
the agent. Its memory checkpoint, after an edit under the agent's auto-memory directory, asks
whether every session and every person needs the fact, and if so to move it into the
repository. Its edit-time lint runs the project's `pre-commit`-stage hooks of
`.pre-commit-config.yaml` on each edited file and shows a failure to the agent; the seeded
baseline stages its per-file hooks there and at `manual`, which the seeded `test` runs, so the
gate runs the same checks. At each Claude
session start the installed check prints `agent-process skill not loaded (<reason>)` when the
user-scope install does not supply the skill; the fix is the reason's `claude plugin install`,
or `claude plugin update agent-process@agent-process-marketplace --scope user` for a stale
release, and a restart. It prints `agent-process project-scope install applies` with one `claude
plugin uninstall` command per project-level install of the project, each run from that
install's path spelling; the person runs them once. A machine still on a
release tag migrates once, outside any project: set the `ref` of `agent-process-marketplace`
in `~/.claude/settings.json` to `stable`, run `claude plugin marketplace add
"ekolvah/agent-process-distribution#stable"`, turn on Enable auto-update for it under
`/plugin` → Marketplaces, then re-run Install in each repository.
