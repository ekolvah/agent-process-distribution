## Why

Install step 6 has the person copy `gh auth token --user <bot>` into `env.GH_TOKEN` of
`.claude/settings.local.json` by hand, once per clone: one more hand-off, a chance to paste the
person's token, a copy that goes stale when the bot's token changes, and a session started in a
worktree under `.claude/worktrees/` runs as the person (ADR 0040 D3). The token already lives once
per machine, in `gh`, after Prepare's bot login. The person decided on 2026-11-14 that a session
takes it from there, so no clone holds it, and that step 6 asks nothing: the person sees its
commands with the plan of step 2, the merge of the installation PR is the consent, and the agent
interrupts only when something fails.

Observed on 2026-11-13/14 (gh 2.87.3, Claude Code 2.1.296, Git for Windows):
- `gh auth token --user ekolvah-agent` printed a 40-character token, the same with
  `GH_TOKEN=dummy-value` in its environment; for an unknown login it printed
  `no oauth token found for github.com account …` and exited 1.
- `git config --get agent-process.bot` exits 1 where the key is not set.
- `gh repo view --json viewerPermission` printed `WRITE` with the bot's token on this repository.
- A headless `claude -p` in a throwaway repository whose project `SessionStart` hook appended
  `export GH_TOKEN=<gh auth token --user ekolvah-agent>` to `CLAUDE_ENV_FILE`, and whose
  `.claude/settings.local.json` held `env.GH_TOKEN: "stale-not-a-token"`, ran
  `gh api user --jq .login` in Bash as `ekolvah-agent`, with a 40-character `GH_TOKEN`, no
  permission denial.
- The plugin's `plugin_env.py` already exports `AGENT_PROCESS_PYTHON` the same way.
- Claude Code keeps each session's exports in `~/.claude/session-env/<session>/`, after the
  session ends (217 directories on this machine).

## What Changes

- The plugin's session-start hook, in a project with the agent-process block, exports
  `GH_TOKEN` from `gh auth token --user <bot>` through `CLAUDE_ENV_FILE`, the bot being
  `git config agent-process.bot`, when that token has write on the repository. Otherwise it
  prints `agent-process agent identity not set` with the reason and the fix, as the skill check
  does today, and the session runs as the person.
- The installed skill check (`.claude/agent-process-check.py`) drops its identity check: it
  runs beside that hook and cannot see its export.
- `init`'s `manual agent-identity` row reads what the hook reads, through the same function,
  instead of `env.GH_TOKEN` of `.claude/settings.local.json`.
- Install step 2 shows, with the dry-run, the commands step 6 will run after the merge while
  the dry-run prints the `manual agent-identity` row. Step 6 runs them without asking and
  interrupts the person only for a command that fails and the steps only the person can do. Its
  per-clone token copy is gone; per machine it gains `git config --global agent-process.bot <bot>`,
  the bot taken from `gh auth status`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: "A Claude session start reports a missing agent identity" becomes "A Claude
  session start takes the agent's token"; "Install reports a pending agent identity" reads the
  token from `gh`; adds "Install's identity step asks nothing".

## Impact

- Edited: `skills/agent-process/scripts/plugin_env.py`, `skills/agent-process/scripts/manual.py`,
  `skills/agent-process/templates/skill_check.py`, `skills/agent-process/SKILL.md` (Install steps
  2 and 6), `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` (D1, D3, D5,
  D6, Consequences, Confirmation).
- Tests edited: `tests/publisher/test_plugin.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/init_harness.py`, `tests/publisher/test_skill_check.py`,
  `tests/publisher/test_planning_workflow.py`.
- Specs: `openspec/specs/distribution/spec.md`. No dependency.
- Consumers: the plugin part reaches them with the release; the skill check's part with their
  next `init` upgrade. A clone that keeps `env.GH_TOKEN` in its local settings still works; the
  export overrides it in Bash.
