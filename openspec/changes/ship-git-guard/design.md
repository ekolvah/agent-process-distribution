## Context

See proposal.md — Why. The plugin's `hooks/hooks.json` runs one `PreToolUse` `Bash` hook,
`navigation_policy pre-bash`, behind the adoption gate
`[ ! -f .github/workflows/agent-process.yml ] || sh "${CLAUDE_PLUGIN_ROOT}/bin/agent-process" …`
(archived `2026-10-02-ship-navigation-hooks`, D2–D3). `navigation_policy.py` already splits a
command into stages with `shlex` (separators, process wrappers, `sh -c` recursion up to depth 3)
and denies with `hookSpecificOutput.permissionDecision: "deny"`, fail-open on a lexer error.
This repository's `.claude/settings.json` still carries the static git deny block.

Platform facts:
- [hooks](https://code.claude.com/docs/en/hooks): all hooks matching an event run in parallel;
  exit 0 with `permissionDecision: "deny"` blocks and shows the reason to the agent; any other
  non-2 exit or a timeout does not block; "When multiple PreToolUse hooks return different
  decisions, precedence is `deny` > `defer` > `ask` > `allow`."
- [permission modes](https://code.claude.com/docs/en/permission-modes), auto mode, "Blocked by
  default": "Force push"; "`git reset --hard` … which the classifier presumes would discard
  uncommitted changes"; "Merging a pull request no human has approved". These apply only in auto
  mode, and the person can clear a block by stating intent.
- Observed in this repository's sessions (2026-10-06): the plugin's `navigation_policy` deny
  reached the agent with its message.

## Goals / Non-Goals

**Goals:** every adopted consumer gets the same git guard this repository has, with a message
that names the alternative.

**Non-Goals:**
- A security boundary: the documented bypass forms (`git 'push'`, a variable, `eval`, a script
  file) stay open; the server boundary is the agent's identity (#357).
- `sleep`, `rm -rf`, or any command outside the issue's list.
- A configurable list or a per-consumer default branch.

## Decisions

**D1 — Own package script `git_guard.py`.** `main` takes `pre-bash` (any other argument →
usage, exit 1, as D8 of the archived change), reads the payload from stdin, prints the deny JSON
or nothing, exits 0. The name carries no `hook` token, so the package-contents guard holds.
*Alternatives:* a rule in `navigation_policy._RULES` — rejected: that module is "advisory about
cost, never about safety", and mixing the two blurs which message is a hint and which a stop;
shipping the deny block — impossible from a plugin (proposal, Why); relying on auto mode's
built-in blocks — rejected: they act only in auto mode, do not list `--no-verify`, `branch -D`,
a plain push to `main` or `gh repo delete`, yield to a stated intent, and do not name the
process's alternative.

**D2 — One stage walker, two callers.** `navigation_policy` exposes
`first_stage_verdict(command, rule)`: it lexes, splits on separators, strips wrappers, recurses
into `sh -c`, and returns the first non-`None` result of `rule(tokens)`. A lexer error, at the top level or inside
`sh -c`, propagates as `ValueError`: `navigation_policy` catches it and stays silent, `git_guard`
applies D6. Its own `_hint` becomes
a call with the navigation rule, so behaviour is unchanged and `test_navigation_policy.py` proves
it. `git_guard` imports it (sibling imports already work, e.g. `from set_status import …`).
*Alternative:* copy the walker — rejected: two lexers drift, and the `sh -c` hole was fixed once.

**D3 — Git argument model.** Before the subcommand, the guard skips git's global options,
consuming the value of `-C`, `-c`, `--git-dir`, `--work-tree`, `--namespace`,
`--exec-path` (separate or `=`-joined). After it, a long flag is matched by its name before `=`
(`--force-with-lease=main:abc` is `--force-with-lease`), a short flag by its characters (`-fu`,
`-nm`), `--` ends the flags, operands are what remains; a value of `-m`/`-F` for `commit` is not
read as a flag. Push destination: the part after `:` of a refspec, else the refspec itself,
compared to `main` or `refs/heads/main`. `gh` is matched on its first two operands.

**D4 — Messages name the alternative.**

| Command | Reason |
|---|---|
| `gh pr merge` | The person merges: report the PR and wait with `agent-process wait_for_pr`. |
| `gh repo delete` | Deleting a repository is the person's action. |
| `git push` to `main` | Push the branch and open a PR. |
| `git push` force / `+` refspec | Add a commit on top instead of rewriting pushed history. |
| `--no-verify` (push, commit) | Fix what the hook reports; hooks are not bypassed. |
| `git reset --hard` | `git stash` keeps the changes; ask the person before discarding them. |
| `git branch -D` | `git branch -d` deletes a merged branch; ask the person otherwise. |

**D5 — Second hook in the existing `Bash` group.** Same gate, same command form
(`… agent-process git_guard pre-bash`), timeout 10. Both hooks run in parallel and `deny` wins
over every other decision (Context), so the guard's deny holds whatever the navigation hook
returns. *Alternative:* one dispatcher hook running both policies — rejected: it couples two
policies' failure modes in one process.

**D6 — An unparsed command is visible, not silent.** A malformed payload yields no output. A
lexer error (an unbalanced quote, typically a heredoc body with an apostrophe:
`git commit --no-verify -F - <<'EOF'` … `don't`) on a command that contains `git` or `gh` as a
word exits 1 with `git_guard: command not parsed, not checked` on stderr — the visible,
non-blocking `hook error` of implementation requirement "A broken hook is visible". Without
`git`/`gh` the error is silent, as in `navigation_policy`. *Alternative:* deny on a lexer error —
rejected: it would stop ordinary heredoc commits for the guard's own limitation. Catchers per
command when the guard misses (bypass form or unparsed):
- push to `main`, force push to `main`: the server ruleset `activate_protection` installs;
- force push to another branch: auto mode's classifier, in auto mode only;
- `git push --no-verify`: CI runs the same checks on the PR head; `git commit --no-verify`: the
  pre-push `ci_check`;
- `git reset --hard`: auto mode's classifier, in auto mode only;
- `gh pr merge`: auto mode's classifier when no human approved, in auto mode only; otherwise
  nothing until #357;
- `git branch -D`, `gh repo delete`: nothing.

**D7 — This repository drops the covered deny entries** and keeps `Bash(sleep:*)`; otherwise
each deny shadows the guard's message (proposal, Why). A settings test asserts no remaining
entry matches a guarded command. The `review-and-merge` requirement "Local safety in Claude Code"
named the deny-list as this stop; its delta names the guard, and the test that asserted the deny
entries (catcher of ADR 0033) is replaced by `test_git_guard.py`. *Lost proof:* the static entries block in every session today,
including the heredoc forms D6 only reports; after the change this repository relies on the
installed plugin's `hooks.json` running its checkout's `git_guard.py`.
- Caught: the group-1 tests run every command of the checkout's `hooks.json`, so a broken entry
  or script fails `ci_check`; the `skill_check` SessionStart hook reports a missing or
  misinstalled plugin.
- Between merge and auto-update (the installed release has no guard hook), and for the D6 forms:
  the catchers listed in D6.

**D8 — SKILL.md Install** names the guard and what it denies in the existing sentence on the
plugin's navigation hooks; that sentence already says they act only in adopted repositories and
that a consumer deny rule blocks first.

No ADR: same distribution mechanism as the archived `ship-navigation-hooks`; the record is this
design and the distribution delta.

## Risks / Trade-offs

- [Default branch hard-coded as `main`, while `init` and `activate_protection` read
  `defaultBranchRef`] → a hook must not call GitHub on every Bash call; a consumer on another
  name gets no local push-to-default stop, and the ruleset `activate_protection` installs still
  rejects that push server-side.
- [kinozal_scraper keeps its deny block] → its commands are still blocked, only without the
  alternative named, until it deletes the block (proposal, Impact).
- [False positive on a lookalike] → the scenario «Ordinary git command» pins the common forms;
  a stop on an unusual form is visible and named, the person can run it.
- [Every Bash call spawns a second Python process in adopted repositories] → the gate is a file
  test; the guard is a few-millisecond parse; timeout 10 bounds a stall.

## Migration Plan

Release ships the hook; auto-update brings it to machines on `stable`. Rollback: revert the PR
and release; restore the deny entries in `.claude/settings.json` from the reverted diff.
