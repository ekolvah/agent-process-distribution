## Why

When `core.hooksPath` is set, the `manual pre-push` row of `init` and the session-start pre-push
marker tell the person to run `git config --unset-all core.hooksPath` without warning them. The
setting usually exists because the repository ships its own hooks directory, and unsetting it
silently turns those hooks off. In `ekolvah/lampa-mediacenter`, `.githooks/pre-commit` was the
only local secrets gate, and the dry-run gave no hint of the hazard (tracking issue 472).

**Reproduction** (git 2.45.1, scratch clone with `git config core.hooksPath .githooks` and
`.githooks/pre-commit`, `manual._pre_push_row` on `main` at 910de56):

```
manual pre-push: in this clone -- git config --unset-all core.hooksPath where it is set, then pre-commit install --hook-type pre-push, so a push runs the declared test (core.hooksPath is set)
```

`templates/skill_check.py` `_pre_push` returns the same reason, `core.hooksPath is set`.

**Root cause**: `manual.pre_push` and `skill_check._pre_push` stop at the exit code of
`git config --get core.hooksPath`. They never look at the directory the setting points to, so
the instruction is the same whether that directory holds hooks or not.

## What Changes

- While `core.hooksPath` is set, `init` and the session-start check list the entries of the
  hooks directory git uses, other than `*.sample`. When there are any, the reason names the
  directory and the entries. It says that git stops running them once `core.hooksPath` is
  unset, and that they must be ported to `.pre-commit-config.yaml` as `repo: local` hooks
  first.
- The reason stays `core.hooksPath is set` when the directory is missing or holds only
  `*.sample` files.
- `init` neither changes git config nor fails the run: the row stays a `manual` row (design D3).

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: *Init renders the pre-push hook* and *A Claude session start reports a missing
  pre-push hook* name the existing hooks, and each requirement gains a scenario.

## Impact

- Edited: `skills/agent-process/scripts/manual.py`, `skills/agent-process/templates/skill_check.py`,
  `tests/publisher/test_init_remote.py`, `tests/publisher/test_skill_check.py`.
- No file is added or removed, and no dependency changes. No doc or ADR describes the row's
  wording (`git grep "manual pre-push"` finds only the spec, code and tests), so none changes.
