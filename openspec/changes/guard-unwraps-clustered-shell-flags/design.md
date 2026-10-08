## Context

`navigation_policy.first_stage_verdict` splits a command into stages and hands each to
`_stage_verdict`, which strips process wrappers and, for `sh`/`bash`/`zsh`, recurses into the
token after an exact `-c`. `git_guard` imports `first_stage_verdict` and supplies its own rule;
the navigation policy's `Bash` route supplies the other. The shell observations and the
navigation measurement are recorded in the proposal's **Why**.

## Goals / Non-Goals

**Goals:**
- A shell stage whose options set `c` in any short-option cluster is unwrapped for the guard.
- The command string is the first operand after that cluster, as the shell reads it
  (`bash -c -e "…"`).
- The navigation policy no longer denies `Bash` commands.

**Non-Goals:**
- Modelling the shells' value-taking options (`-o name`, `-O name`, `--rcfile file`). A value
  placed between the `c` cluster and the command string (`bash -c -o pipefail "…"`) is still read
  as the command string; no reported or observed use has that shape.
- Other shells (`dash`, `ksh`, `fish`) — the shell set is unchanged.
- The navigation policy's `Read` route: it was not measured and does not change.

## Decisions

**D1 — A `c` cluster is a single-dash token of letters that contains `c`.** Match
`re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", token)` against each of `tokens[1:]` and take the first
match. The single dash and the full match keep long options out: `--norc` and `--rcfile` contain
`c` and must not unwrap (`re.search` would match `-rc` in `--rcfile` and read its value as the
command string). Scanning every token keeps `bash -o pipefail -c "…"` and
`bash --rcfile f -c "…"` unwrapped, as `main` does and as the shell runs them (proposal **Why**).
Alternative: parse each
shell's option grammar — rejected, it is a model of three option tables for a case no observation
needs (Non-Goals).

**D2 — The command string is the first token after the cluster that starts with neither `-` nor
`+`.** This follows the observed `bash -c -e`, `bash -c +e` and `bash -c --` / `sh -c --`, each of
which runs the operand after the options (proposal **Why**).
No such token leaves an empty command string, which yields no verdict, as a bare `bash -c` does
today. Alternative: keep "the token after `-c`" as the issue's wording reads literally — rejected,
it leaves `bash -c -e "git push --force"` open by the same lookup.

**D3 — Remove the navigation policy's `Bash` route.** Delete the hook entry, `navigation_hint`,
`_navigation_rule` and its `_hint_*`/`_RULES`, `Stage`, `_split_arguments`, `_VALUE_FLAGS`,
`_REDIRECTS`, `_BOUNDARY`, `pre_bash_response` and the `pre-bash` subcommand, with their tests.
The measurement (proposal **Why**) puts the median denial at a net loss. Alternatives: keep only
the `cat` rule — rejected, its median prevented output (2.1k characters) is below one denial's
cost; make the hook advisory (`additionalContext`, no deny) — rejected, it keeps a bespoke parser
for a benefit no measurement shows.

**D4 — The walker moves into `git_guard.py`.** `_SEPARATORS`, `_WRAPPERS`, `_SHELLS`, `_SHELL_C`,
`_MAX_DEPTH`, `_basename`, `_strip_wrappers`, `_stage_verdict` and `first_stage_verdict` move,
with the `TypeVar` and imports they need;
`_deny` stays in `navigation_policy.py`, which the `Read` route still uses, and the guard keeps
importing it. Alternative: leave the walker in place for a smaller diff — rejected, it would stay
in the navigation policy as code only the guard calls, and outlive the guard.

**D5 — `navigation_policy.main` exits 1 with the usage for any argv but `pre-read`.** The
launcher `bin/agent-process` runs the checkout's `skills/agent-process/scripts/<name>.py` when it
exists, and every hook first changes to the project directory. In the publisher checkout, the
installed release's `hooks.json` still calls `navigation_policy pre-bash` until the next release.
Today an unknown subcommand exits 2, which a `Bash` PreToolUse hook reads as a deny of every
call. Exit 1 is a visible, non-blocking hook error, as observed for the shipped hooks
(`archive/2026-10-02-ship-navigation-hooks/design.md`, D8) and as `git_guard.main` already does. Alternative:
keep `pre-bash` as a silent no-op — rejected, a stale hook entry would then pass unseen.

No new script or check: the change edits and removes existing code, so the design rule for a new
check does not apply.

## Risks / Trade-offs

- Residual bypass through a value option after `-c` (Non-Goals). It has no catcher beyond the
  default-branch ruleset, which stops only a push to `main` and a merge without the required
  checks — not a force or `--no-verify` push to a feature branch, `git reset --hard`,
  `git branch -D`, `git commit --no-verify` or `gh repo delete`. It is accepted as the
  `git_guard.py` docstring accepts `eval` and script files: the guard is a guardrail against
  agent error, not a security boundary.
- Without the `Bash` route an agent may again `cat` a large file. The transcripts show the Bash
  tool saving an output that large to a file instead of inlining it (proposal **Why**), and the
  measurement found no navigation command over 30k characters.
- Between the merge and the next release, every `Bash` call in the publisher checkout shows a
  `navigation_policy` hook error (D5). It goes away with the release; it blocks nothing.
- Rollback is reverting the change; no state, config or consumer file changes. A rollback merged
  after a release that dropped `pre-bash` is safe for the same reason as D5 in reverse: the
  checkout's script accepts `pre-bash` again and the release no longer calls it.
