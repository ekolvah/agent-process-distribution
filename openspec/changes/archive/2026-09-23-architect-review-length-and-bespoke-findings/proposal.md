## Why

Issue 149. The architect review is the plan-stage enforcement of §VII and of goal-function
item 2 (`principles.md`: "if the solution could be half its length, rewrite it"; no
artefact, script or infrastructure a task does not need). Its contract — `## Architect
review` of `skills/agent-process/SKILL.md` — names one simplicity finding: "A simpler
design … is a finding". It does not name the two forms of over-engineering a plan of this
repository actually produces:

- a rule text (or a spec sentence) longer than the words its tests assert — an explanation
  in parentheses, a "why" inside the rule, a clause the issue never asked for;
- a new script or check without an observed problem it closes (the rule "standard over
  bespoke checks" lives in the person's memory only, not in the repository).

Observed on issue 146 (`planning-rules-review-rounds`, 2026-09-19): round 2 of the review
approved a plan whose three rule texts were about twice the length their tests assert and
carried a fourth-round clause the issue had not asked for; the person caught it at
solution review, round 3 approved the tightened plan. The reviewer applied §VII in name
and missed both forms because its contract names neither.

Naming them is not enough (solution review of this change, 2026-09-20): the contract
already named "a simpler design" and the reviewer wrote `none`. `## Findings` is a free
list in prose — a class the reviewer did not check leaves no trace, `none` reads the same
whether six classes were checked or none (§IV, a silent skip), and nothing outside the
reviewer's judgement reads the file except the first line of `## Verdict`.

The standard for a result an LLM must not skip parts of is a contract in JSON Schema,
validated by a standard validator; no spec-driven framework (Spec Kit's `analyze`, BMAD's
checklists, Superpowers' review gates) enforces its review output — each is a prompt.

Replanned after PR 157 (issue comment, 2026-09-23): the contract moved into the portable
skill `skills/agent-process/`, and `.agent-process/` is the publisher's control plane, not
delivered to a consumer — so the schema and every check of it belong in the skill. The
earlier plan's Stop hook in `agents/architect-reviewer.md` could never run: the reviewer is
a plugin agent, and "plugin subagents don't support the `hooks`, `mcpServers`, or
`permissionMode` frontmatter fields. These fields are ignored when loading agents from a
plugin." (https://code.claude.com/docs/en/sub-agents, 2026-09-23). design.md D2–D4 hold
the observations the decisions rest on.

## What Changes

- `skills/agent-process/architect-review.schema.json` (new): the review contract —
  `verdict` (`approve`/`rework`), `reviewer` (`architect-reviewer`/`self-review`), `reasoning`, `classes` with the eight finding classes the
  skill already names or issue 149 adds (`simpler`, `map`, `red`, `platform`, `replaced`,
  `catcher`, `length`, `bespoke`), each `{evidence (non-empty), result (ok|finding),
  finding {principle, artifact, what, change} when result is finding}`, and
  `scenario_coverage`; the evidence each class requires is its `description`.
- `skills/agent-process/SKILL.md`, `## Architect review`: the file is
  `architect-review.json`, valid against the schema; the prose finding list goes — the
  classes are the schema's; `create_tracking_issue.py` validates the review before it
  creates anything, and its errors go back to the reviewer. Group 0: the gate validates the
  review and reads its verdict.
- `skills/agent-process/scripts/start_change.py`: `verdict()` reads JSON after validating
  it with `jsonschema` (imported inside the call; absent → exit 2, `architect review not
  validated: …`); `create_tracking_issue.py` calls it first — invalid or `rework` → exit 2,
  no issue created. One validator, both carriers, both ends of the plan.
- `agents/architect-reviewer.md`: writes `architect-review.json` and reads the schema; no
  hook.
- `.agent-process/requirements.in` / `requirements.txt`: `jsonschema` pinned for the
  publisher's own runs and CI. A consumer's `jsonschema` is an environment prerequisite
  the installer (issue 155) names, like `gh` and `npx` — not a file of its footprint.
- Tests: `tests/publisher/test_planning_workflow.py` — the words of the finding list move
  to the schema (required classes, descriptions), two new tests for the two new scenarios;
  `tests/publisher/test_delivery_scripts.py` — the fixture writes the JSON, one test for the
  invalid file at both scripts, one for the absent validator;
  `tests/publisher/test_plugin.py` — the package file set includes the schema.
- **RENAMED** `architect-review.md` → `architect-review.json` wherever the process names
  it: specs `planning`, `implementation` (`Verdict is rework`), `roles`;
  `openspec/config.yaml` (`context`), `AGENTS.md`, `.claude/rules/workflow.md`,
  `.agents/orchestration/roles.yaml`, `.agent-process/docs/architecture/agent-process.md`;
  ADR 0027 gains one bullet.
- Not edited: `.agent-process/scripts/hooks.py`, the round limit, `principles.md`, the
  OpenSpec schema.

## Capabilities

### New Capabilities

none

### Modified Capabilities

- `planning`: the architect review is a JSON file valid against the review schema — one
  entry per finding class with its evidence; the propose tail refuses an invalid file; the
  over-long rule and the bespoke check are classes.
- `implementation`: `start_change` validates the review file and reads its verdict.
- `roles`: both carriers write `architect-review.json`, which states which of the two wrote it.

## Impact

Added: `skills/agent-process/architect-review.schema.json`. Edited:
`skills/agent-process/SKILL.md`, `skills/agent-process/scripts/start_change.py`,
`skills/agent-process/scripts/create_tracking_issue.py`, `agents/architect-reviewer.md`,
`openspec/config.yaml`, `.agent-process/requirements.in`,
`.agent-process/requirements.txt`, `tests/publisher/test_planning_workflow.py`,
`tests/publisher/test_delivery_scripts.py`, `tests/publisher/test_plugin.py`,
`openspec/specs/{planning,implementation,roles}/spec.md` (through the archive),
`AGENTS.md`, `.claude/rules/workflow.md`, `.agents/orchestration/roles.yaml`,
`.agent-process/docs/architecture/agent-process.md`,
`.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`.
Removed: nothing. One PR; the tracking issue is 149.
