## Context

The plugin's one `SessionStart` hook (`hooks/hooks.json` → `plugin_env.py session-start`)
installs the runtime environment and prints a marker JSON only on failure. `init.release_drift`
already holds the comparison, both fix texts and the publisher-checkout exemption that
`start_change` and `finish_propose` use.

## Standard approach

- Claude Code hooks reference, SessionStart output: `systemMessage` for the person and
  `hookSpecificOutput.additionalContext` for the agent — https://code.claude.com/docs/en/hooks.
  `plugin_env.py` and the skill check already use this carrier.
- none found: a standard updater of installer-managed repository files. Dependabot bumps the
  consumer's `uses:` refs, not the files `init` writes or the release line; Claude Code's plugin
  auto-update covers only the plugin cache.

## Decisions

1. **The plugin's hook, not the repository's skill check.** Problem: issue 484. The skill check
   is the copy `init` wrote, so a drifted repository runs the old copy and would stay silent; the
   plugin's hook runs from the cache at the installed release. Rejected: a new hook (a second
   `SessionStart` entry for the same moment) and a network call to `stable` (the issue excludes
   it; the installed release is what `start_change` compares against).
2. **Reuse `init.release_drift(project, Path(__file__).parent)`.** One comparison and one
   message for the session and the backstop. `init` imports only the standard library
   (observed: `python -c "...import init; print([m for m in ('jsonschema','yaml','markdown_it') if m in sys.modules])"`
   prints `[]`; `-X importtime` reports 175 ms cumulative), so it runs before the environment
   exists. The import is inside the drift reader, after the gate. A publisher test imports `init` under `python -I -S`, so a
   third-party import added to its chain fails CI instead of printing `cannot check` at every session start.
3. **Gate on `# agent-process:begin` in `openspec/config.yaml` of the project directory.** The project directory is `CLAUDE_PROJECT_DIR`, else the current directory, as `skill_check.py` reads it; the hooks reference documents `CLAUDE_PROJECT_DIR` for hook commands, and the plugin's tool hooks in `hooks/hooks.json` already `cd` into it. `init` writes that block in
   every installed repository; the publisher's config has none (`grep -c` → 0) although it has
   `.github/workflows/agent-process.yml`, and `release_drift`'s own exemption does not fire from
   the plugin cache. A block without a release line is an old install and is reported.
4. **The drift message names `/agent-process:init`.** The issue asks for it; changing the text
   in `release_drift` keeps the session marker and `start_change` one text. The path to the
   Install anchor of `SKILL.md` stays for a runner without the command.
5. **One output JSON.** The environment marker and the drift marker are joined as the skill
   check joins its markers: one `systemMessage` line each, `additionalContext` concatenated. A
   failure of the drift reader is caught and printed as the marker with `cannot check: <reason>`
   (§IV); the environment install runs regardless.

## Risks / Trade-offs

- [175 ms more at every session start of an installed repository] → within the hook's 300 s
  timeout; the environment install already dominates a first start.
- [The marker repeats every session until the person runs the fix] → intended; it is the trigger
  the repository files lacked.

## Migration Plan

Reaches every consumer with the plugin's auto-update; no repository change. Rollback is
reverting the PR; the hook keeps no new state.
