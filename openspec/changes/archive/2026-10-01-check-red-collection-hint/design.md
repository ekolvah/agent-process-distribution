## Context

See proposal.md — Why for the reproduction. `check_red` stops at the `_COMPLETE_RUN` check
(rc ∉ {0, 1, 5}) and prints only the rc and the pytest tail, which already names the module
that failed at collection (`ERROR tests/test_greet.py`). The report pytest leaves on that
path is not judged, and this change keeps it so.

## Goals / Non-Goals

**Goals:** the run that hits a collection failure tells its caller — planner probe or
implementer — the next action, at the moment of failure.

**Non-Goals:** judging a collection failure as RED; changing exit codes; reading the report
or pytest's text output to decide whether to print the hint.

## Decisions

**D1 — One conditioned sentence on every incomplete run.** The incomplete-run message gains
a fixed sentence: a test module that fails at collection runs no test; if its import target
does not exist yet, add it as a stub whose body raises `NotImplementedError` and re-run on
the same node ids. Alternative — print it only when the report left by the run has a
`<error message="collection failure">` testcase (observed for rc 4 and rc 2): rejected
(architect review, finding `simpler`); it adds an XML read and a helper whose only gain is
silence on a Ctrl-C, a usage error or an internal error, and the conditioned wording already
keeps those cases from being misdirected. It also ties the hint to a junitxml attribute
that a pytest release could rename.

**D2 — No SKILL.md sentence.** Group 1 is loaded by every planner session; the gate's own
stderr reaches the same reader when the case arises, at the cost of one extra `check_red`
call per change that tests new code. Alternative — a Group 1 rule plus a delta requirement
and an asserted phrase: rejected (architect review, finding `length`). This repository's
`.claude/rules/testing.md` keeps its existing stub rule unchanged.

**D3 — Stub, not import-inside-the-test.** Both reach a judgeable RED. The stub keeps the
import at module top and makes the failure `NotImplementedError` in the test body, the rule
already in `.claude/rules/testing.md`; this repository's own tests import inside the test
body for a different reason (a missing script fails its own scenario, not the module). The
hint names the stub only — one next action.

**D4 — No new script.** The sentence extends the existing gate's message (issue #251); no
standard tool knows `check_red`'s boundary.

## Risks / Trade-offs

- [pytest ends an import error at collection as a complete run] → the hint would not
  print. The scenario test runs a real pytest on both spellings (node ids → rc 4, file path
  → rc 2), so a pytest release that changes this turns it red in the `agent-process /
  quality` check.
- [A project's `addopts` carries `--continue-on-collection-errors`] → the run completes
  (rc 1) and the existing not-RED branch already names the module as not run, without the
  hint. Accepted: the flag is the project's choice, and the verdict is still not RED.
- Rollback: revert the PR; no state or data migration.
