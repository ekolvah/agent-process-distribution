## Context

The platform facts, the sandbox observations and the guard measurement are in proposal.md, Why.

Claude Code applies the `env` of the settings to the session's `Bash` calls. Observed on
2026-10-12 with a headless session started with `--settings` holding a probe `GH_TOKEN`:
`printenv GH_TOKEN` returned the probe. A second headless session, started in a directory whose
`.claude/settings.local.json` held a probe `GH_TOKEN` and a `SessionStart` hook, saw the probe
in the hook. This does not hold for every key: `OTEL_*` keys of the user settings do not reach
`Bash`.

## Goals / Non-Goals

**Goals:**
- A merge of the agent's PR is refused server-side in every command form until the person
  approves.
- Release PRs still merge without the person.

**Non-Goals:**
- An agent that deliberately goes around its env, for example `env -u GH_TOKEN gh pr merge`.
  That command falls back to the person's keyring token. The guard never stopped it either: a
  `python -c` call to the API was always open. The hard boundary for that case is a Claude Code
  cloud session, whose GitHub proxy holds a session-scoped credential.
- Commit authorship. Commits keep the person's `user.name` and `user.email`; only the pusher
  changes.

## Decisions

### D1 — A bot account, not a GitHub App
The person creates a machine account, adds it to `gh` with `gh auth login -s project,workflow`,
and switches back with `gh auth switch --user <person>`. The script reads the bot's token with
`gh auth token --user <login>`, a flag that exists in gh 2.87.3, so the token never passes
through the chat.

Alternative rejected: a GitHub App. Its installation token expires after an hour, which means a
local private key and a minting step for every session. Its `contents: write` merges just as
the bot's token does, so it would need the same ruleset anyway.

### D2 — The server rule is a required approval in its own ruleset, with no bypass
The ruleset `agent-process person approves` holds one `pull_request` rule: one approving review,
stale reviews dismissed on push. Its bypass list is empty, so the admin's merge needs the
approval too. GitHub does not count an author's approval, so the bot cannot approve the PRs it
opens. A bot push after the person's approval dismisses it. The default-branch ruleset's own
`pull_request` rule requires 0 approvals; where rulesets layer, "the most restrictive version of
the rule" applies ([about rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)),
so 1 wins.

`require_last_push_approval` is left off. It adds nothing against the bot, which is already the
author. It would block the PR whose last pusher is the person: "Update branch" makes the person
the pusher, and the bot is the author, so no one could approve. Strict up-to-date checks make
that the common case, because `main` moves after every merge and every release. This follows
from the documented rule; it was not observed. Who presses merge after the approval does not matter:
the person's approval is the decision, and auto-merge may carry it out.

The rule is a ruleset of its own, not new parameters of `agent-process default branch`, for the
reason of D4: without a second identity it blocks the solo person, who cannot approve their own
PR.

Alternative rejected: an `update` rule with an admin bypass for pull requests. The sandbox showed
it refusing the bot's merge, but every merge then needs the person's "bypass rules" choice or
`--admin`, auto-merge stops (it does not use the bypass), and the release PR needs a merge job
of its own. The two-ruleset layout it relies on is a community workaround, not a documented
setting ([discussion 113172](https://github.com/orgs/community/discussions/113172)).

Cost: a PR the person authors needs another approver. The agent's `gh pr review --approve`
counts there. Updating a PR dismisses its approval, so the person updates the branch first and
approves last.

### D3 — `GH_TOKEN` in the clone's local settings, git through the clone's config
`GH_TOKEN` "takes precedence over previously stored credentials"
([gh environment](https://cli.github.com/manual/gh_help_environment)).

The token goes into the clone's `.claude/settings.local.json`, not `~/.claude/settings.json`.
At user scope the bot's token would replace the person's in every repository on the machine. The
script refuses when `git check-ignore` does not ignore that file.

Git gets its route in the clone's own config (`git config --local`), which every worktree of the
clone shares:
- The script sets `credential.https://github.com.helper` to the empty string, which "resets the
  helper list to empty" (gitcredentials).
- It then adds `!gh auth git-credential` as the helper.

In the agent's session, `gh` answers with `GH_TOKEN`. In the person's own terminal, without
`GH_TOKEN`, it answers with the active account, which is the person. Observed on this machine,
where the system helper is `manager`: with that route, `GH_TOKEN=probe-token-123 … git
credential fill` returned `password=probe-token-123`.

Alternative rejected: `GIT_CONFIG_COUNT` pairs in the settings env. They add four more keys to
converge, and they reach only sessions that carry the env.

### D4 — `agent_identity` owns the identity and its ruleset, and reuses the existing helpers
- The ruleset: `activate_protection.plan` reads the conflict and the message name from
  `want["name"]` instead of `NAME`; `write` is unchanged. `agent_identity` plans
  `templates/approval_ruleset.json` with them. `owned_fields` compares only the template's
  parameters, so the defaults GitHub adds on read, such as `allowed_merge_methods`, are not drift.
- Read-back: one run of the same plan after the writes, where every transition must be
  `unchanged`. No second comparator.
- The linked Project and its owner: `set_status._repo`, `_linked_project` and `_project_owner`.
- The settings file: init's `_read`, `_eol`, `_write` and `_settings_text`, so the write is
  atomic and a hand-formatted file is refused, not reformatted.
- The bot's calls (`gh api user`, the invitation acceptance): a `Gh` built on `set_status.run_gh`
  with the bot's `GH_TOKEN` in its environment. Tests inject it as a second fake.
- The admin check and the collaborator check share one read,
  `repos/<repo>/collaborators/<login>/permission`. The local refusals come before any network
  call.

Why not in `activate_protection`: that script runs for every consumer. Without a second identity,
the agent opens PRs as the person, and the required approval blocks every PR, because the person
cannot approve a PR they authored. The ruleset is meaningful only together with the identity.

New script, why: no standard tool adds a collaborator, accepts the invitation as the invitee,
grants a Project role and writes the clone's settings and git route in one previewable run.

### D5 — The release workflow approves the release PR
Before the step that enables auto-merge, a step runs `gh pr review --approve` on the release PR
with `GITHUB_TOKEN`. The release token is the person's, so the PR's author and last pusher is
the person, and the approval by `github-actions` counts. This is the sandbox observation of
proposal.md, Why. Each update of the release PR dismisses the previous approval, and the run
that pushed it approves again. The workflow already has `pull-requests: write`.

The repository allows GitHub Actions to approve pull requests (the workflow permissions setting
`can_approve_pull_request_reviews`). The person sets it once, like `allow_auto_merge` of
ADR 0031 D4. Without it the step fails red, and the release PR waits for the person's approval.

Alternative rejected: a merge job that waits for the checks and merges as the admin. It
rebuilds what auto-merge does, and it needs the `update` bypass that D2 rejected.

### D6 — The whole guard goes; a session marker replaces it
Below, each rule of the guard is paired with the catcher actually reached once the guard is gone:
- `gh pr merge`: refused by `agent-process person approves` until the person approves.
- Push to `main`, force push to `main`: refused for any identity by `agent-process default
  branch` (`pull_request`, `non_fast_forward`, no bypass).
- Force push to a feature branch: not caught. The branch is the agent's own, and the review job
  reviews the new head.
- `--no-verify`: not caught locally. The required check `agent-process / quality` runs the same
  `test` on the pushed head.
- `gh repo delete`: refused by GitHub, because the bot has no admin permission.
- `git reset --hard`, `git branch -D`: not caught. The first was never attempted. The second was
  stopped by Claude Code's permission layer each time. The maintainer decided to drop both.

The skill check compares the `GH_TOKEN` of its own environment, which is the session's, with
`env.GH_TOKEN` of the project's `settings.local.json`, read through `_guarded`. A `GH_TOKEN` that
the person exported, for example their own token, therefore does not silence the marker. `_texts`
gains the identity fix next to the pre-push one. The marker does not check that the ruleset exists, because that would take a network call
at every session start. `agent_identity --dry-run` reports it.

## Risks / Trade-offs

- [A session started inside `.claude/worktrees/<change>` does not read the main clone's
  `settings.local.json`: the worktrees hold no such file] → That session runs on the person's
  token, and the marker names it at session start. A session that starts in the clone and enters
  a worktree keeps its process environment, which is checked live after `--confirm` (tasks).
- [With Actions approvals allowed, any workflow of this repository can approve with
  `GITHUB_TOKEN`. An agent that deliberately pushes such a workflow to its branch approves its
  own PR] → The same class as the env bypass of Non-Goals. A fork's run gets a read-only token,
  so outside contributors cannot. The Claude review job runs with `GITHUB_TOKEN`, but its
  `--allowed-tools` hold only inline comments, `gh pr diff` and `gh pr view`.
- [The bot's token in plaintext in `.claude/settings.local.json`] → The file is git-ignored,
  which the script checks, and the `test` baseline runs detect-secrets. The token reaches only as
  far as a write collaborator.
- [`updateProjectV2Collaborators` on a user-owned Project is unobserved] → The confirmed run's
  re-plan reports it as exit 1. The Project docs say "Admins of user-level projects can invite
  individual collaborators".
- [A consumer whose other PRs auto-merge, such as Dependabot's] → They need the person's
  approval under the ruleset.
- [The refusal of an unapproved merge was not observed: the sandbox merge attempt was denied
  locally] → GitHub documents the required approval. After `--confirm`, the agent reads
  `REVIEW_REQUIRED` on its green PR, and the person calls the merge API with the bot's token from
  their own terminal (`gh api -X PUT repos/<repo>/pulls/<N>/merge`, tasks). `gh pr merge` would
  refuse a `BLOCKED` PR on the client without calling the API.
- [Without the last-push rule, the bot can push to a PR the person authors, such as the release
  PR, and approve it] → A deliberate act of the agent, the class of Non-Goals.

## Migration Plan

1. The person allows GitHub Actions to approve pull requests in this repository, then merges
   this change. The approval step is live from that merge; the ruleset is not.
2. The person creates the bot, adds it to `gh`, runs `agent_identity --dry-run` and then
   `--confirm` in this repository, and restarts Claude Code.
3. The next release PR exercises D5 under the new ruleset.

Rollback:
- the ruleset: `gh api -X DELETE repos/<repo>/rulesets/<id>`, using the id the run printed;
- the token: delete `env.GH_TOKEN` from `.claude/settings.local.json`;
- the git route: `git config --local --unset-all credential.https://github.com.helper`;
- the guard and the approval step: revert the PR.
