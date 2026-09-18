## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/fix-rerun-fallback-head/architect-review.md` exits 0 and `gh issue view 139 --json projectItems` shows the tracking issue in "Planned"; otherwise print `propose run not finished: run its tail (the Architect review entry of this rule) first` and stop
- [x] 0.2 Branch: `gh issue develop -c 139 --name fix-rerun-fallback-head` from fresh `origin/main`; `git branch --show-current` prints it
- [x] 0.3 Status: `python .agent-process/scripts/set_status.py 139 "In Progress"`
- [x] 0.4 Provenance: `gh issue comment 139 --body "planner: Claude; implementer: <this carrier>"`

## 1. RED first

- [x] 1.1 Write the tests of the scenario → test map below — `tests/publisher/test_request_codex_review.py::test_wait_is_present_for_either_trusted_reviewer_on_the_head` (`reviewed()` with the Codex login and `github-actions`: true on a fallback review of the head, false on one of an older head), `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads` (the wait step names both `--reviewer` values; the verify step `github-actions` alone), `tests/publisher/test_resolve_review_thread.py::test_close_round_names_the_rerun_and_the_reply_when_the_rerun_fails` and `::test_close_round_names_the_reply_alone_when_the_reply_fails` (the error after a successful resolve carries only what is still undone, ids filled in) —, run the test runner `AGENTS.md` declares, `python .agent-process/scripts/check_red.py --report <report path> <node ids>` exits 0, commit before any implementation

## 2. The wait reads presence for either trusted reviewer (D1)

- [x] 2.1 `request_codex_review.py`: `--reviewer` repeatable with default `None` resolved to the Codex login after parsing (never an `append` onto a non-empty default), `reviewed()` and `wait_for_review()` over the logins, the `present`/`absent` line names them; `python -m pytest tests/publisher/test_request_codex_review.py -q` green, `::test_wait_for_another_reviewer_reads_its_clean_comment_naming_the_head` among them (a Codex review present and `--reviewer github-actions` alone still exits 3)
- [x] 2.2 `reusable-agent-review.yml`, step *Wait for the Codex review of the head*: `--reviewer chatgpt-codex-connector --reviewer github-actions`, the step's comment says why; `python -m pytest tests/publisher/test_reusable_workflows.py -q` green

## 3. A failure after the resolve names the recovery (D3)

- [x] 3.1 `resolve_review_thread.py`, `close_round`: the rerun and the reply each under `try`; a failed rerun re-raises with `gh run rerun <run-id>` and the reply call (comment id filled in), a failed reply with the reply call alone; `python -m pytest tests/publisher/test_resolve_review_thread.py -q` green
- [x] 3.2 ADR 0027: the decision D2 (no observation before the fix; the fallback and the verify step still unobserved live under the merged callee) and a new placeholder in the form of the one it will fill — `<confirmed on the first fallback head re-run after the merge: run id, wait duration, second review yes/no>` — so the next planner finds it unfilled as this change found `<observed on the next PR>`; that one is filled in 5.3, it needs a run of this PR

## 4. Verify

- [x] 4.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict fix-rerun-fallback-head` valid; `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py` green, or red on the untracked `v2-2-delivery` alone — a change of another session, reported as its own and left where it is (nothing outside `fix-rerun-fallback-head/` is moved, stashed or committed); `git status --short` shows nothing of this change uncommitted

## 5. Deliver

- [x] 5.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py fix-rerun-fallback-head` (marks its own task, archives, commits, pushes)
- [x] 5.2 `gh pr create --title "fix-rerun-fallback-head" --body-file <report>` — the change name, issue 139 as a plain reference, the scenario → test map, the deferral: the callee fix is confirmed on the first fallback head re-run after the merge; the fill of `<observed on the next PR>` named as pending until the first run
- [x] 5.3 `python .agent-process/scripts/request_codex_review.py --request <PR>` → `python .agent-process/scripts/wait_for_pr.py <PR>` → on the first head alone: `gh run view <run-id> --json jobs` of that `pull_request` run fills `<observed on the next PR>` in ADR 0027 (wait → the Codex review → enforce on one path), commit, push, `--request` again, `wait_for_pr.py` again → a `P0`/`P1` thread the push addressed: `python .agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`; a `P2`/`P3` thread is answered; a fix that changes a spec goes through a change of its own on the branch; at most three rounds, the fourth leaves the rest to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view fix-rerun-fallback-head`

## Scenario → test map

- review-and-merge / Re-run on a fallback head → `tests/publisher/test_request_codex_review.py::test_wait_is_present_for_either_trusted_reviewer_on_the_head` (the read) and `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads` (the wait step names both logins, the Claude step's condition is absence alone); the attempt itself → n/a: the callee is exercised by the PR after the merge (the caller pins `@main`) — confirmed on the first fallback head re-run after it and recorded in ADR 0027 (D2)
- review-and-merge / Valid Codex review, Stale Codex review, Codex review absent, Reader failure → `tests/publisher/test_request_codex_review.py::test_wait_is_present_for_a_native_review_on_the_head`, `::test_wait_polls_to_the_timeout_for_a_review_of_an_older_head`, `::test_wait_is_present_for_the_clean_comment_naming_the_head`, `::test_wait_ignores_a_limit_message_and_a_stranger_naming_the_head` (existing); the fallback and the verify step → `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads` (existing)
- review-and-merge / Head from a fork → n/a: the platform's secret rule and the repository's approval setting, not code of the process (ADR 0027)
- review-and-merge / Event other than a push → `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads` (existing: no `if` on the wait, `always()` on the enforcement)
- D3 (no scenario: the order of the step is unchanged, `implementation` / Blocking thread addressed) → `tests/publisher/test_resolve_review_thread.py::test_close_round_names_the_rerun_and_the_reply_when_the_rerun_fails`, `::test_close_round_names_the_reply_alone_when_the_reply_fails`
