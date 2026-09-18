## Why

Two reworks of PR 137 (`v2-2b-review-by-apps`) came from one mistake: a design rested on
a platform behaviour nobody had observed (issue 138). `pull_request_review_thread` was
proposed as a workflow trigger and GitHub rejected the file (`397c54f`, `Invalid workflow
file … Unexpected value`); design D6 assumed a run started by a review event re-runs the
required check on the unchanged head, and head `a1d0bad` showed every event is a required
context of its own (`pull_request` run `35262221116` red and the PR `BLOCKED` beside three
green `pull_request_review` runs). Both facts were checkable in minutes — the events
reference page, or one throwaway run and `gh pr view --json
mergeStateStatus,statusCheckRollup` — and each cost a fixer round, a spec delta and an ADR
entry instead. Reproduction: `python -m pytest tests/publisher/test_planning_workflow.py -q
-k platform` — the `proposal` rule of `openspec/config.yaml` names reading and asking and a
bug's reproduction, never an observation of a platform fact, and the Architect review entry
of the `tasks` rule lists three findings, none for a fact asserted without one. Root cause:
nothing in the propose run distinguishes an observed platform behaviour from an inferred
one, so the inference reaches the design and the PR's review is the first place it meets
the platform.

## What Changes

- `openspec/config.yaml`, `rules.proposal`: a fourth bullet — a design that rests on a
  platform behaviour (an event, a permission, a merge rule, a token scope, a CLI flag)
  verifies it on the platform before the proposal is written and records the observation,
  not the inference: the reference page (URL and the sentence) or the run id / command and
  its output, under **Why** or in `design.md`; a listing or a name is not an observation;
  one already on record (an ADR entry, an archived change) is pointed at, not repeated.
- `openspec/config.yaml`, `rules.tasks`, Architect review entry: a fourth finding — a
  platform behaviour a design rests on that is asserted, not observed.
- `openspec/specs/planning/spec.md`: one added requirement, "Platform facts are observed
  before a design rests on them", two scenarios.
- `tests/publisher/test_planning_workflow.py`: two tests, one per scenario, on the rule
  text (the pattern of the file).
- `.agent-process/docs/adr/0027-…md`: one entry that points at the two facts above where
  the ADR already records them, says what would have shown each in minutes, and records
  the decision on the deterministic check; `agent-process.md`, Planning: the
  `proposal` rule's summary names the observation.
- No new script (owner's decision, 2026-09-18): of the two deterministic checks issue 138
  names, the event set against the required contexts has nothing to check since the
  review-event trigger was withdrawn (`v2-2b-push-only`), and the workflow-file check is
  the standard `actionlint` — a unit of its own, tracked by a separate issue.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `planning`: added requirement "Platform facts are observed before a design rests on
  them" — a proposal whose design rests on a platform behaviour SHALL record the
  observation before the design; a behaviour asserted without one SHALL be an
  architect-review finding.

## Impact

- Edited: `openspec/config.yaml` (one bullet of `rules.proposal`, one clause of the
  Architect review entry of `rules.tasks`), `openspec/specs/planning/spec.md` (via this
  change's delta, applied by the archive), `tests/publisher/test_planning_workflow.py`
  (two tests added), `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`
  (one entry added), `.agent-process/docs/architecture/agent-process.md` (one clause of the
  Planning section).
- Added, removed: none. No code path changes; `agents/architect-reviewer.md` reads its
  contract from the rule and is untouched.
- Every change proposed after the archive is written under the rule and reviewed for the
  finding; the next v2 step (`v2-2c-pr-link-native`, issue 131) rests on
  `closingIssuesReferences` and a reusable workflow and is the first to be proposed under it.
