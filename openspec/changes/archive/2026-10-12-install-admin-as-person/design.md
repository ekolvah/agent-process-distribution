## Context

`run_gh` (`skills/agent-process/scripts/set_status.py`) runs `gh` with the caller's
environment and is the default `gh` of every script; `agent_identity.bot_gh` runs the bot's
calls through it with `GH_TOKEN` set to the bot's token.

## Goals / Non-Goals

**Goals:** the two admin steps read and write as the person in a clone whose sessions carry
the bot's `GH_TOKEN`, with no step the person runs by hand.

**Non-Goals:** `init` (it needs no admin read in a configured clone: the bot lists the
repository's secrets — observed, `gh secret list` as `ekolvah-agent` returned 3 names), and
any check of which account `gh` holds active.

## Decisions

### D1 — Drop the env tokens; `gh` falls back to the stored active account

The person runner is `run_gh` with an environment copied from the process minus `GH_TOKEN`
and `GITHUB_TOKEN`. `gh help environment`: both, "in order of precedence", take "precedence
over previously stored credentials" — so without them `gh` uses the stored active account,
which Install step 6 leaves as the person (`gh auth switch --user <person>`). Observed above:
`env -u GH_TOKEN gh api user` → `ekolvah`, and that view reads `bypass_actors: []`.

`GH_ENTERPRISE_TOKEN` stays: it applies only to a GitHub Enterprise Server host, not to
`github.com`.

Alternatives:
- Read the person's token (`gh auth token`) and pass it as `GH_TOKEN` — one more call and a
  second token in memory for the same result.
- Make the bot an admin — rejected in the issue: an admin can disable the approval ruleset,
  and `agent_identity` refuses an admin bot.
- Ask the person to run steps 5 and 6 outside Claude Code — breaks the unattended re-run the
  issue asks for.

No new script or check: one runner beside `run_gh`, used by two `main` defaults.

### D2 — The runner lives in `set_status.py`, the defaults change in two `main`s

`person_gh` sits next to `run_gh`, which both scripts already import. It becomes the default
`gh` of `activate_protection.main` and `agent_identity.main`; `agent_identity` keeps passing
`bot_gh(token)` for the bot side. `run_gh` itself is unchanged, so the agent-side scripts
(`start_change`, `set_status`, `create_tracking_issue`, …) keep the bot's identity.

### D3 — ADR 0040 gains D6, not a new ADR

ADR 0040 already accepts that the agent can drop `GH_TOKEN` and fall back to the person's
keyring token. The admin steps now use that limit on purpose, still behind `--dry-run` and the
person's yes to `--confirm`; D6 records it and the Confirmation names the test. The deletion
condition is unchanged.

### D4 — In this repository, `--confirm` asks the person

Here the launcher prefers `skills/agent-process/scripts/<name>.py` of the current checkout, so
`--confirm` writes as admin what the agent's working copy of the scripts and templates plans.
`.claude/settings.json` gains
`"ask": ["Bash(*activate_protection* --confirm*)", "Bash(*agent_identity* --confirm*)"]`
beside its `deny`. The permissions documentation: ask rules "apply when any subcommand
matches them … even in auto mode". `--dry-run` reads only and stays unprompted.

It guards the intended invocation, not an agent avoiding it (an abbreviated flag or a copied
script passes) — the limit ADR 0040 already accepts. No spec requirement: it is this
repository's configuration, not distributed behaviour; in an adopting repository the launcher
runs the released plugin's scripts. `init` leaves `permissions` alone while the file keeps
its `_json_text` form.

## Risks / Trade-offs

- New input: the stored active account instead of the session's token. Failure modes and
  their catchers:
  - The active stored account is the bot (the person skipped `gh auth switch`): the runs read
    as the bot again; `activate_protection --dry-run` prints `planned … bypass_actors: null -> []`
    and `--confirm` exits 1 with the 404, as today — visible, not silent.
  - No stored account: `gh` exits non-zero, `run_gh` raises, the script exits 1 naming the
    command.
- What stops proving: nothing the scripts proved before; the session's `GH_TOKEN` was never a
  declared input of the admin steps.
- Migration and rollback: none; reverting the commit restores the old default.
