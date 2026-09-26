## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py remove-copier-leftovers --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 206. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_reusable_workflows.py::test_the_copier_answers_are_gone`, next to `test_the_pr_link_gate_is_gone`: assert `ROOT / ".agent-process" / "copier-answers.yml"` does not exist. Add `tests/agent_process/test_adr_records.py::TestAdrCatalogue::test_no_record_outside_the_catalogue`: list tracked files with `git ls-files -z` (subprocess, `encoding="utf-8"`), and assert that no path whose file name matches `_RECORD_NAME` lies outside `_ADR_DIR`. Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_reusable_workflows.py::test_the_copier_answers_are_gone tests/agent_process/test_adr_records.py::TestAdrCatalogue::test_no_record_outside_the_catalogue` and verify that both fail in the test body; commit as `test: copier leftovers are gone`

## 2. Answers file and dead guards

- [x] 2.1 In `tests/agent_process/test_delivery_gate_wiring.py`, delete `_COPIER_ANSWERS`, `_answers()`, the `yaml` import, and the `pytest` import (unused once the `skipif` guards go; ruff `F401`). Reword the `TestTelemetryAttribution` docstring so that it no longer cites "the optional-adapter `skipif`". Rewrite `TestTelemetryAttribution` per design D1: `vcs.repository.name` is non-empty and matches `^[^/\s]+/[^/\s]+$`; `vcs.repository.url.full == f"https://github.com/{name}"`, and `len(attributes) >= 2`. Drop the blank-URL branch and its comment, and the "which of the two answers wins" comment. Remove the `skipif` from `test_claude_wires_no_stop_hook` and `TestTelemetryAttribution` (design D4), and reword the `TestCodexHookWiring` docstring so that it no longer says "every render" or contrasts with a skip. Remove the same `skipif` from `TestClaudeHookWiring` in `tests/agent_process/test_navigation_policy.py`. Verify `python -m pytest tests/agent_process/test_delivery_gate_wiring.py tests/agent_process/test_navigation_policy.py -q` and `python -m ruff check tests/agent_process` pass
- [x] 2.2 Delete `.agent-process/copier-answers.yml`, and drop it from the scan list of `test_the_v1_quality_callee_is_gone` (the loop keeps `sorted(WORKFLOWS.iterdir())`). Verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes; commit 2.1 and 2.2 as `chore: remove the copier answers file`

## 3. ADR catalogue and docs

- [x] 3.1 `git mv docs/adr/0013-template-source-self-hosting.md docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md .agent-process/docs/adr/`. In the moved 0026, change the link `../telemetry-measurement-setup.md` to `../../../docs/telemetry-measurement-setup.md`. In `docs/telemetry-measurement-setup.md:145`, change the link to `../.agent-process/docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md`. Replace the stale `docs/adr/` directory name with `.agent-process/docs/adr/` in the docstrings of `tests/agent_process/test_adr_records.py` (lines 1 and 3) and `tests/agent_process/test_doc_narrative.py` (lines 41 and 206)
- [x] 3.2 In `docs/telemetry-measurement-setup.md`, replace lines 38-41 ("Until `init` (v2-2) writes the pairs … (#119).") with: each adoption carries its own value; an adopter sets the pairs by hand, because telemetry left the v2 migration (a link to ADR 0029, `0029-telemetry-leaves-the-v2-migration.md`). Keep the URL-pair sentence that follows. Verify `python -m pytest tests/agent_process/test_adr_records.py tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py -q` passes; commit 3.1 and 3.2 as `docs: move the last ADRs into the catalogue`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py`, and verify that both pass

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py remove-copier-leftovers`. Verify that it archives the change, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "chore: remove-copier-leftovers" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`), carries the scenario → test map, and lists the deferral of design D3
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`). The removal is pinned by `tests/publisher/test_reusable_workflows.py::test_the_copier_answers_are_gone`; the existing `maintenance` requirement "Decisions are MADR records" gains `tests/agent_process/test_adr_records.py::TestAdrCatalogue::test_no_record_outside_the_catalogue`
