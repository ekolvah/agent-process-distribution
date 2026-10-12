## Why

The agent runs `gh` and `git` with the person's own token (`gh auth status`: account `ekolvah`,
OAuth token with `repo`), so GitHub cannot tell the agent from the person: whatever lets the
person merge lets the agent merge. The plugin's git guard only stops the command forms it
parses. The server should be the boundary.

GitHub cannot express "a token that pushes but does not merge". Its own pages say so:
- "Merge a pull request" needs `Contents: write`, the same permission as pushing a branch
  ([permissions for fine-grained PATs](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)).
- A fine-grained PAT cannot "contribute to repositories where the user is an outside or
  repository collaborator"
  ([managing PATs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)).

So the agent gets a second identity, and the default branch requires an approved pull request.
GitHub does not count an author's approval of their own PR. This is the platform's standard
gate, and GitHub's own coding agent relies on it ([review Copilot PRs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/review-copilot-prs)).
A PR the agent opens merges after the person approves it, unless the agent deliberately pushes a
workflow that approves as `github-actions` (design, Risks).

Observed on 2026-10-12 in the throwaway public repository
`ekolvah/agent-process-sandbox-restrict-updates`, under a ruleset with one required approval,
stale approvals dismissed on push, and the last push's approval required (a rule the chosen
ruleset drops, design D2):
- PR 2, authored and last pushed by the owner, with auto-merge enabled by the owner, was
  `BLOCKED` with `REVIEW_REQUIRED`.
- A `pull_request` workflow ran `gh pr review --approve` with `GITHUB_TOKEN`, after the
  repository allowed GitHub Actions to approve pull requests. The review by `github-actions`
  counted, and auto-merge merged the PR.

That is how the release PR, whose author is the person's release token, keeps merging without
the person.

Before deleting the guard, its denials were measured over the 538 local transcripts. Since the
guard shipped on 2026-10-06 there were about 2843 `Bash` calls and 0 organic denials: the only
2 denials were deliberate probes (`gh pr merge 0`). Before the guard shipped, the agent tried
`git branch -D` 4 times, and Claude Code's permission layer stopped all 4. `gh pr merge`,
`gh repo delete`, a push to `main` and `git reset --hard` were never attempted. Following the
maintainer's rule on the issue (a rule that never fired, or that Claude Code already stops,
goes) and the maintainer's decision for this change, the whole guard is deleted once the
installer sets up the identity.

## What Changes

- New `agent-process agent_identity --bot <login> (--dry-run | --confirm)`. The person runs it
  once per repository and clone. It:
  - checks that the bot's `gh` token belongs to that login and is not an admin;
  - invites the bot as a collaborator and accepts the invitation with the bot's token;
  - gives the bot write access to the linked Project;
  - writes `GH_TOKEN` into this clone's git-ignored `.claude/settings.local.json`, and routes
    the clone's git credentials to `gh`;
  - converges a ruleset `agent-process person approves`, which requires one approval on the
    default branch and dismisses stale approvals, with no bypass.
- Each Claude session start whose `GH_TOKEN` is not the clone's prints
  `agent-process agent identity not set`.
- **BREAKING** The plugin's git guard is removed, with its hook entry and tests.
- The release workflow approves the release PR with `GITHUB_TOKEN` before enabling auto-merge.
  This repository allows GitHub Actions to approve pull requests.
- `SKILL.md` Install gains the identity step; the guard paragraph goes. ADR 0040 records the
  decision; ADR 0031 D4 is amended.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`:
  - adds "Agent identity converges" and "A Claude session start reports a missing agent
    identity";
  - removes "The plugin ships the git guard";
  - in "Releases go through release-please", the workflow approves the release PR before
    enabling auto-merge.
- `review-and-merge`: "Local safety in Claude Code" is removed; the new "The person approves"
  places the boundary in the ruleset instead of the local guard.

## Impact

- Added:
  - `skills/agent-process/scripts/agent_identity.py`
  - `skills/agent-process/templates/approval_ruleset.json`
  - `tests/publisher/test_agent_identity.py`
  - `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md`
- Edited:
  - `skills/agent-process/scripts/activate_protection.py`: `plan` takes the ruleset name from
    the body, so the new script reuses it.
  - `skills/agent-process/templates/skill_check.py`, `tests/publisher/test_skill_check.py`
  - `.github/workflows/release-please.yml`, `tests/publisher/test_reusable_workflows.py`
  - `hooks/hooks.json`, `tests/publisher/test_plugin.py`, `tests/publisher/test_start_change.py`
  - `tests/agent_process/test_delivery_gate_wiring.py` (docstring)
  - `tests/publisher/test_activate_protection.py`
  - `skills/agent-process/SKILL.md`
  - `.agent-process/docs/adr/0031-release-prs-merge-without-the-person.md`
- Removed: `skills/agent-process/scripts/git_guard.py`, `tests/publisher/test_git_guard.py`.
- Before merging, the person allows GitHub Actions to approve pull requests in this repository.
  After the merge, the person creates the bot account and runs `agent_identity` in this
  repository. Until then the session-start marker shows that the identity is not set up.
- The throwaway repository `ekolvah/agent-process-sandbox-restrict-updates` is left for the
  person to delete: the agent's token has no `delete_repo` scope.
