## ADDED Requirements

### Requirement: The plugin ships the git guard
The plugin's `PreToolUse` hook for the `Bash` tool SHALL deny a command when any of its stages,
including one behind a shell separator, a process wrapper, `sh -c`, or git's global options
before the subcommand, is one of:
- `gh pr merge` — the reason SHALL say that the person merges;
- `gh repo delete`;
- `git push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes`, a refspec
  starting with `+`, `--no-verify`, or a refspec whose destination is `main`;
- `git commit` with `--no-verify` or `-n`;
- `git reset --hard`;
- `git branch -D`, or `git branch` with both a delete and a force flag.

Each denial SHALL name what to do instead. A command the guard cannot parse that contains `git`
or `gh` as a word SHALL produce a non-blocking hook error saying it was not checked. Every other
command SHALL get no output from the guard. This repository's `.claude/settings.json` SHALL declare no `permissions.deny` entry
that matches a guarded command.

#### Scenario: Guarded command in an adopted consumer
- **WHEN** the plugin's `PreToolUse` `Bash` hooks run with a project directory that carries `.github/workflows/agent-process.yml` and no copy of the guard, for each guarded command, alone and after `cd x &&`, under `sh -c`, and with `git -C .` before the subcommand
- **THEN** the call is denied and the reason names the alternative

#### Scenario: Ordinary git command
- **WHEN** the guard runs for an unparseable command without `git` or `gh`, `git push -u origin feature`, `git push origin HEAD`, `git branch -d feature`, `git reset --soft HEAD~1`, `git commit -m "skip --no-verify"`, or `gh pr view 1`
- **THEN** it exits 0 with no output

#### Scenario: Unparsed git command
- **WHEN** the guard runs for a command with an unbalanced quote that contains `git`, such as a heredoc commit whose body has an apostrophe
- **THEN** it exits 1 with `not checked` on stderr and no stdout, so the call proceeds and the hook error is visible

#### Scenario: Repository settings carry no guard deny
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** no `permissions.deny` entry matches a guarded command, so the guard's reason reaches the agent
