## 0. Delivery start

- [x] 0.1 `grep -q "^approve" openspec/changes/v2-1e-unfork-schema/architect-review.md` exits 0 (on `rework`: apply the findings, re-review, no delivery task runs)
- [x] 0.2 The tracking issue exists (#126, priority High — no prompt): `git fetch origin && git checkout main && git pull` → `gh issue develop -c 126 --name v2-1e-unfork-schema`; verify `git branch --show-current` prints the change name
- [x] 0.3 `python .agent-process/scripts/set_status.py 126 "In Progress" --priority High` exits 0
- [x] 0.4 Provenance: `gh issue comment 126 --body "planner: Claude; implementer: <this carrier>"`

## 1. RED first

- [x] 1.1 In `tests/publisher/test_planning_workflow.py`: drop `SCHEMA`; `test_roles_and_carriers` asserts `not (ROOT / "openspec" / "schemas").exists()`, `config["schema"] == "spec-driven"`, `set(rules) <= {"proposal", "specs", "design", "tasks"}`, and that `" ".join(rules["tasks"])` names `architect-review.md`, `architect-reviewer`, `self-review` and `approve`; `test_review_finding` asserts the contract is in the `tasks` rule (`Verdict`, `Findings`, `Scenario coverage`, `§I–VII`, `simpler`, `no RED`); new `test_rework_verdict` asserts the `tasks` rule carries `run the review again` and `the propose run ends on` `approve` (substrings only the new entry has — Group 0 already says `rework` and `re-review`, so those would not be RED), the Group 0 `grep -q "^approve"`, and `"apply" not in config.get("operations", {})` (the gate is stated once); `test_pinned_openspec` iterates `(CONFIG, ARCHIVE)` only. In `tests/publisher/test_openspec_valid.py` delete `test_forked_schema_validates`. Run `python -m pytest --junitxml=.pytest-report.xml tests/publisher` (the command AGENTS.md declares) and verify `python .agent-process/scripts/check_red.py --report .pytest-report.xml tests/publisher/test_planning_workflow.py::test_roles_and_carriers tests/publisher/test_planning_workflow.py::test_review_finding tests/publisher/test_planning_workflow.py::test_rework_verdict` exits 0
- [x] 1.2 New `test_review_archives_with_the_change` (same file): build in `tmp_path` an OpenSpec root — `openspec/specs/` (empty) and `openspec/changes/fixture/` on `spec-driven` (`.openspec.yaml` with `schema: spec-driven`, `proposal.md`, `specs/fixture/spec.md` with `## ADDED Requirements` and one requirement with one scenario, `tasks.md`, `architect-review.md` with a `## Verdict` line `approve`); run `_openspec("archive", "fixture", "-y")` from `test_openspec_valid` with `cwd=tmp_path` (add a `cwd` parameter defaulting to `ROOT`); assert exit 0 and that exactly one `openspec/changes/archive/*-fixture/architect-review.md` exists. Green from the first run: it proves OpenSpec's `moveDirectory`, not this change — so it is outside the `check_red` set, and the RED commit records `no RED: proves upstream behaviour` for it
- [x] 1.3 Commit `test(v2-1e): RED for the unfork` before any implementation

## 2. Configuration replaces the fork

- [ ] 2.1 `openspec/config.yaml`: `schema: spec-driven`; append to `rules.tasks` one entry that starts with `Architect review — after tasks.md is written and before the artifacts are reported ready, not a group of tasks.md:` and carries the invocation (Claude: the `architect-reviewer` subagent; Codex: the planner as a self-review), the output file `openspec/changes/<change>/architect-review.md`, its three sections (`## Verdict` — a line starting with `approve` or `rework` plus one line of reasoning; `## Findings` — `§<principle> · <artifact>:<heading> — what is wrong → what to change`, or `none`; `## Scenario coverage` — every scenario no test proves with the `n/a: <reason>` of `tasks.md`), the review lens (principles §I–VII; a simpler design meeting the same scenarios is a finding; a scenario missing from the map is a finding, and so is a Group 1 that names no test without a `no RED` task; point at the artifacts, do not restate them), and the loop (on `rework` apply or answer every finding in the artifact it names, run the review again; the propose run ends on `approve`; task 0.1 of the delivery tasks is the apply gate); delete `rules.architect-review`; no `operations` key. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q -k "review_finding or rework_verdict"` green
- [ ] 2.2 `git rm -r openspec/schemas` (five files). Verify `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` exits 0 with no `Unknown artifact ID` warning, `npx -y @fission-ai/openspec@1.13.0 status --change v2-1e-unfork-schema` still resolves (schema `spec-driven`), and `python -m pytest tests/publisher/test_planning_workflow.py -q` is green
- [ ] 2.3 `agents/architect-reviewer.md`: description and step 1 — read the `Architect review` entry of `rules.tasks` in `openspec/config.yaml` (contract and file structure) and the four artifacts of `openspec/changes/<change>/` in full; write only `openspec/changes/<change>/architect-review.md`; no `openspec` command, no `--store`. Verify `python -m pytest tests/publisher -q` green; commit `feat(v2-1e): architect review as a rule of spec-driven`

## 3. Documentation follows

- [ ] 3.1 `.agent-process/docs/architecture/agent-process.md` Planning section: `spec-driven` schema, the review as the last step of the propose run by the `tasks` rule (no `openspec/schemas/`, no `architect-review` rule); `.claude/rules/workflow.md`: the subagent writes `architect-review.md` (not "the artifact"); `AGENTS.md` lines 25–26: the review is written as `architect-review.md` as a self-review in Codex; `.agents/orchestration/roles.yaml`: line 22 comment names the `tasks` rule of `openspec/config.yaml`, line 66 `planner.completion_evidence` reads "Every artifact of the `spec-driven` schema and `architect-review.md` exist and `openspec validate --strict` passes"; ADR 0027 observation: the fork is rejected because `openspec schema` is experimental in 1.13.0 and a fork cannot follow upstream — the same gate is a `tasks` rule and the first delivery task. Verify `python -m pytest tests/agent_process/test_doc_narrative.py tests/agent_process/test_agent_orchestrator.py -q` green; commit `docs(v2-1e): planning on spec-driven`

## 4. Verify

- [ ] 4.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py` exit 0

## 5. Deliver

- [ ] 5.1 `git status --short` empty (commit what is left) → `python .agent-process/scripts/archive_change.py v2-1e-unfork-schema` exits 0: the archive commit (this directory, `architect-review.md` included, under `openspec/changes/archive/`) is pushed and is the head the PR opens on
- [ ] 5.2 `gh pr create --title "v2-1e-unfork-schema" --body-file <report>` — the report names the tracking issue as a plain reference (#126, no `Closes`), Why / What, the scenario → test map below, the deferred scope of the issue; ends with the Claude Code footer
- [ ] 5.3 `python .agent-process/scripts/request_codex_review.py --request <PR>` (v1, until v2-4; re-run after every push)
- [ ] 5.4 `python .agent-process/scripts/wait_for_pr.py <PR>`; apply every unresolved thread, push, re-request, at most three rounds; the fourth leaves the rest to the person with a reply. The person merges. No tick after 5.1 (the PR is the record); a run interrupted here resumes with `gh pr view v2-1e-unfork-schema`

## Scenario → test map

- roles / Procedure changes once → `tests/publisher/test_planning_workflow.py::test_roles_and_carriers`
- roles / Codex plans a change → n/a: a Codex run; the carrier text is asserted by `test_roles_and_carriers` (`self-review` in the `tasks` rule)
- planning / Review finding → `tests/publisher/test_planning_workflow.py::test_review_finding`
- planning / Rework verdict → `tests/publisher/test_planning_workflow.py::test_rework_verdict`
- planning / Review archives with the change → `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change`
