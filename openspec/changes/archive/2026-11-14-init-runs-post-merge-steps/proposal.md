## Why

After the installation PR merges, Install steps 5 and 6 still ask the person twice and hand
them work the agent can do: step 5 asks before `activate_protection --confirm`; step 6 asks
before the identity commands, then leaves the bot's invitation, the Project's Writer role and
the clone's `env.GH_TOKEN` to the person. All of it follows from the one decision to install
the process, which the person already gives once, before the first `init --confirm`. The goal is
the least person involvement: the merge is the person's consent, and after it only the restart
of Claude Code stays with the person. Each write has a platform API, observed in design.md, Standard approach.

## What Changes

- New step module `post_merge`: once the installation PR of its release reads `MERGED`, a
  confirmed `init` writes `protection`, and, for the agent account, `agent-collaborator`
  (invite, then accept as the bot), `agent-project` (Writer of the linked Project),
  `approval-ruleset`, `auto-merge` and `agent-token` (the clone's git-ignored
  `env.GH_TOKEN`, never printed). Before that merge each outstanding one prints `after-merge`
  and writes nothing.
- The agent account is the one github.com account `gh auth status` lists besides the person's;
  `--agent <login>` chooses among several, and none leaves the `manual agent-identity` row.
- **BREAKING** (output): the `manual protection` and `manual auto-merge` rows go; the
  `manual agent-identity` row prints only without an agent account.
- Install asks no question: after a dry-run that exits 0 the agent runs `--confirm` unasked,
  and the person's merge of the installation PR, whose body lists the `after-merge`
  transitions, is the consent. After any merge the agent runs `init --confirm` again unasked,
  then `gh auth setup-git`, and asks the person to restart Claude Code when the token was
  written. Steps 5 and 6 become one step 5.
- ADR 0040: D1, D6, D7 and the deletion condition name the transitions instead of the runbook.

## Capabilities

### New Capabilities

### Modified Capabilities

- `distribution`: post-merge transitions and the agent account; the remote-write list; the
  identities of the calls; the identity row; the removed rows; Install's continuation and
  consent; the session-start identity fix.
- `review-and-merge`: the Install sentence about auto-merge goes.

## Impact

Added:

- `skills/agent-process/scripts/post_merge.py` — the six steps, over `manual.Target`

Edited:

- `skills/agent-process/scripts/init.py` — `--agent`, calls `post_merge.steps`, docstring
- `skills/agent-process/scripts/onboarding.py` — the installation PR's body lists the
  `after-merge` transitions, rewritten on a rerun when they change
- `skills/agent-process/scripts/manual.py` — rows `protection` and `auto-merge` removed, the
  identity read takes its token, the identity row only without an agent account,
  `IDENTITY_FIX` names step 5
- `skills/agent-process/templates/skill_check.py` — its copy of the fix
- `skills/agent-process/SKILL.md` — Install steps 2–6
- `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md`
- `tests/publisher/init_harness.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/test_planning_workflow.py`, `tests/publisher/test_skill_check.py`

Removed: none.
