## Context

See proposal.md — Why. Today the quality commands reach CI only as `with:` inputs of the managed
caller (`templates/agent-process.yml`), rendered from `init --test/--setup`. `quality.yml`
interpolates them into `run:`. The config block repeats the command as a `tasks` rule, which
Verify reads. `check_red` runs `python -m pytest` itself and reads no declaration. The publisher
caller passes its own `setup`/`test`/`checks` literals.

## Goals / Non-Goals

**Goals:** no command is asked for before it exists; CI shows that it tests nothing; the change
that brings the first tests cannot finish RED without declaring the command; an upgrade never
silently drops a consumer's running tests.

**Non-Goals:** recognising a declared command that tests nothing (`python -c "pass"`
declared on purpose). An exit code does not tell a no-op from a green suite, and no
language-agnostic probe exists. `check_red`'s runner is unchanged (still pytest, issue 112).

## Decisions

### D1 — The commands live in a consumer-owned declaration

The declaration is `.github/agent-process-quality.json`: `{"test": str, "setup"?: str, "checks"?: str}`,
with the same meaning as today's inputs. `init` never writes it, and the change that brings the
first tests adds it (D4).

- **Problem closed:** #249.
- **Standard for the job and why it does not fit:** workflow `with:` inputs are GitHub's
  carrier for a caller's values, but here they sit in a file `init` manages ("rerun it instead
  of editing"), so a change cannot set them without re-running Install. No language-agnostic
  standard names a project's test command: `package.json` `scripts.test` covers npm only, and a
  Makefile `test` target is a convention, not a guarantee.
- **Alternatives rejected:**
  - Keep `--test` and probe-run it in `init`. It cannot tell `python -c "pass"` from a suite,
    and a dry-run would execute consumer code.
  - An unconditional `manual` reminder row. It fires on every run, so it distinguishes nothing.
  - Seed a dummy test at install. This is the placeholder again: CI stays green and proves
    nothing, and `init` would have to guess a language and write product code outside its closed
    footprint.
  - A key in `openspec/config.yaml` outside the owned block. It needs a YAML parser that
    neither the stdlib nor the scripts carry, and it mixes into OpenSpec's file.
  - A path under `.agent-process/`. Package files must not name it (spec *Package paths
    resolve in a consumer*).
- JSON is read by stdlib `json`; `.github/` sits beside the caller that consumes it.

### D2 — One reader, `skills/agent-process/scripts/quality.py`

`read(root)` returns the declaration, `None` when the file is absent, or raises a `ValueError`
naming the fault (the malformed forms listed in the spec). `init` and `check_red` import it.
`quality.yml`'s plan job runs `python trusted/skills/agent-process/scripts/quality.py
--github-output` from a trusted checkout at `job.workflow_sha`, as the link job already does for
`release_pr.py`, so a PR cannot change the parser that judges its own declaration. It writes
`setup`, `test`, `checks` to `$GITHUB_OUTPUT`. Absent: `::warning::` plus empty `test`.
Malformed: `::error::` and exit 1.

**Platform fact (GitHub Docs, "Workflow commands for GitHub Actions"):** "Setting an output
parameter" writes `{name}={value}` lines to `$GITHUB_OUTPUT`, and "For multiline strings, you
may use a delimiter". A value with a line break would therefore add a further output (a `test`
whose second line is `checks=…`). The reader rejects a line break in any value as malformed
instead of choosing a delimiter: a quality command fits one line.

- **Problem closed:** #249; a single parser avoids a jq reader in CI drifting from the Python
  readers.
- **Standard:** none reads this file; `json` does the parsing, and the script only validates
  the shape.

### D3 — CI without a declaration warns and passes

The check job runs `setup`/`test` from the plan outputs through `env` and `eval`, never
`${{ }}` interpolation into `run:`. With an empty `test` it runs nothing, and the gate stays
unchanged.

**Why not fail?** A repository without tests has nothing to prove. Failing would also turn the
installation PR red, while *Protection activation observes quality first* needs a successful
`agent-process / quality` on it. The hard stop is D4.

**Platform fact (GitHub Docs, "Workflow commands for GitHub Actions" — Setting a warning
message):** "Creates a warning message and prints the message to the log. This message will
create an annotation". The annotation is shown on the run and on the PR's checks.

**Trust.** The declaration is PR content executed with the PR's read-only token, the same
trust as the PR's tests and as the head's own caller file, which `pull_request` already takes
from the PR. The `quality.yml` header comment ("`run:` interpolates only the caller file's
literal commands") is rewritten to say this.

### D4 — `check_red` refuses without a declared `test`

It reads the current directory (spec *Skill commands run from a consumer root*) before running
pytest, and exits 2 (gate precondition, not "tests are not red") naming the file, the fault,
and the JSON shape. RED is where a repository's first tests are born, so the command is
declared by the change that brings them, in its own PR, which then proves them in CI.

### D5 — Upgrade over a passed `test` is a conflict

`_workflow_text` raises `Conflict` when the existing managed caller carries a `test:` input
line and no `test` is declared. For `init`, a declaration that `quality.read` rejects counts
as no `test` declared, in one helper that both the marker and this check use, so no
`ValueError` reaches `_file_step`. Only `init`'s own renders up to 3.0.2 carry that line.
The message quotes the line and names the fix: declare it, or delete the caller when the
repository has no tests. Without this, an upgrade would rewrite the caller with no input and
the consumer's CI would silently stop testing.

### D6 — The publisher uses the same source

`.github/workflows/agent-process.yml` passes no `with:`. `.github/agent-process-quality.json`
holds today's three literals. `quality.yml` has one input path, and the publisher's own
`check_red` passes D4.

### D7 — Release

The PR is titled `fix: declare-quality-with-first-tests`, and its body ends with a
`BREAKING CHANGE:` footer, as #243 did for 3.0.0: `init --test/--setup` are removed, and an
upgraded consumer declares its command once.

### Replaced input: failure modes and catchers

This drops a guard (`--test` was required) and moves the input from the installer to the
project. For each failure mode, the catcher:

| Failure mode | Catcher actually reached |
|---|---|
| Declaration absent after tests were added through the process | `check_red` exit 2 on the RED of that change, in its worktree |
| Declaration absent, tests added outside the process | `::warning::` from `quality.py --github-output`, on every head of every PR |
| Declaration malformed | `quality.py` `::error::` fails `agent-process / quality` on that head; `check_red` exit 2 locally |
| Upgrade drops a passed `test` | `init` `conflict` on the dry-run, before any write (D5) |
| A PR deletes or weakens its declaration | `agent-review / agent-review` on that head. No new exposure: the PR could already rewrite its caller's `with:` |
| Declared command is a no-op | Not caught (Non-Goals). Same as today |

What stops proving: nothing that proved anything before. The required `--test` guaranteed
only a non-empty string.

## Risks / Trade-offs

- [The warning is ignored while tests arrive outside the process] → D4 covers every
  process-driven change, and the marker is on every head.
- [A new `init` can no longer hand off to a release ≤3.0.2, whose own parser requires `--test`]
  → Accepted: such a downgrade runs that release's installer directly. The spec's hand-off
  contract stands, since the requested release owns its run.
- [Plugin auto-update brings the new `check_red` to consumers before they re-run Install] →
  Intended. Its message names the one-file fix, and release drift already sends them to
  Install.

## Migration Plan

An existing consumer re-runs Install. The dry-run reports the D5 `conflict` quoting its current
`test:`, and the operator writes `.github/agent-process-quality.json` with that command (or a
real one), then confirms. Rollback: revert the PR. Consumers pinned to `quality.yml@v<old>` keep
working, because their callers still pass inputs to their own tag.
