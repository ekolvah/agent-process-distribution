## Context

See proposal.md — Why. Init installs one Python file, the check (`init.py`, step `check`). The
suite already runs the remote `astral-sh/ruff-pre-commit` hook at the pin
(`tests/agent_process/test_ci_check.py` `TestComplexityLimits`).

## Standard approach

Ruff's formatter suppression comments `# fmt: off` / `# fmt: on`, compatible with Black's
(https://docs.astral.sh/ruff/formatter/#format-suppression); a `# fmt: off` with no closing
`# fmt: on` disables formatting to the end of its block — here the module.

Observed with ruff 0.15.12 on a scratch copy of the template with `# fmt: off` inserted as line
2 (after `# agent-process:managed`, before the docstring):
- `ruff format --isolated --check` → exit 0 at `--line-length` 60, 88, 100 and 120, and at
  `--target-version py39`; the unmodified template exits 1 at 88 (the reproduction);
- `ruff check --isolated --extend-select=C901,PLR0911,PLR0912,PLR0913,PLR0915,RUF028` and
  `ruff check --config pyproject.toml` → `All checks passed!` (`RUF028` flags a misplaced
  suppression comment);
- `python -m pytest tests/publisher/test_skill_check.py` against the template → 23 passed.

## Decisions

**D1 — Module-level `# fmt: off` in the template.** The consumer's formatter stops touching the
managed file whatever its `line-length` or `target-version`, so the class of failure closes,
not one configuration of it.
Alternatives:
- this repository at ruff's default 88 (drop `line-length = 100`) — chosen against by the
  person: on a scratch clone of `7040c29` it reformats 70 of 79 `.py` files (+2619/−756) and
  pushes `init.py`, `init_harness.py`, `test_start_change.py` and `test_reusable_workflows.py`
  past the 1000-line module limit (`ci_check.py --only module-size` exits 1), so it also needs
  splitting them or raising the limit off the seeded 1000;
- a nested `templates/ruff.toml` (`extend` root, `line-length = 88`) and a reformat — matches
  only a consumer on ruff's defaults and adds a file to the plugin package;
- an `exclude` of the check in the seeded `.pre-commit-config.yaml` — reaches only configs init
  creates, not the block it updates in an existing one;
- the consumer-side exclusion (the issue's workaround) — every consumer repeats it.
Cost: this repository's `ruff-format` stops formatting the template too; its lint still runs.

**D2 — The test runs the seeded hook.** A test in `test_init_config.py` takes the `ruff-format`
hook and its `rev` from `templates/pre-commit-config.yaml`, runs it alone in a fresh git
repository holding the template as `.claude/agent-process-check.py`, parametrized over no ruff
configuration and a `ruff.toml` with `line-length = 60`, and asserts the hook passes and the
bytes are unchanged. It reads the pin, so the PR that bumps it runs the test under
`agent-process / quality`.
Alternative: asserting the comment's presence — proves the mechanism, not the scenario.

## Risks / Trade-offs

- [A consumer whose ruff lint selects rules the template breaks still fails `ruff-check` on the
  check] → out of scope: the issue and the seeded selection are about format; the seeded
  `ruff-check` passes (observation above).
- [A later ruff release changes `# fmt: off` semantics] → D2's test fails in the PR that bumps
  the seeded pin.

## Migration Plan

The next init replaces the managed check. Rollback: revert the PR.
