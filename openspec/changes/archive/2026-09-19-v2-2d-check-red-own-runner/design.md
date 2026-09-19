## Context

See proposal.md — Why. The archived `design.md` of `v2-2d-check-red-test` (D1 and its
three amendments at rounds 3, 5 and 7 of the review of PR 145) is the state this change
starts from: `--test "<runner command>"` split with `shlex`, `--tb=no --maxfail=0
--junitxml=<tmp>` appended, the report judged whole, a count guard (`at_least=len(paths)`
in `evaluate_report`) that exits 2 on a report short of the node ids.

## Goals / Non-Goals

**Goals:**
- One runner, one configuration of the run, owned by the script; a recorded boundary of
  what the gate guarantees.
- No code that exists for a consumer that does not exist.

**Non-Goals:**
- `init` and a consumer's `test:` input (issue 112): when a consumer with another runner
  appears, the input is designed with its failure modes listed (issue 146), not reinstated
  from this diff.
- Proving the collection (a second `--collect-only` run) — see Alternatives.

## Decisions

### D1 The runner is the script's own, and so is the configuration of the run

`main` builds `[sys.executable, "-m", "pytest", "--tb=no", "--maxfail=0", "-p",
"no:cacheprovider", f"--junitxml={tmp}/red.xml", *node_ids]` and runs it with
`encoding="utf-8"` in a `TemporaryDirectory`. `--test`, `shlex`, the `ValueError` branch
of the split and the `OSError` branch of the launch go: the interpreter that runs the
script runs pytest. `evaluate_report` loses `at_least`; the report is judged whole, as
before. Exit codes unchanged: 0 RED, 1 not RED, 2 no verdict (report missing or malformed,
capture `None`) with the tail of the runner output.

*The boundary.* The gate guarantees that every node id it was given ran to a verdict, or
that it exits 2: `--maxfail=0` cancels `-x`/`--maxfail` wherever they come from, and
`-p no:cacheprovider` turns `--stepwise`, `--sw-skip`, `--lf`, `--ff`, `--nf` into a
usage error (rc 4, no report → exit 2 with that error in the tail). An explicit selection
in the project's `addopts` — `-k`, `-m`, `--deselect` — is the project's configuration:
the gate judges the run under it, as the project itself runs its tests. A node id that
collects nothing is pytest's own error (rc 4 or "no tests collected" → exit 1 or 2), not
the gate's to re-derive.

*Why the count guard goes.* With fail-fast cancelled by the script, no pytest run
produces a report shorter than the node ids except through a duplicate node id, which
pytest dedupes — the guard's only remaining effect is a false exit 2 (PR 145, round 8,
P2). Dead insurance is a second interpreter of the node id in disguise (§VII).

*Observations (pytest 9.1.1, 2026-09-19, a two-test file `test_a` failing, `test_b`
passing).* `-x --maxfail=0 -p no:cacheprovider` → `1 failed, 1 passed`; `addopts = -x`
with `-p no:cacheprovider --maxfail=0` on the command line → `1 failed, 1 passed`;
`-p no:cacheprovider --sw` → `ERROR: usage: … error: unrecognized arguments: --sw`, rc 4,
no `--junitxml` file written; the same with `addopts = --sw` and `-p no:cacheprovider
--maxfail=0 --junitxml=…` on the command line → the same usage error, rc 4, no report;
`-p no:cacheprovider --lf` → the same usage error. The round-7 observation on `maxfail`
(`store_const` vs `store`, last wins) is on record in the archived D1.

*Alternatives.* A second `--collect-only` run compared by count: catches every early
stop but not a filter, doubles the gate's time, and `-p no:cacheprovider --maxfail=0`
already closes the early stops pytest has. Parsing the runner string for forbidden flags:
a second interpreter, and `addopts` is not on the string. Keeping `--test` with the two
flags: cheaper now, but the input without a consumer keeps its failure-mode family (three
of the eight rounds) and would be redesigned anyway when a consumer appears.

*Amended at round 9 of the review of PR 145 (owner's decision), closed by its class.*
Two findings followed from the paragraphs above: `-p no:cacheprovider` disables the whole
plugin, so a test that uses the `cache` fixture errors at setup (P1); and an interrupted
run — `pytest.exit()` from a hook — returns 2 with a partial report that the gate judged
RED (P1). Both are instances of one invariant that the boundary states and the
implementation did not derive from: the signal that the run reached the end is pytest's
own exit code. The script now accepts the report only when `returncode` is 0, 1 or 5
(`_COMPLETE_RUN`); 2 (interrupted), 3 (internal error) and 4 (usage error) exit 2 with the
tail. The configuration cancels what shortens a run without changing the exit code:
`--maxfail=0` stays; `-p no:cacheprovider` is replaced by `-o cache_dir=<tmp>/cache` — an
empty cache of the script's own leaves `--lf`/`--ff`/`--nf` nothing to replay (also over
`addopts = --lf` and `cache_dir` in the ini, `-o` wins), and the `cache` fixture stays;
`-p no:stepwise` keeps `--stepwise` a usage error, as the spec says ("stepping disabled").
Observed on pytest 9.1.1 (same fixture): `--sw` → rc 2 (`Session.Interrupted` is a
`KeyboardInterrupt`), `-x` → rc 1, `-k` → rc 1; `--lf`/`--ff` with `-o cache_dir=<empty>`
→ `1 failed, 1 passed`; the `cache` fixture under `-o cache_dir` → the test runs;
`pytest.exit()` from `pytest_runtest_logreport` → rc 2, one testcase of two in the
report. Tests: `test_interrupted_run_is_no_verdict` (rc 2, 3, 4 → exit 2; rc 5 → the
empty report is judged), `test_behavioural_change` asserts `-p no:stepwise`, `-o
cache_dir=` beside the report path, and no `no:cacheprovider`. Why nine rounds: each fix
closed the reviewer's example, not the class; issue 146 carries the rule.

*The scenario name "Runner given" stays.* OpenSpec 1.13.0 refuses a MODIFIED block that
drops a scenario the current spec has (`validate --strict`: `MODIFIED "RED first for
behavioural changes" omits scenario(s) the current spec still has: "Runner given". Copy
them into the MODIFIED block (a MODIFIED requirement replaces the whole block, so archive
refuses to drop them)`), and a REMOVED plus ADDED of one title is refused too
(`Requirement present in both ADDED and REMOVED`). The scenario keeps its name and
states the new truth: the runner is a given of the script.

### D2 Tests drive the `subprocess.run` boundary

`test_behavioural_change` and `test_runner_owns_the_selection` monkeypatch
`check_red.subprocess.run` (the precedent is `test_none_capture_is_an_error`) with a fake
that records the command, writes the fixture report at the `--junitxml=` argument and
returns a `CompletedProcess`. The fake runner script and `_fake_runner` go; so does
`test_partial_report_is_no_verdict`. `test_behavioural_change` asserts the command:
`[sys.executable, "-m", "pytest"]` first, `--tb=no`, `--maxfail=0`, `-p no:cacheprovider`,
one `--junitxml=`, the node id last; `--test` is refused (argparse, exit 2).

## Risks / Trade-offs

- [A project whose runner is not `python -m pytest` cannot use the gate] → true today as
  well (the default was the only exercised path); the input returns with its consumer.
- [The gate's run writes a cache of its own] → `-o cache_dir=<tmp>/cache` lives in the
  script's temporary directory and goes with it; the project's `.pytest_cache` and its
  own runs are untouched.

## Migration Plan

Same PR (145); the archive of this change carries the spec.
