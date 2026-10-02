## Context

See proposal.md — Why. Today `.agent-process/scripts/navigation_policy.py` holds the parser
and the read budget, `.agent-process/scripts/hooks.py` adapts them (`pre-bash`, `pre-read`)
beside `on-edit`, and this repository's `.claude/settings.json` wires all three with
`cd "$CLAUDE_PROJECT_DIR" && python .agent-process/scripts/hooks.py <name>`. The launcher
`bin/agent-process` runs `skills/agent-process/scripts/<name>.py` of the current directory when
it exists, else the plugin's copy, with `exec python`.

Platform facts this design rests on ([hooks](https://code.claude.com/docs/en/hooks),
[permissions](https://code.claude.com/docs/en/permissions)):

- "When a plugin is enabled, its hooks merge with your user and project hooks."
  `${CLAUDE_PLUGIN_ROOT}` is "the plugin's installation directory"; `${CLAUDE_PROJECT_DIR}` is
  "the project root where the session started".
- The shell "Defaults to `"bash"`, or to `"powershell"` on Windows when Git Bash isn't
  installed." Observed in this repository's sessions on Windows: the settings hook
  `cd "$CLAUDE_PROJECT_DIR" && python …` runs and denies `ls`/`grep`.
- "Any other exit code doesn't block … the transcript shows a `<hook name> hook error`
  notice"; "A timed-out … hook doesn't block the tool call."
- "Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns: a
  matching deny rule blocks the call" — and "That precedence covers hooks in settings files and
  in a plugin's `hooks/hooks.json`."

Observed on 2026-10-02 (Windows, Git Bash):

- `claude -p … --plugin-dir <probe> --model haiku --allowedTools Bash`, run in a scratch project,
  with a probe plugin whose `hooks/hooks.json` is `{"hooks": {"PreToolUse": [{"matcher": "Bash",
  "hooks": [{"type": "command", "command": "cd \"$CLAUDE_PROJECT_DIR\" && sh
  \"${CLAUDE_PLUGIN_ROOT}/deny.sh\"", "timeout": 10}]}]}}`: the Bash call was denied and the model
  quoted the reason `PROBE-DENY: use the Read tool`; the probe's file recorded
  `pwd=/tmp/…/scratchpad/proj root=C:/Users/…/scratchpad/pv` — the hook ran in the project
  directory with `CLAUDE_PLUGIN_ROOT` set to the plugin directory.
- `claude plugin validate --strict <probe>`: an event declared outside the `"hooks"` object is an
  error ("PreToolUse/PermissionRequest is declared at the top level, outside the "hooks"
  object"), an unknown event a warning ("unknown hook event; entry ignored at runtime").

## Goals / Non-Goals

**Goals:** one copy of the navigation policy, delivered by the plugin, acting only where the
process is installed.

**Non-Goals:**
- A `PowerShell` tool matcher.
- Shipping `on-edit` (ruff, pip-compile and memory reminders are repository-specific).
- Reverting to project-scope install. Revisit the gate and scope when
  anthropics/claude-code#75855 (drive-letter case in `installed_plugins.json` keys) is fixed.

## Decisions

**D1 — The policy moves into the package as a launcher script.**
`git mv` `navigation_policy.py` to `skills/agent-process/scripts/`; `pre_bash_response`,
`pre_read_response` and a `main` (`pre-bash|pre-read`; any other argument → usage, exit 2;
otherwise the deny JSON or nothing, exit 0) move with it. `hooks.py` keeps only `on-edit`.
The file name carries no `hook` token, so the package-contents guard stays as is.
*Alternative:* ship `hooks.py` whole — rejected: `on-edit` is repository-specific and
`hooks.py` would trip the package's `hook` token guard.

**D2 — `hooks/hooks.json` runs the policy through the plugin's launcher.**
PreToolUse matchers `Bash` and `Read`, timeout 10 (as today), command
`cd "$CLAUDE_PROJECT_DIR" && { [ ! -f .github/workflows/agent-process.yml ] || sh "${CLAUDE_PLUGIN_ROOT}/bin/agent-process" navigation_policy pre-bash; }`
(`pre-read` for `Read`). The launcher makes this repository's checkout copy win here
(dogfood) and the plugin's copy win in a consumer. `sh` is named explicitly so the launcher's
execute bit does not matter on Windows checkouts. This supersedes the rejection of plugin hooks in
archived `2026-09-23-architect-review-length-and-bespoke-findings` (design: "keeps hooks out of
the package … would add a hook to every consumer session"): D3 bounds the hook to adopted
repositories, and the test it cited no longer exists.
*Alternative:* the hook in consumer `.claude/settings.json` rendered by `init` — rejected: it
copies a publisher path into every consumer and grows the closed installed footprint; the plugin
is the platform's mechanism for this.

**D3 — Adoption gate in the shell, on the installer's workflow file.**
The marker is `.github/workflows/agent-process.yml`: `init` writes it (`init.WORKFLOW`), the
installed footprint requirement names it, `activate_protection` reads it, and this repository
carries it. `.agent-process/` is publisher-only and cannot mark a consumer. The test runs every
command of `hooks/hooks.json`, so a future plugin hook without the gate fails it.
*Standard:* the platform scopes a plugin by its install scope; at user scope (forced by #75855)
it has no per-project switch except a consumer's own `enabledPlugins: false`, which is opt-out,
not opt-in. Hook `matcher`/`if` filters match tools and arguments, not the project.

**D4 — This repository's settings drop the PreToolUse `Bash`/`Read` entries.** Otherwise both
the settings hook and the plugin hook run. *Lost proof:* the settings entries were observed to fire in this
repository's sessions; the plugin file is not, until a release is installed. Catchers: the
live probe above shows the platform loads and runs a plugin PreToolUse hook of this shape; the
group-1 tests read `hooks/hooks.json` through its `"hooks"` envelope and run each command of the
checkout, so a broken envelope, matcher or command fails `ci_check` on the PR head; a settings
test asserts no PreToolUse `Bash`/`Read` entry is left. Not caught: a machine still on a release
without `hooks/hooks.json` — the SessionStart check compares no version, so nothing reports it;
the marketplace follows `stable` with auto-update on, so a machine that did the
`plugin-channel` row gets the release within a session (SKILL.md Install), and until then the
navigation hooks are absent (first Risk).

**D5 — No stat fast path in `read_budget_hint`.** Proposed in the issue discussion, dropped: a
`stat` shortcut would skip only reads of files within the 28 KB budget (an over-budget file is
read whole either way to compute the slice that fits), gives the same verdicts, and no observed
cost asks for it (§VII).

**D6 — Interpreter stays `python`.** The launcher (`exec python`) and the consumer's
SessionStart check (`python …/agent-process-check.py`) already require `python` on `PATH`; a
`python3` fallback in one hook would make the requirement inconsistent, not lighter. Without
`python` the hook exits non-zero: a visible, non-blocking `hook error` (implementation
requirement "A broken hook is visible"). The gate runs before Python, so a non-adopted
repository never needs it.

**D7 — SKILL.md Install documents the hooks** in one sentence of its plugin paragraph: they act
in a repository carrying `.github/workflows/agent-process.yml`, and a consumer
`permissions.deny` rule matching the same command blocks first, so the hook's replacement
message never reaches the agent.

**D8 — An unknown `hooks.py` subcommand exits 1, not 2.** Observed on the first reviewed head of this
change's PR (#319): the review job restores `.claude/` from `main` ("Restoring .claude … from origin/main (PR head is
untrusted)") and runs the PR head's scripts, so `main`'s `hooks.py pre-bash` reached a
`hooks.py` that knows only `on-edit`; its usage exit 2 is a PreToolUse block, the reviewer's
`gh pr diff` was denied twice (`permission_denials_count: 2`) and no review was posted. Settings
and the script they call can come from different revisions, so an argument the script does not
know is a broken hook, not a denial: exit 1 is the visible, non-blocking `hook error`
("Any other exit code doesn't block"), which satisfies implementation requirement "A broken
hook is visible".

No ADR: this is a delivery mechanism of an existing policy; its record is this design and the
distribution delta.

## Risks / Trade-offs

- [The publisher's `hooks/hooks.json` acts only after a release is installed] → between the merge
  and the machine's update this repository runs without navigation hooks; tests run the
  checkout's `hooks.json` commands, so the shipped file is verified before release.
- [Machine without Git Bash: hooks run under PowerShell and the POSIX gate errors on every
  `Read`] → the process already requires Git Bash (the launcher is `sh`, the SessionStart
  command uses `$CLAUDE_PROJECT_DIR`); the error is visible, never blocking.
- [Consumer `permissions.deny` for `cat`/`grep`] → the call is still blocked, only without the
  replacement named; documented by D7.
- [Every `Bash`/`Read` call in any project spawns `sh` for the gate] → a file test, no Python;
  timeout 10 keeps a stall from blocking.

## Migration Plan

Release ships the hooks; auto-update brings them to machines on `stable`. A consumer with its
own copy wired in settings runs both — same verdicts — until it removes the copy
(ekolvah/kinozal_scraper#612). Rollback: revert the PR and release; settings entries return.
