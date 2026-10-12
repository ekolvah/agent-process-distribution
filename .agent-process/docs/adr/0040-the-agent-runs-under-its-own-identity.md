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
  `agent-process agent_identity --bot <login>` reads its token with `gh auth token --user`, so
  the token never passes through the chat, refuses an admin, makes the bot a write collaborator
  and a writer of the linked Project, and plans and converges the rest of this record with
  `--dry-run` and `--confirm`.
* **D2 — the gate.** The ruleset `agent-process person approves` on the default branch requires
  one approving review and dismisses stale reviews on push; its bypass list is empty. GitHub
  does not count the author's approval, so the bot cannot approve its own PR, and a bot push
  after the approval dismisses it. Layered on `agent-process default branch` (0 approvals), the
  most restrictive rule wins. `require_last_push_approval` stays off: against the bot, the
  author, it adds nothing, and it would block a PR whose branch the person updated, since then
  no one may approve. Updating dismisses an approval, so the person updates first and approves
  last. Auto-merge may carry out the person's approval.
* **D3 — the token in the clone.** `GH_TOKEN` goes into the clone's git-ignored
  `.claude/settings.local.json`, which Claude Code applies to the session's `Bash` calls; at
  user scope it would replace the person's token in every repository. Git reaches it through
  the clone's own config: `credential.https://github.com.helper` reset to the empty value, then
  `!gh auth git-credential`. A session started inside a worktree under `.claude/worktrees/`
  does not read the clone's file and runs as the person; a session started in the clone keeps
  its environment when it enters a worktree.
* **D4 — the release PR.** The release workflow approves the PR with `GITHUB_TOKEN` before it
  enables auto-merge ([ADR 0031](0031-release-prs-merge-without-the-person.md) D4). The PR's
  author is the person's release token, so the approval of `github-actions` counts. The
  repository allows GitHub Actions to approve pull requests.
* **D5 — the guard goes.** The approval refuses `gh pr merge` in every form; the default-branch
  ruleset refuses a push to `main` and a force push to it; the bot has no admin to delete the
  repository; `quality` runs on the head a `--no-verify` push skipped. A force push to the
  agent's own branch, `git reset --hard` and `git branch -D` are no longer caught; the last was
  stopped by Claude Code's permission layer each time it was tried. Each session start whose
  `GH_TOKEN` is not the clone's prints `agent-process agent identity not set`.

### Consequences

* Good, because a merge of the agent's PR is refused server-side until the person approves,
  whatever command the agent runs.
* Good, because one standard rule replaces the guard's command parser and its tests.
* Bad, because the gate does not hold against an agent that deliberately goes around its env
  (`env -u GH_TOKEN` falls back to the person's keyring token) or pushes a workflow that
  approves as `github-actions`; the guard did not hold there either.
* Bad, because a PR the person authors needs another approver, and other auto-merging PRs,
  such as Dependabot's, wait for the person's approval.
* Bad, because the bot's token lies in plaintext in a git-ignored file.

### Deletion condition

Remove the bot, its token and `agent_identity` when local Claude Code gets a session-scoped
GitHub credential, as cloud sessions do; the ruleset stays.

### Confirmation

`tests/publisher/test_agent_identity.py` holds D1–D3,
`tests/publisher/test_skill_check.py::test_identity_missing` the marker of D5, and
`tests/publisher/test_reusable_workflows.py::test_release_workflow_approves_and_enables_auto_merge`
D4. Live: after `--confirm`, the agent's green PR reads `REVIEW_REQUIRED`, and the merge API
called with the bot's token is refused.

## Pros and Cons of the Options

* GitHub App — its installation token expires within an hour, so every session needs a local
  private key and a minting step, and its `contents: write` merges as the bot does, needing
  the same ruleset.
* `update` rule with a bypass — refuses the bot's merge, but every merge then needs the
  person's "bypass rules" choice, auto-merge stops, and the release PR needs a merge job of its
  own; the layout is a community workaround, not a documented setting.
* The git guard — parses commands, so `python -c` against the API was always open.
