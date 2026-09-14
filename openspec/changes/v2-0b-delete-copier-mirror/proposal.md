## Why

Nobody but this repository consumes the v1 Copier render (the second consumer, #117, keeps
its copied files and migrates after v2-2), yet every v2 step that deletes a root file must
also delete its `template/` twin, its `.jinja`, its `template-drift-allowlist.yml` row and
the render tests that reach it — the drift gate roughly doubles the diff of v2-1 and v2-2
for a mechanism v2-2 removes anyway. Deleting the mirror first (step 0b of #107, issue #119)
makes every later step a root-only change.

## What Changes

- **BREAKING** — the Copier source (`template/`, `copier.yml`) and its self-hosting drift
  gate (`template_drift.py`, `template-drift-allowlist.yml`) are deleted. Until v2-2 lands
  `init`, the repository has no installation path; accepted, the process is used only here.
- The v1 installation and update scripts that exist only for the render are deleted:
  `adopt_agent_process.py`, `check_consumer_test_collision.py`, `bootstrap_github_project.py`.
- The render fixture (`tests/publisher/conftest.py`) and every publisher test that renders
  the template or reads `template/` are deleted; `reusable-quality.yml` stops installing
  `copier`; the `template/` exclusions in `test_doc_links.py`, `test_doc_narrative.py`,
  `test_branch_protection.py` and `ci_check.py` go.
- `agent-process.md` loses §Test suite ownership's render paragraphs and §Maintaining this
  distribution; `agent-process-installation.md` gets a one-line retirement notice; ADR 0027
  records the observation.
- Kept: `.agent-process/copier-answers.yml` — `tests/agent_process/test_delivery_gate_wiring.py`
  reads it as the source of the Project attribution; it goes with v2-2 together with those
  tests. Kept: the reusable workflows and the thin callers in `.github/workflows/`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `distribution`: REMOVED `Layered delivery through Copier` — the Codex skills and the
  provider-neutral core no longer reach a consumer as a Copier render; the Claude plugin
  marketplace and the pinned reusable workflows are unchanged and are restated by v2-2 together
  with `init`. The other three requirements stay as written; the scenarios `Rendered payload`
  and `Process change` have no render to observe until v2-2 (recorded in `design.md`).

## Impact

- Deleted: `template/` (whole tree), `copier.yml`, `template-drift-allowlist.yml`,
  `.agent-process/scripts/{template_drift,adopt_agent_process,check_consumer_test_collision,bootstrap_github_project}.py`,
  `tests/publisher/{conftest,test_template_drift,test_project_bootstrap_template,test_self_installed_process,test_payload_layout,test_bare_consumer_quality,test_existing_project_installation,test_existing_project_update,test_workflow_references,test_test_suite_ownership}.py`.
- Edited: `.github/workflows/reusable-quality.yml`, `tests/publisher/test_reusable_workflows.py`
  (three tests read `template/`), `tests/agent_process/{test_doc_links,test_doc_narrative,test_branch_protection,test_issue_branch,test_delivery_gate_wiring}.py`
  (`test_issue_branch` loaded the template's pristine `project_settings.py` as its unconfigured fixture; it now blanks the real module's IDs), `AGENTS.md` (the `adopt_agent_process.py` bullet),
  `.agent-process/scripts/ci_check.py`, `.agent-process/docs/architecture/{agent-process,agent-process-installation}.md`,
  ADR 0027, `openspec/specs/distribution/spec.md` (through the archive).
- Consumers: none affected — no repository runs `copier update` against this source.
- Later steps: v2-1 (#111) and v2-2 (#112) are already replanned as root-only changes on top of this one.
