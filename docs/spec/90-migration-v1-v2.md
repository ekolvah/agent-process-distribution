# Migration v1 → v2

**Question this document answers:** in which order v1 is replaced by v2, what stays, what
goes, and what happens to this file afterwards.

Status: draft — deleted when every step below has merged and the v2 ADR is accepted.

## Requirements

- **MIGR-1** (MUST) Same repository, major version v2: history and the marketplace URL
  are kept. A new repository would lose both and gain nothing.
- **MIGR-2** (MUST) Five PRs, each leaving CI green, in this order:
  1. remove the control plane (`agent_orchestrator`, `delivery_state`, `state.json`,
     roles catalogue routes) and the Stop gate's budget logic;
  2. remove Copier, `template/`, `adopt_agent_process`, `template_drift`,
     `check_consumer_test_collision`, `tests/publisher/*` render tests;
  3. move the procedure into `skills/` with `scripts/` inside; plugin hooks resolve from
     `${CLAUDE_PLUGIN_ROOT}`;
  4. replace the review workflow and branch-protection scripts with the advisory
     workflows and the ruleset JSON;
  5. add `/agent-process:init` and the migration note for the second project.
- **MIGR-3** (MUST) One ADR "v2" supersedes ADR 0011, 0013, 0015, 0019, 0021, 0022, 0023;
  the others stay as history with no edits.
- **MIGR-4** (MUST) Each PR flips the `Status:` line of the specs it implements from
  `draft` to `accepted` and updates `agent-process.md` or deletes the part it replaced, so
  the "target vs. current" gap in `README.md` shrinks with every merge.
- **MIGR-5** (MUST) The second consumer project is migrated after step 5 by removing its
  `.agent-process/` payload and running `init`; the note from step 5 is the runbook.
- **MIGR-6** (SHOULD) Open questions in the specs are settled by observation during the
  step that touches them and recorded in the v2 ADR, not by reading vendor docs.

## Rationale

The order is chosen so each step deletes more than it adds and never leaves a consumer
without a working path: the control plane and Copier go first because nothing else depends
on them; the skill move comes before the review change so the new `wait_for_pr` has a
home; `init` is last because it needs everything else to exist.

## Non-goals

- Migrating consumers before step 5.
- Rewriting history or ADR text.

## Open questions

- Whether step 2 and step 3 are safer as one PR (the plugin hooks currently target
  `.agent-process/scripts/hooks.py`, which step 2 leaves in place and step 3 moves).

## Traceability

- This spec set (#105).
- Discussion of 2026-09-12 (v2 Q&A).
