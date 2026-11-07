## Context

`init` seeds the baseline hooks once, when it creates `.pre-commit-config.yaml` (ADR 0035 D1).
The `detect-secrets` entry comes from `skills/agent-process/templates/pre-commit-config.yaml`,
and `tests/publisher/test_init_config.py::_baseline()` asserts its shape and pin. The
reproduction and the root cause are in `proposal.md`.

## Standard approach

- Python UTF-8 mode (`-X utf8` / `PYTHONUTF8=1`) makes `open()` without an `encoding` use
  UTF-8 whatever the locale: https://docs.python.org/3/library/os.html#utf8-mode. It becomes
  the default from Python 3.15: https://peps.python.org/pep-0686/.
- pre-commit, https://pre-commit.com/, "Repository local hooks": "You can configure
  repository-local hooks by specifying the repo as the sentinel `local`". In "python": "This
  language also supports additional_dependencies so it can be used with local hooks." In
  "pre-commit-config.yaml - hooks", `entry` is not a documented override key.
- Prior art: this repository's own gate already runs the same command
  (`.agent-process/scripts/ci_check.py::_secrets_cmd`).
- Upstream: no prior issue (`gh search issues --repo Yelp/detect-secrets` for "UnicodeDecodeError
  encoding" and "utf-8 windows" returned none); filed as
  https://github.com/Yelp/detect-secrets/issues/1013.

## Decisions

**D1. A local `language: python` hook runs the module under `-X utf8`.** The entry is
`python -X utf8 -m detect_secrets.pre_commit_hook` with
`additional_dependencies: [detect-secrets==1.5.0]` at the stages it already has.
This gives the consumer gate the same decoding as this repository's gate. Observed: the
reproduction in `proposal.md` reports `ru2.md:1`.
- *Alternative: keep `Yelp/detect-secrets` and override `entry`.* On the same files with
  `PYTHONUTF8=0` it also reported `ru2.md:1`. pre-commit merges every manifest key over the
  manifest (`pre_commit/clientlib.py` 4.6.0, lines 444–451). But the docs do not list `entry`
  as an override key. Rejected, because a silent regression there means a silent secret miss.
- *Alternative: set `PYTHONUTF8` for the hook.* pre-commit has no per-hook environment key,
  and asking every consumer to set it globally is a "remember to" rule.
- *Deletion condition:* when detect-secrets reads files as UTF-8, or Python 3.15 (PEP 686) is
  the floor, the remote hook returns.

**D2. The pin moves from `rev` to `additional_dependencies`.** `_baseline()` builds the
expected `detect-secrets==<pin>` from `.agent-process/requirements-dev.txt`. A bump that
misses the template therefore still fails `test_created_config_carries_the_baseline`.
`pre-commit autoupdate` does not bump this line, so it is bumped by hand, like mypy's typed
dependencies.

**D3. The other baseline hooks are unchanged.** ruff, mypy and pylint decode Python source by
its PEP 263 declaration, which defaults to UTF-8, not by the locale. pip-audit reads only
`requirements*.txt`, and pytest runs the project's own tests. None has an observed
locale-decoding miss.

**D4. A behaviour test runs the seeded entry under an ASCII locale.** It takes the seeded
`detect-secrets` hook, swaps in `language: unsupported` and drops `additional_dependencies`,
so the test interpreter runs the template's exact `entry` from `PATH`, as the `pytest` hook
test does, with no network. It sets `PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C`. On POSIX
that gives an ASCII locale encoding (PEP 538, PEP 540), and Windows keeps `cp1252`, so the old
entry misses the file on every platform. Observed on Windows with these variables: the entry
without `-X utf8` printed `Passed` on `ru2.md`, and with it printed `Failed` and
`Location: ru2.md:1`. The `language: python` install is not under test; it was observed once,
in `proposal.md`.

## Risks / Trade-offs

- Under `-X utf8` the scanner still silently skips a file that is not valid UTF-8, such as
  cp1251 or UTF-16. This is the upstream behaviour named in the root cause, not a regression
  of this fix.
- ADR 0035 says "every check is a standard tool through its own hook repository". For
  detect-secrets the tool stays the same but the repository becomes `local`. The ADR's
  Decision Outcome, D2, D3, Consequences (autoupdate leaves this pin behind) and Confirmation
  (the new test) are amended.

## Migration Plan

Configs created from now on get the local hook. An existing config is owned by its
repository (ADR 0035 D1) and is not rewritten, so a consumer with the old hook copies the new
entry from the template. Rollback is reverting the template, the test and the ADR wording
together.
