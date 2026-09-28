## 0. Delivery start

- [x] 0.1 Run `agent-process start_change release-pr-line-bump --planner Claude --implementer Claude` for tracking issue 260. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/release-pr-line-bump`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 `tests/publisher/test_release_pr.py`: add `test_old_version_kept_elsewhere_is_a_release_pr`: base and head as `_texts("2.0.0")` and `_texts("2.1.0")` with `INIT` prefixed at both by the line `# rendered up to 2.0.0\n`; `release_verdict(CONFIG, CHANGES, base, head)` is `None`. Extend `test_other_change_in_a_version_file_is_not_a_release_pr` (D1 class: each non-version edit of `INIT`, the reason names `INIT`): a line appended, a line removed (`import sys\n` dropped), the final newline dropped, and a line changed together with its version bump (`VERSION = "2.1.0"  # x-release-please-version` → `VERSION = "2.1.0"  # edited`)
- [x] 1.2 Run `agent-process check_red tests/publisher/test_release_pr.py::test_old_version_kept_elsewhere_is_a_release_pr` and verify that it fails in its body (the extended test already passes and stays out: it guards the class through the fix). Commit as `test(review): release PR keeps an old version elsewhere`

## 2. Fix

- [ ] 2.1 `.agent-process/scripts/release_pr.py` (D1): `_beyond_the_version` compares `splitlines(keepends=True)` of base and head — the counts match and each head line equals its base line or that line with every bump applied — and keeps the reason `<path> changes more than the version`; the module docstring states the line rule. Verify `python -m pytest tests/publisher/test_release_pr.py -q` passes
- [ ] 2.2 `.agent-process/docs/adr/0031-release-prs-merge-without-the-person.md` D1: "equals its base with each `old → new` version replaced" becomes the line rule of D1; D3's "only version substitutions pass D1" becomes "D1 passes only lines unchanged or changed by the version; a version place left unbumped fails `test_version_drift`, which runs in `check` on the same head". Verify `python -m pytest tests/agent_process/test_doc_narrative.py tests/agent_process/test_adr_records.py tests/agent_process/test_doc_links.py -q` passes. Commit as `fix(review): release PR recognised line by line`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change release-pr-line-bump`. Verify that it archives the delta into `openspec/specs/review-and-merge/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: release-pr-line-bump" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#260), and carries the scenario → test map and the observation of proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `review-and-merge` / Release PR → `tests/publisher/test_release_pr.py::test_release_pr_is_recognised` (unchanged)
- `review-and-merge` / Old version kept elsewhere → `tests/publisher/test_release_pr.py::test_old_version_kept_elsewhere_is_a_release_pr`
- `review-and-merge` / Other change in a version file → `tests/publisher/test_release_pr.py::test_other_change_in_a_version_file_is_not_a_release_pr`
- `review-and-merge` / File outside the set → `tests/publisher/test_release_pr.py::test_file_outside_the_set_is_not_a_release_pr` (unchanged)
- `review-and-merge` / No release configuration → `tests/publisher/test_release_pr.py::test_no_release_configuration_means_no_release_pr` (unchanged)
- `review-and-merge` / Failed read → `tests/publisher/test_release_pr.py::test_failed_read_fails_the_check` (unchanged)
