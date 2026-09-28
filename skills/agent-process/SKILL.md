---
name: agent-process
description: Plan, implement, review, and deliver the shared GitHub agent development process.
---

# Agent process

Use this procedure with Claude Code. Repository-specific facts remain in
`openspec/config.yaml`; this skill owns the portable planning and delivery procedure. Run
repository operations, and every command printed below, from the repository root, where the
paths those commands name resolve. Placing this skill in a repository that does not carry it
at those paths is the installer's to define.

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

1. Group 0 — Delivery start: one task runs `python
   skills/agent-process/scripts/start_change.py <change> --planner Claude --implementer Claude`;
   the issue records them as provenance. Its text carries `tracking issue <N>`; the propose tail
   replaces the placeholder, and both scripts read the token there. The script validates the
   architect review, reads its verdict and the Status of the issue, removes the clean
   worktrees of merged changes, creates the linked branch from `origin/main` in its own
   worktree `.claude/worktrees/<change>`, moves the change's files there, sets In Progress
   and posts the provenance line. Enter that worktree with `EnterWorktree` (its `path`) and
   run every later task there; a run interrupted before the archive resumes by entering the
   same worktree. On `rework`, apply
   the findings and run the review again. It prints `propose run not finished` and exits 2
   while the token still carries `<N>` or the issue is not a Project item in the Status the
   propose run leaves it in: nothing is asked and nothing is created there.
2. Group 1 — RED first: write the tests in the scenario-to-test map and run `python
   skills/agent-process/scripts/check_red.py <node ids>`. It runs `python -m pytest` of its
   own interpreter under its own configuration, with a report path of its own and the node
   ids, and takes nothing else. Commit RED before implementation. When
   the map names no test for docs-only, `skip_specs`, or a rename, record
   `no RED: <reason>` as the task.
3. Implementation groups: one task per scenario, design decision, or review finding, each
   with its verification command. End each coherent group with a commit.
4. Verify: run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and the complete
   quality command the repository names in the context of `openspec/config.yaml`.
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
`python skills/agent-process/scripts/create_tracking_issue.py <change> --area <name>` (without
`--area` it lists the options); otherwise run it without area. It validates the review
first; send its errors back to the reviewer. The issue must be `Planned` before the
plan is ready. Then explain the plan in plain words — what changes, why, what the person
decides — as a page linked in the final message, or in that message when the carrier cannot
publish one. Artifact status is file existence only: the verdict is the gate, and Group 0
reads it.

## Delivery

Start from a clean worktree. Run `python skills/agent-process/scripts/archive_change.py
<change>` before `gh pr create --title "<type>: <change>" --body-file <report>`. The report names the
tracking issue as a plain reference, never `Closes`, and carries the scenario-to-test map and
deferrals. The archive is the head the PR opens on.

The `agent-review` check reviews every head with the Claude review job. After creating the
PR and after every corrective push, run `python skills/agent-process/scripts/wait_for_pr.py <PR>`;
it waits until two reads 30 seconds apart agree that all checks on one head concluded, then
reads unresolved threads on that head.

Apply findings and repeat at most three rounds; the fourth leaves the rest to the person with
a reply. After a push, run `wait_for_pr.py` again. A P0/P1 thread the push addressed may be resolved only after the
settled review: `python skills/agent-process/scripts/resolve_review_thread.py --repo
<owner/repo> --pr <PR> --list` prints the open threads with the `<id>` of each, then
`python skills/agent-process/scripts/resolve_review_thread.py --repo <owner/repo> --pr <PR>
--thread <id> --reply-file <path>` closes one; the script
refuses a thread reported against the current head and refuses while the head's check is
still running, then resolves, re-runs that check and replies last. A P2/P3 thread is
answered, never resolved by the process. A spec correction goes through a change of its own on
the PR branch — `npx -y @fission-ai/openspec@1.13.0 new change <name>`, the delta under its
`specs/`, `validate --strict`, then `python skills/agent-process/scripts/archive_change.py
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

In a consumer repository, `skills/agent-process/` in the commands of this skill means this
skill's own directory. Run from the consumer's root:

1. Ask the person for the repository's complete quality command (`--test`) and an optional
   dependency setup command (`--setup`). `gh` must be authenticated with the `project`
   scope: even the dry-run reads the repository's Projects.
2. Run `python skills/agent-process/scripts/init.py --test "<command>" --dry-run` (add
   `--setup "<command>"` and `--version <x.y.z>` when given) and show its whole output. A
   `conflict` line names a path or Project the installer does not own: the person resolves
   it, then the dry-run runs again.
3. Ask once; on yes run the same command with `--confirm` instead of `--dry-run`.
4. Tell the person to review and commit the changed files and to do the `manual` rows:
   the `project-*` rows in the Project's UI, and the `review-secret` row, which sets the
   repository's `CLAUDE_CODE_OAUTH_TOKEN` secret the review caller passes to the review, and
   the `plugin-channel` row, once per machine and outside any project.
   The installer never commits or pushes; its only GitHub writes are the copy of the
   template Project and its link to the repository.
5. Once the installation PR shows `agent-process / quality` and `agent-review / agent-review`
   green and the person has merged it, run `python skills/agent-process/scripts/activate_protection.py --pr <N> --dry-run` with
   that PR's number (admin rights on
   the repository) and show its whole output. Ask once; on yes run it with `--confirm`
   instead of `--dry-run`. It makes the check required through one ruleset and never
   writes classic branch protection.

Claude applies the plugin only after the person trusts the folder, and runs the release the machine last
fetched for the marketplace name: the `ref` in `.claude/settings.json` does not re-point a
marketplace the machine already knows (#184). The marketplace follows the branch `stable`,
which each release fast-forwards, with auto-update on, so a machine that did the
`plugin-channel` row gets a release within a session. At each Claude session start the installed
check prints `agent-process skill not loaded (<reason>)` when the plugin does not supply
the skill; the fix is `claude plugin update agent-process@agent-process-marketplace --scope
<user|project>` and a restart, or enabling the plugin for the project. A machine still on a
release tag migrates once, outside any project: set the `ref` of `agent-process-marketplace`
in `~/.claude/settings.json` to `stable`, run `claude plugin marketplace add
"ekolvah/agent-process-distribution#stable"`, turn on Enable auto-update for it under
`/plugin` → Marketplaces, then re-run Install in each repository.
