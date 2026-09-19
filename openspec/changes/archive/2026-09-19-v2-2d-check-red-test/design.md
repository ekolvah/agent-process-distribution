## Context

See proposal.md — Why. Current state that shapes the approach:

- `check_red.py` has two branches: `--report <path>` (reads a report the runner declared
  in `AGENTS.md` wrote) and the v1 spawn (`python -m pytest --tb=no --junitxml=<tmp>
  <paths>` in a `TemporaryDirectory`). `evaluate_report` is a pure function over the
  JUnit XML; `test_behavioural_change` forbids the spawn and uses `--report`.
- The `tasks` rule (`openspec/config.yaml`) Group 1 says: run the runner declared in
  `AGENTS.md` with the declared report path, then `check_red.py --report <path>`.
- The change's own `tasks.md` follows the rule as it reads today: Group 1 proves RED with
  `check_red --report` (the flag exists until task 2.1, which runs after the RED commit).

## Goals / Non-Goals

**Goals:**
- No project-side declaration for `check_red`: the runner is its input, the report its own.
- One evaluation path in the script.

**Non-Goals:**
- `init` and the consumer's `test:` input (issue 112): the runner string is `check_red`'s
  input now; `init` will carry it later.
- `wait_for_pr` (`v2-2e-wait-for-pr-checks`), Group 0 scripts (`v2-2f-start-change`).

## Decisions

### D1 `check_red.py --test "<runner command>"` replaces `--report`

`--test` is a string; empty → `[sys.executable, "-m", "pytest"]`; given →
`shlex.split(cmd, posix=os.name != "nt")`. The script appends `--tb=no
--junitxml=<tmpdir>/report.xml <node ids>`, runs it with `encoding="utf-8"`, and evaluates
the report as today (`evaluate_report`, `_select_cases`). Exit codes unchanged: 0 RED, 1 not
RED, 2 unevaluated (report missing or malformed → the tail of the runner output, as now).
The `--report` branch, the `AGENTS.md` runner paragraph and the `.gitignore` entry for
`.pytest-report.xml` are deleted.

*Alternatives.* Keep `--report` beside `--test` — two ways to do one thing, and the
declaration it needs is the convention being removed. Pass the runner as separate argv
after `--` — would forbid a runner string in a future `init` input; a string is what the
input will be.

*Observation.* `python -m pytest --help` (pytest 9.1.1): `--junit-xml=path      Create
junit-xml style report file at given path` (`--junitxml` is its alias the v1 branch of the
script already passes; `check_red` keeps that spelling).

### D2 The `tasks` rule names the call

Group 1 of the `tasks` rule becomes: `python .agent-process/scripts/check_red.py --test
"<runner command>" <node ids>` (the runner of this repository is the default, so `--test`
is omitted here); the sentences on the `AGENTS.md` declaration and the report path leave
the rule. Groups 0 and Deliver are untouched (they are the subject of `v2-2f-start-change`).

### D3 Tests follow the seam

- `test_behavioural_change`: a fake runner given via `--test` (a Python script that
  writes a JUnit file at the `--junitxml=` argument it receives and echoes its argv) proves
  the report path and node ids are appended and the report read; the "no spawn" monkeypatch
  goes. `test_class_scoped_node_id`, `test_parametrized_node_id` move to `--test`.
- `test_tasks_of_a_new_change`: asserts `check_red.py --test` in the rule and no
  `AGENTS.md` / `--report` sentence in Group 1.

## Risks / Trade-offs

- [`shlex.split` on Windows with `posix=False` keeps quotes] → the default needs no
  splitting; a given runner with quoted arguments is documented as unsupported on Windows
  until `init` carries the input.
- [The RED task of this change writes `.pytest-report.xml` while the `.gitignore` entry
  still exists; task 2.1 deletes the entry] → task 2.1 also deletes the file, so no
  untracked file blocks `archive_change`.

## Migration Plan

One PR. Rollback is the revert of the PR: no data, no platform state.
