## 0. Delivery start

- [x] 0.1 Run `agent-process start_change issue-refs-only-in-history --planner Claude --implementer Claude` for tracking issue 353. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/issue-refs-only-in-history`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `tests/agent_process/test_issue_refs.py`: a helper loads the hook with id `no-issue-refs` from the repository's `.pre-commit-config.yaml` (asserting it exists, in the test body), writes it as the only hook of a `.pre-commit-config.yaml` in a temporary git repository with the given files, stages them and runs `python -m pre_commit run --all-files`, returning exit code and output (`encoding="utf-8"`). Offending literals are built through f-strings (`f"(issue {349})"`), so this file carries none (design D4)
- [x] 1.2 `test_issue_reference_outside_history`: one file each, at real repository paths (`skills/agent-process/scripts/x.py`, `.github/workflows/x.yml`, `.claude/rules/x.md`, `tests/x.py` and more under them), with a comment `(issue N)`, a docstring `(#N)`, a reference wrapped across lines in prose and in a `#` comment, `PR N`, `pull request N`, `issue #N` → exit 1 and every file named in the output (design D2)
- [x] 1.3 `test_history_record_keeps_its_references`: `.agent-process/docs/adr/0001-x.md`, `CHANGELOG.md` and `openspec/changes/x/proposal.md` carrying `#N` and `issue N`, plus a file with `&#123;`, `pull/5#x`, `#doc-guards`, `C#1` and `#<N>` → exit 0
- [x] 1.4 Run `agent-process check_red tests/agent_process/test_issue_refs.py`. Verify that it prints `RED: 2 failed` and exits 0, each failing in its body (no hook `no-issue-refs`). Commit with the Group 1 ticks as `test(maintenance): issue references only in history records`

## 2. Rule and hook

- [x] 2.1 In `.pre-commit-config.yaml`, add under `repo: local` the hook `no-issue-refs` exactly as design D1 declares it, with the name `issue or PR reference outside history records (ADR, CHANGELOG.md, openspec/changes)` (design D3). Verify that `python -m pytest tests/agent_process/test_issue_refs.py -q` passes
- [x] 2.2 Remove `tests/agent_process/test_doc_narrative.py` (design D2). Verify that `python -m pytest tests/agent_process -q` passes. Commit 2.1–2.2 as `feat(maintenance): issue references only in history records`

## 3. Remove the existing references

- [x] 3.1 In the non-test files of the proposal's Impact list, remove each issue or PR reference, rewriting the sentence so it states the current state, or dropping it when it only records history. In `CLAUDE.md` and `openspec/config.yaml`, drop the pointers to the closed tracking issue and the v2 delivery sentence they carry; in `skills/agent-process/scripts/start_change.py` write the example token as `tracking issue <N>`
- [x] 3.2 In the test files of the Impact list, do the same for comments and docstrings; build fixture numbers from a named constant (`tracking issue 7` in `test_start_change.py`, `#4 Board` / `#5 Other` in `test_set_status.py`) (design D4)
- [x] 3.3 Run `python -m pre_commit run no-issue-refs --all-files` and verify that it passes; run `python -m pytest -q` and verify that it passes. Commit 3.1–3.3 as `refactor: remove issue references outside history records`

## 4. Verify

- [ ] 4.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `agent-process archive_change issue-refs-only-in-history`. Verify that it archives the delta into `openspec/specs/maintenance/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: issue-refs-only-in-history" --body-file <report>`. The report references the tracking issue plainly (#353), never with `Closes`, and carries the scenario → test map
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `maintenance` / Narrative issue reference → `tests/agent_process/test_issue_refs.py::test_issue_reference_outside_history`
- `maintenance` / History record keeps its references → `tests/agent_process/test_issue_refs.py::test_history_record_keeps_its_references`
