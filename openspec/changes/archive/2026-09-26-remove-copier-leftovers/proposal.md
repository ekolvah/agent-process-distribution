## Why

`v2-0b-delete-copier-mirror` (#119, ADR 0027) deleted the Copier mirror, but v1 leftovers
stayed:

- `.agent-process/copier-answers.yml` is read by no script. Its data is wrong:
  `required_status_contexts: quality / quality` (the ruleset requires `agent-process / quality`),
  and `ci_checks` lists 7 checks against 9 in the `ci_check.py` registry. Its only readers are
  `tests/agent_process/test_delivery_gate_wiring.py::TestTelemetryAttribution`, which takes
  `github_repository` and `repo_name` from it, and the scan list of
  `tests/publisher/test_reusable_workflows.py::test_the_v1_quality_callee_is_gone`.
- `docs/adr/0013-*.md` and `docs/adr/0026-*.md` lie outside `.agent-process/docs/adr/`, where
  the `maintenance` requirement "Decisions are MADR records" puts every ADR, so
  `tests/agent_process/test_adr_records.py` (`_ADR_DIR`) never checks them.
- Remnants the word `copier` does not match: the `skipif(not _CLAUDE_SETTINGS.is_file(),
  reason="the generated project does not include the optional Claude adapter")` in
  `test_delivery_gate_wiring.py` (twice) and `test_navigation_policy.py`. Nothing renders
  these tests into a project without `.claude/settings.json` any more, so the guard can only
  turn a missing file into a silent skip (§IV). `docs/telemetry-measurement-setup.md:38-41`
  still describes "the Copier render" and an `init` step that telemetry's exit (ADR 0029) cancelled.

This change has a tracking issue (#206).

## What Changes

- Delete `.agent-process/copier-answers.yml`. `TestTelemetryAttribution` checks the
  attribute pairs against each other instead of against the answers (design D1). The scan
  in `test_the_v1_quality_callee_is_gone` drops the file.
- `git mv` ADR 0013 and ADR 0026 into `.agent-process/docs/adr/` and fix the links to them.
- Drop the dead `skipif` guards, and reword the "every render" docstring of
  `TestCodexHookWiring` and the `docs/adr/` directory name in the docstrings of
  `test_adr_records.py` and `test_doc_narrative.py`.
- Rewrite the stale paragraph of `docs/telemetry-measurement-setup.md`.
- New tests: `test_the_copier_answers_are_gone` and a catalogue test that no ADR file lives
  outside `.agent-process/docs/adr/`.

## Capabilities

### New Capabilities

### Modified Capabilities

None. The move brings the repository in line with the existing `maintenance` requirement
"Decisions are MADR records"; no requirement changes, so the change sets `skip_specs: true`.

## Impact

- Removed: `.agent-process/copier-answers.yml`.
- Moved: `docs/adr/0013-template-source-self-hosting.md`,
  `docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md` →
  `.agent-process/docs/adr/` (0026's link to `../telemetry-measurement-setup.md` becomes
  `../../../docs/telemetry-measurement-setup.md`).
- Edited: `tests/agent_process/test_delivery_gate_wiring.py`,
  `tests/agent_process/test_navigation_policy.py`, `tests/agent_process/test_adr_records.py`,
  `tests/agent_process/test_doc_narrative.py` (docstrings only),
  `tests/publisher/test_reusable_workflows.py`, `docs/telemetry-measurement-setup.md`.
- Not touched: ADR 0012 and ADR 0017 (design D2), and the historical text of ADR 0027:160
  and of the moved ADR 0026 (Copier answers, deleted drift tests), which stay as history under
  the same rule; the consumer-render branch
  `_has_product_scope` of `.agent-process/scripts/ci_check.py` and its test (design D3).
