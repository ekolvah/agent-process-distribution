## Why

Tracking issue (#126), step 1c of the v2 plan (#107), after the archive-before-PR change (#125).

The planning schema of this repository is a fork: `openspec/schemas/agent-process/` was made
with `openspec schema fork spec-driven` (v2-1b, #123) to add the architect review as a fifth
artifact. Observed after the merge: `openspec schema` is `[experimental]` in 1.13.0 and has no
`extends`, so a fork is a full copy of the upstream schema — 230 of its 269 lines and four of
its five templates are `spec-driven` verbatim. `openspec update` no longer brings upstream
changes of `spec-driven` into this repository, and the `@1.13.0` pin freezes the fork rather
than a dependency. OpenSpec moves fast; the process must be able to follow it. The review
itself stays: it returns `rework` regularly (#121, #123, #127's plan) and pays for itself.

Root cause: the review was modelled as a schema artifact, which is the one extension point
OpenSpec 1.13.0 does not support without a copy. The same gate is expressible with the
extension point it does support — `rules` of `openspec/config.yaml`, injected into
`instructions <artifact>` — plus the Group 0 `grep` on the verdict that every `tasks.md`
already carries.

## What Changes

- `openspec/config.yaml`: `schema: spec-driven`. The `tasks` rule gains the last step of
  the propose run — invoke the architect review (Claude: the `architect-reviewer` subagent;
  Codex: the planner as a self-review), which writes `openspec/changes/<change>/architect-review.md`;
  on `rework` the planner applies or answers every finding in the artifact it names and the
  review runs again; the propose run ends on `approve`. The review contract (Verdict /
  Findings / Scenario coverage, principles §I–VII, the map-gap and `no RED` findings) moves
  from the schema `instruction` and template into that rule — the one text both carriers
  read. `rules.architect-review` (a key of no `spec-driven` artifact) folds into it.
- The apply gate is task 0.1 of every `tasks.md` alone (`grep -q "^approve"` on the verdict,
  put there by the `tasks` rule): the fork's `apply.instruction` said the same thing a second
  time and goes with the fork.
- `openspec/schemas/` removed. **BREAKING** for nothing outside this repository: the schema
  was never published.
- `agents/architect-reviewer.md`: reads the contract from the `tasks` rule of
  `openspec/config.yaml` and the four artifacts of the change directly (there is no
  `instructions architect-review` to run); still writes only `architect-review.md`.
- Tests (RED first): `test_roles_and_carriers` asserts `schema == spec-driven`, no
  `openspec/schemas/`, and that the `tasks` rule names the review; `test_review_finding`
  reads the contract from the `tasks` rule and a new `test_rework_verdict` its `rework` →
  re-review loop and the Group 0 `grep`; `test_forked_schema_validates` removed; a new
  `test_review_archives_with_the_change` proves on a fixture change that `openspec archive`
  moves `architect-review.md` with the change directory (`moveDirectory` in 1.13.0).
- Docs: `agent-process.md` Planning section names `spec-driven` plus the rules;
  `.claude/rules/workflow.md`, `AGENTS.md` and `.agents/orchestration/roles.yaml` stop calling
  the review an artifact of the `agent-process` schema / naming the `architect-review` rule;
  ADR 0027 gains the observation.

Loss accepted: `openspec status` shows 4/4 artifacts plus a file, and `apply.requires` does
not name the review — OpenSpec checks file existence only, so the gate was always the verdict
text.

This change is itself created on `spec-driven` (`openspec new change --schema spec-driven`):
a change on `agent-process` would delete the schema it stands on in the middle of its apply,
and `openspec status` would stop resolving it. Its `architect-review.md` is the first one
written as an extra file.

## Capabilities

### New Capabilities

none

### Modified Capabilities

- `roles`: "OpenSpec skills are the carriers of the procedure" — the process extends the
  skills only through `openspec/config.yaml` on the unmodified `spec-driven` schema, no
  forked schema; "Roles and carriers" — the review is written as `architect-review.md`, not
  as a schema artifact.
- `planning`: "Architect review is an artifact of the change" is removed and replaced by
  "Architect review is the last step of the propose run" — the `tasks` rule invokes it, the
  first delivery task is the gate, and the file archives with the change.

## Impact

Edited:
- `openspec/config.yaml` — `schema`, `rules.tasks`; `rules.architect-review` removed
- `agents/architect-reviewer.md` — procedure reads the rule, not `instructions architect-review`
- `tests/publisher/test_planning_workflow.py` — `test_roles_and_carriers`, `test_review_finding`, `test_pinned_openspec` (the reviewer no longer runs `npx`); new `test_rework_verdict`, `test_review_archives_with_the_change`
- `tests/publisher/test_openspec_valid.py` — `test_forked_schema_validates` removed
- `openspec/specs/roles/spec.md`, `openspec/specs/planning/spec.md` — via the archive of this change
- `.agent-process/docs/architecture/agent-process.md` — Planning section
- `.claude/rules/workflow.md`, `AGENTS.md`, `.agents/orchestration/roles.yaml` — wording of the review pointer and of the planner's completion evidence
- `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md` — observation

Removed:
- `openspec/schemas/agent-process/schema.yaml` and `templates/` (five files)

Deferred (issue's deferred scope): the pinning strategy for the OpenSpec CLI the skill
carriers run → installation guide.
