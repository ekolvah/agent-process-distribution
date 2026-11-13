## Why

`/simplify` on the post-merge `manual` rows left four optional cleanups that each touched code
outside that diff (tracking issue 491). Two of them are duplicated logic, and a later fix would
have to change both copies:

- `manual.py` keeps a failed shared read and re-raises it per row twice:
  `_names_or_unreadable`/`_has` and `_repository`/`_field`.
- `wait_for_pr._required` and `manual._protected` each parse the `required_status_checks`
  contexts out of `gh api repos/<o>/<n>/rules/branches/<b>`.

`_plugin_file` now also reads `.claude/settings.local.json`, so its name misleads.

## What Changes

- One generic `_kept`/`_ok` pair replaces both keep-the-`Unreadable` pairs (design D1).
- One `activate_protection.required_contexts(rules)` serves both rules parsers (D2).
- `manual._plugin_file` is renamed `_json_file` (D4).
- Issue item 3 (one `gh repo view` per `init` run) is declined (D3).

No observed response changes outcome: every row, message, exit code and `gh` call stays as it
is. D2 names the one unobserved shape that does.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a pure refactor, so `skip_specs: true`.

## Standard approach

none found: this extracts functions inside the repository's own scripts, a job no library does.
`grep -rn "rules/branches"` over `skills/` and `tests/` finds only the two parsers above and
the test doubles.

## Impact

- Edited: `skills/agent-process/scripts/manual.py`, `skills/agent-process/scripts/wait_for_pr.py`,
  `skills/agent-process/scripts/activate_protection.py`.
- Edited (test): `tests/publisher/init_harness.py` and `tests/publisher/test_init_remote.py`
  gain one `UNREADABLE` case, `rules-shape` (design D2).
- Added, removed: none. No spec, ADR or doc changes: the docstrings describe behaviour that
  stays, and no ADR names these helpers.
