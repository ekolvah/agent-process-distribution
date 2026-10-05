# Design

## D1. The runner is the `python` on `PATH`

`check_red` resolves `shutil.which("python")` and runs `<that> -m pytest …` instead of
`sys.executable -m pytest …`. The `python` on `PATH` is the interpreter the consumer's tests
run under in a session: the launcher falls back to it, the baseline `pytest` pre-commit hook
runs it (`distribution` spec, "Tests run once they exist"), and this repository's declared
`test` and CI `setup` use it. The launcher runs the script with `AGENT_PROCESS_PYTHON` by
direct path, without putting the plugin environment on `PATH`, so the lookup reaches the
consumer's interpreter. Observed in this repository's session:

```
$ "$AGENT_PROCESS_PYTHON" -c "import shutil; print(shutil.which('python'))"
C:\Users\jadow\AppData\Local\Programs\Python\Python312\python.EXE
```

which has pytest 9.0.3; the issue's workaround (`AGENT_PROCESS_PYTHON=python`) is the same
interpreter. The script itself stays on the plugin environment.

Alternatives rejected:
- The launcher runs `check_red` with `python`, as it ran every script before the plugin
  environment (#334); the script needs only the standard library. Rejected: an exception to the `distribution` requirement that the launcher runs
  every script with `AGENT_PROCESS_PYTHON`; a missing `python` would end as the shell's exit
  127 instead of a named exit 2; and the runner belongs to the script however it is invoked.
- Install pytest into the plugin environment: the consumer's tests import the consumer's
  dependencies, which that environment does not have (issue 342).
- Run the declared `test` command: it is a bash command line (`ci_check.py`, `pytest -q && …`)
  to which the node ids and the gate's own flags cannot be appended (issue 112).
- A new variable naming the test interpreter: an input without an observed consumer (§VII);
  a consumer whose `python` on `PATH` is not its test interpreter (uv, poetry without an
  activated environment) is designed with that consumer.

The input the change replaces is the script's interpreter, which the caller already chose by
invoking it; the new input is the session's `PATH`. Its failure modes: no `python` on `PATH`
(D2), and a `python` without pytest or without the consumer's dependencies — a rc 1 with no
report or a collection error, both of which `check_red` already turns into exit 2 with the
pytest output (the reproduction under **Why** of the proposal is that output). No proof is
lost: the verdict still comes from the report of the run, judged as before.

## D2. No `python` on `PATH` is exit 2

`shutil.which("python")` returning `None` exits 2 before the temporary directory is made:
`check_red: \`python\` is not on PATH; the tests run under the python on PATH`. A silent fallback
to `sys.executable` would bring the issue back unseen (§IV).

## Migration and rollback

None: one script, no state. Rollback is reverting the PR. A direct
`python skills/agent-process/scripts/check_red.py` run is unchanged whenever that `python` is
the one on `PATH`.
