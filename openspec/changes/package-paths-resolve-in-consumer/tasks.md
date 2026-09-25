## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py package-paths-resolve-in-consumer --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 185. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `test_package_paths_resolve_in_a_consumer` to `tests/publisher/test_plugin.py` (design D4): over the text files of `skills/agent-process/`, `agents/`, `commands/`, collect each `.agent-process/` occurrence not preceded by `~/`, each relative Markdown link of a skill file whose target resolves outside the skill directory, and each `agents/*.md` that names `skills/agent-process/` without `${CLAUDE_PLUGIN_ROOT}/skills/agent-process/`; assert the lists empty, naming file and path. Add `principles.md` to the expected set of `test_package_contents_are_closed`. Run `python skills/agent-process/scripts/check_red.py "tests/publisher/test_plugin.py::test_package_paths_resolve_in_a_consumer" "tests/publisher/test_plugin.py::test_package_contents_are_closed"` and verify both fail (the reviewer's and the Install step's `.agent-process/` paths, the reviewer without `${CLAUDE_PLUGIN_ROOT}`; `principles.md` absent). Commit as `test(distribution): package paths resolve in a consumer`

## 2. Package

- [x] 2.1 `git mv .agent-process/docs/architecture/principles.md skills/agent-process/principles.md` (design D1); rewrite its `../../../skills/agent-process/SKILL.md` links to `SKILL.md` and drop the `[REVIEW_CONTRACT.md](../../REVIEW_CONTRACT.md)` parenthetical of §VII. Verify that `python -m pytest tests/publisher/test_plugin.py::test_package_contents_are_closed tests/publisher/test_reusable_workflows.py -q` is green after the path update of `test_review_contract_and_principles_stay_coupled_on_narrow_simplicity_triggers`
- [x] 2.2 Rewrite steps 1–2 of `agents/architect-reviewer.md` per design D2: read `SKILL.md`, `architect-review.schema.json` and `principles.md` from `skills/agent-process/` at the repository root when it exists, otherwise from `${CLAUDE_PLUGIN_ROOT}/skills/agent-process/`. Verify that `python -m pytest tests/publisher/test_planning_workflow.py -q` stays green
- [x] 2.3 Remove the pre-push hook sentence from Install step 4 of `skills/agent-process/SKILL.md` (design D3). Verify that `python -m pytest tests/publisher/test_plugin.py -q` is green, then commit Group 2 as `fix(distribution): ship principles in the skill, drop publisher-only paths`

## 3. Repository follows the move

- [ ] 3.1 Retarget this repository's live links to the old path: `AGENTS.md`, `openspec/config.yaml` context, `.claude/rules/mindset.md`, `.claude/rules/testing.md`, and the links of ADR 0011 and ADR 0021. Verify that `git grep -n "docs/architecture/principles" -- ':!openspec/changes/archive'` prints nothing
- [ ] 3.2 Move the doc-guard scope per design D5: `.agent-process/docs/architecture` → `skills/agent-process` in `_EXPECTED_SCOPE_DIRS` of `tests/agent_process/test_doc_links.py` and `tests/agent_process/test_doc_narrative.py`; in `tests/agent_process/test_doc_headers.py` replace the architecture directory with the file `skills/agent-process/principles.md` in the header scope and its non-vacuity check. Verify that `python -m pytest tests -q` is green, then commit Group 3 as `docs(maintenance): follow the principles move`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes; verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py package-paths-resolve-in-consumer`. Verify that it commits the archive and pushes the branch
- [ ] 5.2 Run `gh pr create --title "package-paths-resolve-in-consumer" --body-file <report>`. The report references tracking issue 185 without `Closes` and carries the scenario → test map
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`; answer P2/P3 without resolving. After the third reviewed head with an open P0/P1 thread, stop and escalate to the person
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, report the PR ready. The person merges it

## Scenario → test map

| Scenario | Test |
|---|---|
| distribution / Package paths resolve in a consumer / Publisher-only path in the package | `tests/publisher/test_plugin.py::test_package_paths_resolve_in_a_consumer` |
| maintenance / Documents are guarded / Narrative issue reference | `tests/agent_process/test_doc_narrative.py::TestDocsCarryNoNarrative::test_no_narrative_issue_ref` (existing; the requirement edit only moves the header scope, covered by `tests/agent_process/test_doc_headers.py::TestMappedDocsCarryHeader` per design D5) |
