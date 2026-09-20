# Agent-process installation

**Question this document answers:** How does a person bootstrap, install, update, verify,
and roll back agent-process 2.0 in a consumer repository?

Installation is separate from per-issue delivery. It needs Node/`npx`, Python 3.12 or
newer, `git`, authenticated `gh`, Claude Code, and Codex. The portable plugin ships no
hooks and the repository receives no Python control-plane copy.

## Bootstrap the shared skill once

Claude Code can bootstrap from the marketplace:

```text
/plugin marketplace add ekolvah/agent-process-distribution
/plugin install agent-process@agent-process-marketplace
```

Then run `/agent-process:init` and supply the target repository's complete test command
plus an optional setup command.

For the first Codex bootstrap, before the user-level link exists, check out the immutable
release and create the link explicitly. On Unix:

```bash
git clone --filter=blob:none --branch v2.0.0 --single-branch https://github.com/ekolvah/agent-process-distribution.git "$HOME/.agent-process/distribution"
mkdir -p "$HOME/.agents/skills"
ln -s "$HOME/.agent-process/distribution/skills/agent-process" "$HOME/.agents/skills/agent-process"
```

On Windows PowerShell:

```powershell
git clone --filter=blob:none --branch v2.0.0 --single-branch https://github.com/ekolvah/agent-process-distribution.git "$env:USERPROFILE\.agent-process\distribution"
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\agent-process" "$env:USERPROFILE\.agent-process\distribution\skills\agent-process"
```

Review the checked-out `SKILL.md`, restart Codex so it discovers the linked skill, and run
its install procedure. `init` normalizes the same checkout and link; it refuses a dirty
checkout or foreign link before fetching or selecting a tag.

## Run the installer

From the consumer repository, first show the complete plan without writing:

```bash
python "$HOME/.agents/skills/agent-process/scripts/init.py" --setup "python -m pip install -r requirements.txt" --test "python -m pytest" --dry-run
```

On Windows, use the corresponding `%USERPROFILE%` or PowerShell path. After reviewing the
plan, authorize the local and remote composition once:

```bash
python "$HOME/.agents/skills/agent-process/scripts/init.py" --setup "python -m pip install -r requirements.txt" --test "python -m pytest" --confirm-remote
```

The literal setup/test strings are YAML-escaped, so multiline shell commands remain one
caller input. An empty test command is refused. Every subprocess capture is UTF-8; an
unavailable stdout or stderr is an error rather than an empty result.

## Exact repository footprint

Pinned `npx -y @fission-ai/openspec@1.13.0 init --tools claude,codex --no-animation`
owns these generated families:

- `.claude/commands/opsx/{apply,archive,explore,propose,sync,update}.md`
- `.claude/skills/openspec-{apply-change,archive-change,explore,propose,sync-specs,update-change}/SKILL.md`
- `.agents/skills/openspec-{apply-change,archive-change,explore,propose,sync-specs,update-change}/SKILL.md`
- `openspec/config.yaml` and later user-created `openspec/specs/**` and
  `openspec/changes/**`

Agent-process adds or merges only:

- the marker-owned pointer block in `openspec/config.yaml`;
- `.github/workflows/agent-process.yml`;
- the marker-owned GitHub Actions entry in `.github/dependabot.yml`;
- `extraKnownMarketplaces.agent-process-marketplace` and
  `enabledPlugins["agent-process@agent-process-marketplace"]` in
  `.claude/settings.json`.

Outside the repository it keeps `~/.agent-process/distribution` at release tag `v2.0.0`
and links `~/.agents/skills/agent-process` to its skill directory. Remote state is one
active repository ruleset and zero or one linked copy of user Project 4.

No `.agent-process/`, hook, `AGENTS.md` fragment, review contract, report-path convention,
process script, or process test is installed in the consumer. An unmarked conflicting
`rules:` block, workflow, Dependabot file, malformed marker pair, foreign skill link,
dirty checkout, duplicate process ruleset, or several linked Projects is a visible
conflict; the installer leaves consumer-owned content unchanged.

## Remote writes and person-owned actions

With `--confirm-remote`, `init` upserts the uniquely named active ruleset, reads it back,
and verifies that it targets the default branch, has no bypass actor, blocks deletion and
non-fast-forward updates, requires a pull request, and strictly requires
`quality / quality` from GitHub Actions integration 15368.

If no Project is linked, it runs `gh project copy 4 --source-owner ekolvah --target-owner
@me --format json` and links the copy. One linked Project is reused; several stop the run.
The script intentionally does not inspect or mutate Project fields, views, visibility, or
workflow switches.

The command prints these remaining actions for the person and does not perform them:

1. Run `gh secret set CLAUDE_CODE_OAUTH_TOKEN` and enter the value directly into `gh`.
2. Enable Codex automatic review for PR open and every push in the Codex GitHub settings.
3. Set the Project's intended visibility and verify the built-in workflows for Auto-add,
   Item added, Item reopened, Item closed, and Pull request merged.

The secret value and UI decisions never enter `init` output or arguments.

## Advisory review and workflow trust

The one caller invokes the tagged reusable quality workflow and calls
`anthropics/claude-code-action@v1` directly. Codex automatic review is independent. Neither
review is required or parsed; failures and comments remain visible for the person.

The required quality context is bound by name and GitHub Actions integration, not by an
authenticated caller definition. Before every merge, inspect the current-head diff of
`.github/workflows/**` and the visible review state. Organization repositories may add a
required-workflow ruleset as a stronger external trust anchor. Do not move a credentialed
review to `pull_request_target`.

## Repeat, update, and partial recovery

Rerunning the same version is idempotent. Completed local files, the correct link, the
unique ruleset, and one linked Project are reported unchanged or updated without
duplication. If a later step fails, fix the named cause and rerun the same command; earlier
steps are safe to observe again.

For an update, update the Claude plugin, then run the existing linked skill's `init.py`
with the new `--version`. It checks that the checkout is clean, fetches tags, selects the
new immutable tag, updates the caller/reference and settings, and re-reads remote state.
Dependabot independently proposes GitHub Actions reference updates for review.

## Rollback

Rollback is ordered so the default branch never loses a required context:

1. Restore the previous caller and any previous classic required context before removing
   or disabling the new caller.
2. Verify that the restored context is green on the rollback PR head.
3. Point the Claude plugin and Codex checkout back to the previous immutable tag; never
   move or reuse a release tag.
4. Restore the previous skill link only if its resolved target is known; never replace a
   foreign path.
5. After protection is restored, delete the uniquely identified process ruleset with
   `gh api --method DELETE repos/OWNER/REPO/rulesets/ID` if rollback requires it.
6. Unlink or delete a copied Project only after the person confirms it contains no unique
   item state; Project deletion is destructive and is not automated by `init`.

Repository files not owned by the closed allow-list are never rollback targets.
