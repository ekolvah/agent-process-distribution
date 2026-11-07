## Why

`test_git_failure_inside_a_repository_is_visible[gitfile]` fails on every PR since runner image
`ubuntu-24.04` 20261101.360 moved git to 2.56.0, which words a `.git` file naming a missing
gitdir differently. Reproduction, run 42374569845 (`git version 2.56.0`):

```
AssertionError: assert 'fatal: not a git repository: ' in 'edit-time lint is not active: fatal: gitfile does not point to a valid repository: /tmp/.../repo/removed/.git\n'
```

Root cause: the test pins git's message text, which is not git's contract. The hook is correct:
it exits 2 and its stderr carries the marker followed by git's message, as the scenario
*Git fails inside a repository* requires. The `_NOT_REPOSITORY_CODE` prefixes do not match the
new wording either, so the hook still reports instead of going silent.

## What Changes

- The gitfile case expects the marker immediately followed by git's `fatal: ` prefix,
  `edit-time lint is not active: fatal: `, instead of the 2.55 wording.
- The comment above `_NOT_REPOSITORY_CODE` in `edit_lint.py` names both wordings.

## Standard approach

Assert on the stable part of a third-party message (git's `fatal: ` prefix, written after the
hook's own marker), not on its prose. none found: git documents no wording for these errors;
neither `git-rev-parse.html` nor `gitrepository-layout.html` of git 2.45.1's bundled docs
contains `not a git repository` or `does not point to a valid`.

## Capabilities

### New Capabilities

### Modified Capabilities

None: `skip_specs` — the hook's behaviour and its scenario are unchanged.

## Impact

- Edited: `tests/publisher/test_edit_lint.py`, `skills/agent-process/scripts/edit_lint.py` (comment only).
