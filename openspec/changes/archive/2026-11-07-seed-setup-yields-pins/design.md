## Context

See proposal.md — Why. The seed lives in `skills/agent-process/templates/agent-process-quality.json`,
rendered by `init` through `string.Template` (`$$` is a literal `$`). CI runs it as
`eval "$SETUP"` in a `bash -e` step of `.github/workflows/quality.yml` after
`actions/setup-python`; the pre-push hook never runs `setup`.

## Standard approach

pip's install semantics (https://pip.pypa.io/en/stable/cli/pip_install/): without `--upgrade`
an already satisfied requirement is left as installed. Observed with pip 24.3.1 and pytest
9.0.3 installed: `python -m pip install pytest` printed
`Requirement already satisfied: pytest in … (9.0.3)` and `pip show pytest` still read
`Version: 9.0.3`, while 9.1.1 is published.

## Goals / Non-Goals

**Goals:** one owner per tool version in a seeded declaration: the project's requirements.

**Non-Goals:** changing existing declarations (`init` never rewrites one).

## Decisions

- **D1 — One install: the tools without a version, with the requirements.** The seed becomes
  `set --; for f in requirements.txt requirements-dev.txt; do if [ -f "$$f" ]; then set -- "$$@" -r "$$f"; fi; done; python -m pip install pre-commit pytest "$$@"`.
  One resolution: a tool the requirements pin, directly or transitively, keeps that version,
  and so does every dependency they pin; a repository without requirements gets the current
  release of each. The command's status is pip's, so a failed install fails the step.
  Observed (architect review, fresh venvs): `pip install pluggy==1.4.0` then `pip install pytest`
  printed `Successfully installed ... pluggy-1.7.0 pytest-9.2.0` — a second install replaces a
  dependency pin silently — while `pip install pytest -r req.txt` with `pluggy==1.4.0` kept
  pluggy 1.4.0 and resolved pytest 8.1.2. Under `bash` with a `python` function echoing its
  arguments, the seed ran `-m pip install pre-commit pytest`, then
  `… -r requirements-dev.txt`, then `… -r requirements.txt -r requirements-dev.txt` as the
  files appeared, and a function returning 3 made the command exit 3. `pre-commit` is included: its pin has the same defect as
  `pytest`'s. ADR 0035 D3 (seeded pins equal this repository's) is amended accordingly.
  Alternatives:
  - *Requirements first, then a separate unpinned `pip install pre-commit pytest`* — the second
    resolution ignores the project's pins and upgrades a pinned dependency silently (observed
    above).
  - *Pin only when `pip show` finds the tool absent* — keeps the template as a second owner,
    adds two shell branches and an exit code not on pip's reference page.
  - *Grep the requirements for the tool name* — a hand-written requirement parser that misses
    transitive installs.
  - *Drop the tools from `setup`* — a fresh repository's first CI run fails with no
    `pre-commit`, which the seed exists to prevent (ADR 0035).
  - *The same single install with the tools pinned, or a constraints file* — a differing
    project pin fails resolution: loud, but the template still owns a pin.
  - *A `>=` floor at this repository's pins* — a project pinned below the floor is upgraded
    over its pin: the same silent override.

## Risks / Trade-offs

- [A repository without requirements gets whatever release is current at each CI run] → the
  repository owns its versions: listing `pre-commit` and `pytest` in `requirements-dev.txt`
  pins them. The previous fixed pin aged in the consumer's JSON, where nothing updated it.

## Migration Plan

Fresh seeds only. Rollback: revert the template, `_seeded()` and the ADR text; existing
declarations are unaffected either way.
