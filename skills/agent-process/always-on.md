# Agent process: always on

## Goal function

Every agent working in this repository optimises the same three goals, in this
strict order. They are the *why* behind §I–§VII: when two principles pull in
different directions, the higher goal decides.

1. **Minimize future bug-fixing and support.** Root cause before fix — no
   workaround or shim until the cause is named (§V). A visible anomaly beats a
   silent skip: degradation reaches the operator as a marker, not as silence
   (§IV). Bug fixes are test-first: failing test → code → green (§I).
2. **Optimize token spend**, both development and runtime. Do not produce
   artefacts, scripts, or infrastructure a task does not need (§VII); before an
   expensive step — a subagent, a web search, a wide grep — weigh whether it
   pays for itself. Watch for work for work.
3. **Preserve predictability and user control.** One PR is one logical unit;
   risky or shared-state actions are confirmed with the user even when they are
   technically permitted. The procedural half of this goal lives in
   the `agent-process` skill.

### Scripts over instructions

A deterministic step of any multi-step workflow ("check X", "make sure Y",
"extract Z") becomes **a standard, maintained tool** where one does the job (a new
dependency is still asked first, §VII), otherwise **a script with an exit code and unit
tests** on its pure functions, not a line of prose. Prohibitions become a deny-list, a
hook, or branch protection — never "remember not to do X". Trigger heuristic: the moment
a rule is phrased as "must not forget about X", X belongs in a script or a gate. When a
tool causes friction, look first for the architectural choice that causes it, not for a
workaround script.

**Rationale:** an agent skips prose items in a long pipeline; `exit 0/1` always runs.

## Claude harness

- Read narrowly: a search or an `offset`/`limit` read before a whole file. When the read-budget
  hook denies a `Read`, take the call it names; never route around it.
- Spawn a subagent only for independent work, or for research that needs more than three
  round trips; do not redo the work it reports.
- Be concise by default, in replies and in files.
- Wait for a long command with one foreground call and a raised `timeout`, never a `sleep` or
  re-read loop.
- After a compaction between the RED commit and GREEN, recover from the branch
  (`git branch --show-current`), the RED commit and one `gh issue view <N>`; do not re-read
  what the RED commit records.
