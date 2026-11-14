---
status: "accepted"
date: 2026-10-12
decision-makers: ekolvah
---

# The agent runs under its own identity

## Context and Problem Statement

The agent ran `gh` and `git` with the person's token, so GitHub could not tell the agent from
the person: whatever let the person merge let the agent merge. The plugin's git guard stopped
only the command forms it parsed, and over about 2843 `Bash` calls since it shipped it denied
nothing but deliberate probes. GitHub has no token that pushes but does not merge: merging
needs `Contents: write`, as pushing does, and a fine-grained PAT cannot reach a repository
where its user is a collaborator.

## Considered Options

* A bot account and a ruleset requiring one approval, with no bypass
* A GitHub App instead of the bot account
* An `update` rule on the default branch with an admin bypass for pull requests
* Keep the git guard

## Decision Outcome

Chosen: **a bot account and a ruleset requiring the person's approval**, the platform's
standard gate, which GitHub's own coding agent relies on.

* **D1 — the bot.** The person creates a machine account and adds it to `gh`
  (`gh auth login -s project,workflow`, then `gh auth switch --user <person>`).
  `init` finds the bot as the one `gh auth status` account that is not active (`--agent`
  chooses among several) and, once the installation PR is merged, writes its steps, each
  classified from a read: the bot invited as a write collaborator and its invitation accepted
  with its token, the bot made Writer of the linked Project, the ruleset of D2 and auto-merge.
  Before the merge they print `after-merge` and the PR's body lists them, so the merge is the
  person's consent. The collaborator step is done when the `viewerPermission` read with the
  bot's token is `WRITE` or `MAINTAIN` — the person's token is `ADMIN`; a non-collaborator's
  is `READ`. `init`'s `manual agent-identity` row reads the token `gh` holds for
  `agent-process.bot`, with that token, as the session-start hook of D3 reads it, and stays
  outstanding until it is `WRITE` or `MAINTAIN`.
* **D2 — the gate.** The ruleset `agent-process person approves` on the default branch requires
  one approving review and dismisses stale reviews on push; its bypass list is empty. GitHub
  does not count the author's approval, so the bot cannot approve its own PR, and a bot push
  after the approval dismisses it. Layered on `agent-process default branch` (0 approvals), the
  most restrictive rule wins. `require_last_push_approval` stays off: against the bot, the
  author, it adds nothing, and it would block a PR whose branch the person updated, since then
  no one may approve. Updating dismisses an approval, so the person updates first and approves
  last. Auto-merge may carry out the person's approval.
* **D3 — the token at session start.** In a project whose `openspec/config.yaml` holds the
  agent-process block, the plugin's session-start hook takes `gh auth token --user <bot>` for
  the login `git config agent-process.bot` names (set once per machine; a clone may override
  it) and appends `export GH_TOKEN=<token>` to `CLAUDE_ENV_FILE`, which Claude Code applies to
  the session's `Bash` calls, only when that token's `viewerPermission` is `WRITE` or
  `MAINTAIN`; otherwise the session runs as `gh`'s active account, the person. The token passes
  through no chat and no output. Git reaches it through `gh auth setup-git`, run once
  per machine: the global `credential.https://github.com.helper` reset to the empty value,
  then `gh auth git-credential`, which answers with the session's `GH_TOKEN` and outside a
  session with `gh`'s active account, the person. A session started in a worktree under
  `.claude/worktrees/` runs the same hook and also takes the token. Alternatives: a per-clone
  copy in the clone's git-ignored `.claude/settings.local.json` (a step per clone, stale
  copies, a worktree session running as the person); `env.GH_TOKEN` at user scope, which would
  replace the person's token in every repository.
* **D4 — the release PR.** The release workflow approves the PR with `GITHUB_TOKEN` before it
  enables auto-merge ([ADR 0031](0031-release-prs-merge-without-the-person.md) D4). The PR's
  author is the person's release token, so the approval of `github-actions` counts. The
  repository allows GitHub Actions to approve pull requests.
* **D5 — the guard goes.** The approval refuses `gh pr merge` in every form; the default-branch
  ruleset refuses a push to `main` and a force push to it; the bot has no admin to delete the
  repository; `quality` runs on the head a `--no-verify` push skipped. A force push to the
  agent's own branch, `git reset --hard` and `git branch -D` are no longer caught; the last was
  stopped by Claude Code's permission layer each time it was tried. Each session start where
  the hook takes no token prints `agent-process agent identity not set`.
* **D6 — the admin steps run as the person.** `activate_protection` reads and writes rulesets,
  which the bot cannot see: GitHub returns `bypass_actors: null` to a non-admin. Its `gh` calls
  drop `GH_TOKEN` and `GITHUB_TOKEN` and run as `gh`'s stored active account, the fallback the
  Consequences below accept, used on purpose behind `--dry-run` and the person's yes to
  `--confirm`. `init`'s post-merge steps reuse it, and run their other person-side calls the
  same way, so they succeed from a session already holding the bot's token; the bot's own
  calls, the invitation's acceptance and the reads that check it, carry its token. In this repository the launcher runs the checkout's own scripts, so
  `.claude/settings.json` makes each `--confirm` run ask the person, auto mode included.
* **D7 — the approval merges.** Right after `gh pr create` the agent runs
  `gh pr merge <PR> --auto --squash`; the approval ruleset holds the PR, so the person's
  approval merges it. `init` runs `gh repo edit --enable-auto-merge`, off by default on
  GitHub, only after the approval ruleset, and Install runs `gh pr merge --auto` on the
  installation PR only when both read `unchanged`. No check of the agent's own guards auto-merge: in a repository without
  the ruleset it would merge on checks alone, and the ruleset is the barrier. An approval during the review loop
  merges the PR; `wait_for_pr` reads the PR's state with its head and exits 4 on a PR no longer
  open. A merge during the wait stops the loop before the fix; a push already made after the
  merge is reported by the `wait_for_pr` run that follows it. The approval ruleset is unchanged.

### Consequences

* Good, because a merge of the agent's PR is refused server-side until the person approves,
  whatever command the agent runs.
* Good, because one standard rule replaces the guard's command parser and its tests.
* Bad, because the gate does not hold against an agent that deliberately goes around its env
  (`env -u GH_TOKEN` falls back to the person's keyring token) or pushes a workflow that
  approves as `github-actions`; the guard did not hold there either.
* Bad, because a PR the person authors needs another approver, and other auto-merging PRs,
  such as Dependabot's, wait for the person's approval.
* Bad, because each session leaves the bot's token in plaintext in Claude Code's session-env
  directory, `~/.claude/session-env/<session>/`, kept after the session.

### Deletion condition

Remove the bot, its token and `init`'s `agent-*` post-merge steps when local Claude Code gets
a session-scoped GitHub credential, as cloud sessions do; the ruleset stays.

### Confirmation

`tests/publisher/test_init_post_merge.py::test_agent_identity_pending_is_manual`,
`::test_agent_identity_holds`, `::test_agent_account`, `::test_agent_account_ambiguous` and
`::test_post_merge_steps_are_written` hold D1, the last also D6,
`tests/publisher/test_activate_protection.py::test_approval_ruleset_body` D2,
`tests/publisher/test_activate_protection.py::test_a_clone_with_the_agent_identity` D6,
`tests/publisher/test_session_start.py::test_session_start_takes_the_agent_token`,
`::test_session_start_reports_a_missing_identity` and `::test_session_start_reports_the_marker`
D3 and the marker of D5, and
`tests/publisher/test_reusable_workflows.py::test_release_workflow_approves_and_enables_auto_merge`
D4, `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` and
`tests/publisher/test_pr_delivery.py::test_pr_no_longer_open` and
`tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` D7. Live:
after Install step 5, the
agent's green PR reads `REVIEW_REQUIRED`, and the merge API
called with the bot's token is refused.

## Pros and Cons of the Options

* GitHub App — its installation token expires within an hour, so every session needs a local
  private key and a minting step, and its `contents: write` merges as the bot does, needing
  the same ruleset.
* `update` rule with a bypass — refuses the bot's merge, but every merge then needs the
  person's "bypass rules" choice, auto-merge stops, and the release PR needs a merge job of its
  own; the layout is a community workaround, not a documented setting.
* The git guard — parses commands, so `python -c` against the API was always open.
