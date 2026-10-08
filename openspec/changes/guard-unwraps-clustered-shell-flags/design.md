## Context

`navigation_policy.first_stage_verdict` splits a command into stages and hands each to
`_stage_verdict`, which strips process wrappers and, for `sh`/`bash`/`zsh`, recurses into the
token after an exact `-c`. `git_guard` imports `first_stage_verdict` and supplies its own rule, so
one change in `_stage_verdict` fixes both hooks. The shell observations are recorded in the
proposal's **Why**.

## Goals / Non-Goals

**Goals:**
- A shell stage whose options set `c` in any short-option cluster is unwrapped, for both hooks.
- The command string is the first operand after that cluster, as the shell reads it
  (`bash -c -e "…"`).

**Non-Goals:**
- Modelling the shells' value-taking options (`-o name`, `-O name`, `--rcfile file`). A value
  placed between the `c` cluster and the command string (`bash -c -o pipefail "…"`) is still read
  as the command string; no reported or observed use has that shape.
- Other shells (`dash`, `ksh`, `fish`) — the shell set is unchanged.

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

No new script or check: the change edits the existing walker, so the design rule for a new check
does not apply.

## Risks / Trade-offs

- A cluster also widens the navigation policy's denials: `bash -lc "cat README.md"` is now denied
  where it passed. That is the policy's intent (implementation spec, "Shell navigation").
- Residual bypass through a value option after `-c` (Non-Goals). It has no catcher beyond the
  default-branch ruleset, which stops only a push to `main` and a merge without the required
  checks — not a force or `--no-verify` push to a feature branch, `git reset --hard`,
  `git branch -D`, `git commit --no-verify` or `gh repo delete`. It is accepted as the
  `git_guard.py` docstring accepts `eval` and script files: the guard is a guardrail against
  agent error, not a security boundary.
- Rollback is reverting `_stage_verdict`; no state, config or consumer file changes.
