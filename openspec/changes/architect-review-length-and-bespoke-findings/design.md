## Context

See proposal.md — Why. On `main` after #157 the review contract is `## Architect review` of
`skills/agent-process/SKILL.md`; the review is `architect-review.md` with three prose
sections; its only machine reader is `skills/agent-process/scripts/start_change.py`
`verdict()`, which takes the first line under `## Verdict`. `create_tracking_issue.py`, the
propose tail, imports from `start_change` and reads no review. The seven skill scripts
import the standard library only. `agents/architect-reviewer.md` is a plugin agent (ADR
0027) and reads its contract from the skill. `tests/publisher/test_planning_workflow.py`
proves the contract by the words of `SKILL.md`; `tests/publisher/test_plugin.py` pins the
package's file set.

This change replaces no project-declared input and drops no guard: the first-line read of
`verdict()` becomes a validation of the whole file, and a second reader (the propose tail)
is added, so the `design` rule's failure-mode list does not apply.

Observed:

- Sub-agents docs (https://code.claude.com/docs/en/sub-agents, 2026-09-23): "For security
  reasons, plugin subagents don't support the `hooks`, `mcpServers`, or `permissionMode`
  frontmatter fields. These fields are ignored when loading agents from a plugin. If you
  need them, copy the agent file into `.claude/agents/` or `~/.claude/agents/`." The plugins
  reference says the same.
- `jsonschema` 4.26.0 (Python 3.12.8), `Draft202012Validator` on the draft schema, errors
  sorted by path, printed as `f"{e.json_path}: {e.message}"`: a file with every class,
  non-empty evidence and `result: ok` → no error; a file with `length` missing,
  `simpler.evidence` `""` and `map.result: finding` without `finding` →
  `$.classes: 'length' is a required property`,
  `$.classes.map: 'finding' is a required property`,
  `$.classes.simpler.evidence: '' should be non-empty`. Its requirements: `attrs`,
  `jsonschema-specifications`, `referencing`, `rpds-py`.
- `codex exec --output-schema` with the draft schema → HTTP 400 `'if' is not permitted`
  (2026-09-20, the OpenAI strict subset).

## Goals / Non-Goals

**Goals:**

- The reviewer cannot leave a class unchecked without a validation error naming it (§IV):
  eight required class entries, each with a non-empty evidence and a result.
- The two findings of issue 149 are classes of the same contract, not sentences.
- The contract, its validation and the reviewer are all on the portable side of the
  package boundary; nothing the consumer runs points into `.agent-process/`.
- Both carriers pass the same check at both ends of the plan: the propose tail and the
  apply gate.

**Non-Goals:**

- Judging the evidence: whether "the rule is 41 words, the test asserts 12" is a true count
  is the person's read at solution review; the schema proves that the count was written.
- Installing `jsonschema` in a consumer (#155) — this change names it as a prerequisite.
- The reviewer's reference to `.agent-process/docs/architecture/principles.md` (a
  control-plane path, as on `main` today).
- Changing the round limit, `principles.md`, or the OpenSpec schema.

## Decisions

- **D1 — The contract is one JSON Schema file in the skill, and the class descriptions are
  the evidence definitions.** `skills/agent-process/architect-review.schema.json` (draft
  2020-12): `verdict` enum `approve|rework`, `reviewer` enum `architect-reviewer|self-review`
  (where the Codex self-review is stated, as the verdict line stated it before — `roles.yaml`
  `adapter_independence`), `reasoning`, `classes` with eight required keys
  (`simpler`, `map`, `red`, `platform`, `replaced`, `catcher`, `length`, `bespoke`),
  `scenario_coverage` array of `{capability, scenario, reason}`; `$defs.class` =
  `{evidence: non-empty string, result: ok|finding, finding?: {principle, artifact, what,
  change}}` with `if result == finding then finding required`; `additionalProperties:
  false` throughout. Each class carries a `description` saying what its evidence is — e.g.
  `length`: "for each rule or spec sentence the plan adds or edits, its word count and the
  count of the words its tests assert"; `bespoke`: "for each script, check or file the plan
  adds, the observed problem it closes (issue, PR, run) or `none`". The tests read the
  schema, so the reviewer, the validator and the tests share one source; `SKILL.md` names
  the file and the schema, nothing of the shape. The scripts find it as
  `SCRIPT_DIR.parent / "architect-review.schema.json"` — from the skill, wherever it is
  installed, as `SCRIPT_DIR` already is. *Alternative:* `.agent-process/` — rejected: not
  delivered to a consumer (#157 D2). *Alternative:* keep the classes in `SKILL.md` prose and
  the schema structural only — rejected: two sources for one list, and the prose is what
  the reviewer read past.
- **D2 — No hook: the propose tail validates.** The Claude reviewer is a plugin agent, whose
  frontmatter `hooks` are ignored (observed above) — a `Stop` hook there would never run.
  `create_tracking_issue.py` calls `start_change.verdict()` before any `gh` call: an invalid
  file or a verdict other than `approve` → exit 2 with the errors, no issue created; the
  planner (either carrier) sends the errors back to the reviewer and reviews again, as on
  `rework`. The catchers reached: `create_tracking_issue.py` in the propose run, then
  `start_change.py` in Group 0 of the apply — both on every change, both carriers.
  *Alternative:* a `SubagentStop` hook in the plugin's `hooks/hooks.json` — rejected: #157
  keeps hooks out of the package (`test_package_has_no_installer_state`), and it would add
  a hook to every consumer session for one subagent. *Alternative:* a copy of the agent in
  `.claude/agents/` so its frontmatter hook loads — rejected: an installer-owned file
  outside #155's footprint, and a second copy of the reviewer. *Alternative:* a
  `SubagentStop` hook in `.claude/settings.json` — rejected: control plane, publisher only.
- **D3 — The validator is the `jsonschema` library, imported on the call.** `verdict()`:
  `import jsonschema` inside the function (the other scripts that import `start_change`
  keep running without it); `ModuleNotFoundError` → `ValueError("architect review not
  validated: <error>")`, exit 2 through the existing `main()` mapping — visible, not a
  pass; load the file (missing → `FileNotFoundError`, invalid JSON → the decoder's error,
  both exit 2); `Draft202012Validator(schema).iter_errors(data)` sorted by `error.path`,
  each `f"{review}: {error.json_path}: {error.message}"`, any → `ValueError` joined by
  newlines; else return `data["verdict"]`. *Alternative:* the `check-jsonschema` CLI —
  rejected: with no hook and no per-carrier command there is no caller for a CLI, and it
  wraps the same library. *Alternative:* a stdlib check of the schema's `required` lists —
  rejected by the person (2026-09-23): a bespoke subset of JSON Schema.
- **D4 — The dependency crosses the package boundary as a prerequisite, not a file.** The
  publisher pins `jsonschema` in `.agent-process/requirements.in` (its CI and the
  installation guide install `requirements.txt`). A consumer runs the skill scripts with its
  own Python; `jsonschema` there is an environment prerequisite like `gh` and `npx`, which
  the installer (#155) names and checks — its repository footprint list is unchanged.
  Until then the absent library is the visible exit 2 of D3.
- **D5 — The file is renamed, not kept beside a `.md`.** `architect-review.md` →
  `architect-review.json` in every process file that names it (proposal, Impact); the specs
  carry the rename as MODIFIED requirements of `planning`, `implementation` (`Verdict is
  rework`) and `roles`. *Alternative:* JSON as a fourth section of the `.md` — rejected: two
  formats in one file, and the validator would need a bespoke extraction.
- **D6 — The tests assert the schema and the scripts, not sentences.** The tests of the
  finding list's words (`test_review_finding`, `test_review_sections_carry_their_contents`,
  `test_asserted_platform_fact`, `test_untraceable_catcher`) read the schema: the eight keys
  are `required`, each class `description` names its evidence, a class needs `evidence` and
  `result`, a `finding` result needs `finding`, a coverage entry needs its three fields.
  `test_verdict_line_the_gate_reads` becomes the JSON read: `approve` is returned,
  `Approved` is a validation error. New: `test_over_long_rule_or_bespoke_check` (the two
  classes); `test_review_not_valid` (the invalid file at both scripts, exit 2, no issue and
  no branch, the three messages); `test_review_validator_absent` (`jsonschema` masked →
  exit 2 naming it).

## Risks / Trade-offs

- [The reviewer writes filler evidence to satisfy `minLength: 1`] → The evidence is in the
  file the person reads at solution review, one line per class; filler is visible, `none`
  on a prose list was not.
- [A consumer without `jsonschema` cannot finish a propose run] → Exit 2 naming the missing
  module at the tail, before any issue exists; the fix is one `pip install`, and #155 names
  the prerequisite.
- [The reviewer cannot make the file valid] → The planner sees the errors at the tail and
  re-invokes the reviewer with them — a round the person sees, bounded by the propose run.
- [A reviewer copy older than this change — the plugin installed from the marketplace before
  it refreshes — still writes `architect-review.md`] → `create_tracking_issue.py` exits 2
  with `no architect review at …architect-review.json` at the tail of that propose run,
  before any issue exists.
- [The skill scripts gain their first third-party import] → Only `verdict()`, lazily;
  `set_status`, `check_red`, `wait_for_pr`, `resolve_review_thread`, `archive_change` stay
  stdlib-only.
