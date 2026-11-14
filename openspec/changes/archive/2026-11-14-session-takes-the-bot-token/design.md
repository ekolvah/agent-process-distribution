## Context

ADR 0040 D3 keeps the agent's `GH_TOKEN` in each clone's git-ignored
`.claude/settings.local.json`, copied there by the person (Install step 6). The installed skill
check (`.claude/agent-process-check.py`, from `templates/skill_check.py`) reports
`agent-process agent identity not set` unless the session's `GH_TOKEN` equals that copy;
`init`'s `manual agent-identity` row reads the copy's permission. The plugin's own
`SessionStart` hook, `plugin_env.py session-start`, already exports `AGENT_PROCESS_PYTHON`
through `CLAUDE_ENV_FILE` and, in a project with the agent-process block, reports release drift.

## Standard approach

Claude Code's `SessionStart` hooks get `CLAUDE_ENV_FILE`; the lines appended to it are sourced
before each Bash command (<https://code.claude.com/docs/en/hooks>), which `plugin_env.py`
already relies on. `gh auth token --user <login>` prints the stored token of that account
(<https://cli.github.com/manual/gh_auth_token>). `git config` is git's key/value store, where a
clone's value overrides the global one (<https://git-scm.com/docs/git-config>). All three are
observed in proposal **Why**.

## Decisions

### D1 — the plugin's session-start hook exports the token

`plugin_env.py session-start`, behind the same gate as its drift check (the agent-process
block in `openspec/config.yaml` of `CLAUDE_PROJECT_DIR`), calls one function of `manual.py`,
`agent_token(run)`, which in the project reads `git config --get agent-process.bot`, runs
`gh auth token --user <bot>`, and reads `gh repo view --json viewerPermission` with
`GH_TOKEN=<token>`; it returns the token when that permission is `WRITE` or `MAINTAIN`, or the
reason otherwise. The hook then appends `export GH_TOKEN=<shlex.quote(token)>` to
`CLAUDE_ENV_FILE`. The token is in no output. Failure (unset key, `gh`'s non-zero exit or empty
stdout, another permission or an unreadable one, no `CLAUDE_ENV_FILE`, `gh` or `git` missing) is
one line in the hook's existing JSON: `agent-process agent identity not set (<reason>) — fix:
Install step 6 of the agent-process skill, then restart Claude Code` (§IV). `agent_token` names
one reason per failure: `git config agent-process.bot is not set`, `gh holds no token for
<bot>`, `<bot> has <permission> permission on the repository, not WRITE or MAINTAIN`, or
`cannot read <bot>'s permission`; where `gh` printed to stderr, its first line follows after
`: `. A missing `CLAUDE_ENV_FILE`, `gh` or `git` is named as such. `run` is an injected `typing.Protocol` (§II), so
unit tests use an in-memory double; `manual` already loads with the standard library alone,
as `init` does after the same gate.

The permission check keeps the global key of D2 from making the bot the identity where it
cannot act: in another owner's repository, or before the bot accepts its invitation, the
session runs as `gh`'s active account, the person, and prints the marker, as today. It costs
one GitHub read per session start in a project with the block; observed on 2026-11-14,
`gh repo view --json viewerPermission` printed `WRITE` for the bot's token on this repository.

Only Bash sees the export: the agent's `gh`, `git push` through `gh auth git-credential`, and
`agent-process` scripts all run there. A session started in a worktree under
`.claude/worktrees/` runs the same hook and reads the same global key, which closes ADR 0040
D3's worktree gap.

Alternatives:
- Keep the token in each clone and have the agent write it (the previous plan of this change):
  per-clone step, stale copies, worktree gap stay; rejected by the person on 2026-11-14.
- Export from the installed skill check: reaches consumers only at their next `init` upgrade,
  where the plugin reaches them with the release.
- `env.GH_TOKEN` in user-scope settings: every session on the machine, in every repository,
  would act as the bot (ADR 0040 D3).

### D2 — the bot's login is a git config key

`agent-process.bot` is set once per machine by step 6 (`git config --global`), and a clone can
override it for a repository with another bot. It is not a secret, needs no installer change,
and every clone and worktree reads it. Step 6 skips it when it is already set; otherwise the
agent takes the bot from `gh auth status`: Prepare logs in the bot, then the person, so the bot
is the one github.com keyring account `gh` does not show active. With none or several such
accounts (a third login, or a `GH_TOKEN` in the session that makes every keyring account
inactive) the agent asks the person for the login, a problem case.
Alternatives: an `init --bot` argument written into the committed hook command (installer
change, upgrade path for the value); the hook guessing the bot at every session start
(ambiguous with a third account, where step 6 asks once).

### D3 — the skill check drops its identity check

Both `SessionStart` hooks run for one event and the skill check cannot see the plugin's export,
so its comparison would fire on every session. `_identity`, `IDENTITY_MARKER`, `IDENTITY_FIX`
and `LOCAL_SETTINGS` leave `templates/skill_check.py`; the marker moves to `plugin_env.py`,
which uses `manual.IDENTITY_FIX`, so the publisher test that held the template's copy of the
fix equal to `manual`'s goes.

### D4 — `init`'s row reads what the hook reads

`_identity_pending` calls `agent_token` of D1 with a runner over `Target.git` and `Target.gh`,
so the row names the same reasons as the marker (D1); an unreadable permission stays
`(cannot read: <reason>)`. The row becomes
`manual agent-identity: once the installation PR has merged`. `SETTINGS` and `PERMISSION_QUERY`,
used only here, go; `_settings_env` stays for the attribution row.

### D5 — step 6 asks nothing; step 2 shows its commands

The person decided that the merge of the installation PR is the consent to step 6 and that the
person sees every command up front. Step 2, when the dry-run prints the `manual agent-identity`
row, shows step 6's commands with the dry-run's output. Step 6 runs them after the merge without
asking and shows the person a command that fails, with its output, and the steps only the
person can do: the bot accepting the invitation, the Project's access setting, the restart. Per
machine it runs `gh auth setup-git` and `git config --global agent-process.bot <bot>` (D2); the
per-repository commands are unchanged; the per-clone copy is gone. They still run as the
person: the session has no bot token until the bot holds write on the repository (D1), which
the bot's acceptance gives only after the session started. The asks of steps 3 and 5,
including step 3's ask on a printed `manual agent-identity` row, are not this change's.

## Risks / Trade-offs

- [Each session leaves a plain-text copy of the bot's token in
  `~/.claude/session-env/<session>/`, which Claude Code keeps after the session (proposal
  **Why**)] → accepted: the same profile directory as `gh`'s own configuration, outside every
  repository, where today's copy sits one `git add -f` from a commit. Not mitigated here.
- [A clone keeps a stale `env.GH_TOKEN` in its local settings] → the export overrides it in Bash
  (observed); the hook's own `gh` reads set their `GH_TOKEN` or need none. When the hook exports
  nothing, Bash keeps the stale copy and step 6's commands fail as that account, shown under
  D5. The person may delete it. This repository has no agent-process block and keeps its copy.
- [Auto mode's classifier refuses a per-repository command of step 6] → plausible: on 2026-11-14
  it refused, as `[Unauthorized Access]`, this planning session's headless launch of
  `gh api -X PUT …/collaborators/ekolvah-agent -f permission=push` and
  `gh repo edit --enable-auto-merge` with `GH_TOKEN` removed. A refusal is a failed command under
  D5: the agent shows it, and the person runs the same line in their own terminal, outside
  Claude Code, where no session export applies and `gh` runs as its active account, the person.
- [A session start without network access or with a slow GitHub] → the permission read fails;
  the hook exports nothing and prints the marker with `gh`'s reason, and the session runs as
  the person until the next start. The read adds its latency to each session start in a
  project with the block.
- [An existing consumer with the old skill check and its settings copy] → that check stays silent
  while the copy matches; the plugin's hook marks the identity until the person sets
  `agent-process.bot`, which the marker's fix names.

## Migration Plan

On a machine already set up: `git config --global agent-process.bot <bot>`, then restart
Claude Code. A clone's `env.GH_TOKEN` in its local settings may go only after that clone's next
`init` upgrade: the old skill check compares the session's `GH_TOKEN` with it and, without it,
prints `agent-process agent identity not set` at every session start. The release notes name
both.
