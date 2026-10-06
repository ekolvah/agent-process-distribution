## Context

The current-state rule lost its home with `project-map.md`. The only guard,
`tests/agent_process/test_doc_narrative.py`, checks the form of `#N` in `.md` (pointer in
parentheses, no number in a heading, `#` reserved for issues) and leaves code unguarded.
Issue references in comments and docstrings keep arriving with each fix (PR 352).

## Goals / Non-Goals

**Goals:** the rule stated once; a deterministic check outside the history records; the
existing references removed.

**Non-Goals:** links to issue URLs and history notes without a number (a judgement, left to
review); consumer repositories (the hook is this repository's own).

## Decisions

### D1. The check is a `pygrep` hook of `pre-commit`

Problem: issue references reach code and docs unchecked (PR 352; 144 references on `main`).
Standard: `pre-commit`'s built-in `pygrep` language, a regular expression with `exclude`; the
repository already runs `pre-commit`-stage hooks at edit time and in `ci_check lint`, so the
hook needs no new script and no wiring. Ruff's `TD003` and `todocheck` solve the opposite job
(they require an issue link in a TODO); Vale lints prose only.

Declared in `.pre-commit-config.yaml` under `repo: local`, `stages: [pre-commit]`,
`types: [text]`, `args: [--multiline, --ignore-case]`, `exclude:
'^(\.agent-process/docs/adr/|CHANGELOG\.md$|openspec/changes/)'`, entry
`(?<![\w&/#])#\d+\b|\b(?:issues?|PRs?|pull requests?)[\s#]+\d+\b`.

Observed with `pre-commit 4.6.0` in a scratch repository (`pre-commit run --all-files`,
exit 1): `--multiline` reports `ok (issue` / `112` across a line wrap and `x = 1  # fixed
(issue` / `# 112` across a wrapped comment; the excluded `docs/adr/0001.md` and
`CHANGELOG.md` carrying `#42` are not reported; `&#123;`, `pull/5#x`, `#doc-guards` and `C#1`
are not reported. In multiline mode the hook prints the first match of each file only.

### D2. `test_doc_narrative.py` is removed

Forbidding the reference supersedes checking its form. Lost proofs and their catcher:

- narrative `#N` in `.md` → the hook (D1), on every head through `ci_check lint`;
- `#N` in a heading → the hook (any `#N` outside history);
- `workflow #N` / `Project #N` → the hook (`#N` after a space);
- `#N` in a code span or link label, allowed before → now reported; the repository writes
  a placeholder (`#<N>`) instead;
- the scope tests (`test_scope_covers_expected_dirs`, `test_non_md_files_are_in_sigil_scope`,
  `test_adr_records_are_out_of_scope`), which kept an empty or over-wide scope from passing
  green → `test_issue_reference_outside_history` places its offending files at
  `skills/agent-process/scripts/`, `.github/workflows/`, `.claude/rules/` and `tests/`, and
  copies the repository's own hook, so an `exclude` or `types` that drops one of them fails
  it; `test_history_record_keeps_its_references` fails an exclusion that misses a history
  record.

### D3. The rule lives in the spec, the hook delivers it

The `maintenance` requirement states the rule; the hook's name states it in the failure the
edit-time lint shows the agent on the offending edit, and in the `ci_check lint` output.
A `CLAUDE.md` bullet was rejected: it would repeat the spec in every session's context while
the hook already reaches the agent at the moment of the violation. The skill and
`principles.md` stay unchanged: the rule is this repository's, not a consumer requirement.

### D4. Fixtures build numbers from constants

Tests whose input is an issue number (`tracking issue 7`, a project list `#4 Board`) take
it from a named constant through an f-string, so the source carries no literal reference and
the hook keeps covering tests, where PR 352 put one.

## Risks / Trade-offs

- [The hook reports one match per file] → the operator reruns after each fix; the cleanup
  itself uses a full scan.
- [An issue URL or a reference wrapped behind `//` or `<!--` passes] → named limit; review
  catches it.
- [A future TODO pointing at an open issue is reported] → no TODO exists today (§VII); add a
  TODO form to the expression when one is needed.

## Migration Plan

One PR: hook, rule, cleanup and test removal together, since the hook fails until the
cleanup lands. Rollback is a revert of that PR.
