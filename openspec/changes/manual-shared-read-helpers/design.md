## Context

The two rules parsers differ in tolerance:

- `manual._protected` reads `rule["type"]` and turns `KeyError`/`TypeError` into `Unreadable`.
- `wait_for_pr._required` reads `rule.get("type")` and lets any other malformed shape raise.

Observed: `gh api "repos/{owner}/{repo}/rules/branches/main" --jq '[.[] | {type, has_type: has("type")}]'`
on this repository (2026-11-12) printed six rules, each `"has_type":true`, and two of them were
`required_status_checks`. So every observed rule carries `type`, and contexts have to be
de-duplicated across rules.

## Goals / Non-Goals

**Goals:**

- One implementation of each duplicated piece.
- A name that says what the JSON reader does.

**Non-Goals:**

- New behaviour. The one new test, `rules-shape` (D2), pins a path that already exists.

## Decisions

**D1 — `_kept`/`_ok` in `manual.py`.** The pair is generic over a module-level
`T = TypeVar("T")`. It does not use PEP 695 syntax: consumers run the scripts under their own
`python` (`bin/agent-process`, `plugin_env.py`), no minimum of 3.12 is declared, and `init`
imports `manual`.

- `_kept(read: Callable[[], T]) -> T | Unreadable` returns `read()`, or the `Unreadable` it
  raised.
- `_ok(kept: T | Unreadable) -> T` raises a kept `Unreadable` and returns anything else.

In `rows`:

- `secrets = _kept(lambda: _names(t, "secret"))` and `repo = _kept(lambda: _repository(t))`.
- `_has(secrets, X)` becomes `X in _ok(secrets)`.
- `_field(repo, k)` becomes `_ok(repo)[k]`.
- `_repository` raises its shape `Unreadable` instead of returning it.

In `readings`, which already sits in a `try/except Unreadable`, the check becomes
`GRAFANA_TOKEN in (_names(t, "secret") if secrets is None else _ok(secrets))`.

`_names_or_unreadable`, `_has` and `_field` are deleted.

**D2 — `activate_protection.required_contexts(rules) -> list[str]`.** It returns the `context` of every
check in every rule whose `rule["type"]` is `required_status_checks`, in rule order and without
duplicates. A malformed shape raises `KeyError`/`TypeError`.

It lives in `activate_protection`, which already owns the process's `contexts()` and is already
imported by `manual`. The issue's name, `contexts(rules)`, is taken, and a bare `required` would sit beside the
unrelated private `_required(checks)`.

Each caller keeps its own read and its own error handling:

- `wait_for_pr._required` keeps its `note:`.
- `manual._protected` keeps its `isinstance` guard and `Unreadable` message, and compares
  `set(contexts()) <= set(required_contexts(rules))`.

Tolerance follows `manual`. A rule without `type` now makes `wait_for_pr` raise where it used
to skip the rule. No observed response has such a rule. `rule.get("type")` was rejected because
it would make `manual` silently skip a malformed rule it reports today (§IV).

No test reaches that path today: the harness returns only well-formed rules or the 404 object,
which fails the `isinstance` guard first. The `UNREADABLE` case `rules-shape` closes that gap.
Its harness fault returns `[{"parameters": {}}]`, and it asserts the `protection` row carries
`(cannot read: `. It goes in green before the refactor and must stay green after it.

**D3 — Issue item 3 declined.** Passing init's `gh repo view` read into `Target` would be wrong.
`init._run` reads before its writes, and `manual.rows` reads after them, so that a Project this
run linked is seen (comment before `_manual` in `init.py`; archived `manual-rows-from-state`
D1). Shared, that read would show such a Project as unlinked.

Dropping manual's REST `repos/<o>/<n>` read is possible, but declined on cost. It would take a
GraphQL query that reads `autoMergeAllowed` beside `_linked`'s fields, because
`gh repo view --json` does not accept that field. That means rewriting `_linked`'s read and the
`init_harness` doubles to save one `gh` call per `init` run.

**D4 — `_plugin_file` → `_json_file`.** A rename inside `manual.py`.

## Risks / Trade-offs

- `wait_for_pr` already exits 1 with a traceback on a malformed `rules/branches` response, for
  example a check without `context`. That exit 1 is the code it documents for failed checks.
  D2 adds a rule without `type` to those shapes. Mapping them to exit 2 would change behaviour,
  so it is outside this refactor.
- Rollback: revert one commit.
