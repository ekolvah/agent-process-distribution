## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/v2-2b-fork-policy/architect-review.md` exits 0. The tracking issue is the one of the open PR this change is delivered on (issue 130, its second PR); it was closed by the merge of the first PR and is not in `Planned` — this change is the delta of a review fix of that PR (Deliver rule: a fix that changes a spec goes through a change of its own), so the propose-run gate on `Planned` does not apply: no issue is created, nothing is asked
- [x] 0.2 Branch: `git branch --show-current` prints `issue-130-review-events` — the branch of the PR; no `gh issue develop`
- [x] 0.3 No status move: the tracking issue is closed
- [x] 0.4 Provenance: the PR body names planner and implementer (Claude, both)

## 1. RED first

- [x] 1.1 `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads`: assert `claude["if"] == "steps.codex.outputs.absent == 'true'"` (the exact condition, no fork clause); `python .agent-process/scripts/check_red.py --report <report> <node id>` reports RED; committed as `c4f719c`

## 2. The guard goes, the ADR says why

- [x] 2.1 `reusable-agent-review.yml`, step `Claude review`: `if: steps.codex.outputs.absent == 'true'`; the comment names the platform rule (every secret but `GITHUB_TOKEN` withheld from a run of a fork PR on `pull_request_review` as on `pull_request`) and the repository setting; `python -m pytest tests/publisher/test_reusable_workflows.py -q` green
- [x] 2.2 ADR 0027, "Observations from v2-2b": the fork bullet replaced — the two Codex findings, the platform rule with its source (events reference; aws-actions/configure-aws-credentials issue 416 as the observation in the wild), the setting `all_external_contributors` and its API call, the deletion condition
- [x] 2.3 This change's delta for `review-and-merge`: the requirement text of `main` (no "head in the repository itself" clause), the scenario *Head from a fork* restated on the platform rule and the setting (a MODIFIED delta cannot drop a scenario in 1.13.0), the other scenarios unchanged; `npx -y @fission-ai/openspec@1.13.0 validate --strict v2-2b-fork-policy` valid

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` reports only the pre-existing failure of the untracked `v2-2-delivery` (a change of another issue, not of this PR) and `python .agent-process/scripts/ci_check.py` green with that directory set aside; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [x] 4.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py v2-2b-fork-policy` (marks its own task, archives — applying the delta to `openspec/specs/` —, commits, pushes)
- [ ] 4.2 The PR exists: `python .agent-process/scripts/update_pr_body.py 137 --body-file <report>` — the report names this change, the setting, and the scenario → test map below
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request 137` → `python .agent-process/scripts/wait_for_pr.py 137` → resolve the `P1` thread of `66a29e1` (the caller-YAML finding) with `python .agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr 137 --thread PRRT_kwDOUAa7yM6jfNyL`, reply after the resolve with the platform rule, its source and the setting. The three fixer rounds of the PR are spent; this round is the owner's decision (2026-09-17: enable the setting, remove the guard); anything further is left to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view 137`

## Scenario → test map

- review-and-merge / Valid Codex review, Stale Codex review, Codex review absent, Reader failure, Event other than a push → `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads` (task 1.1: the exact `if` of the Claude step; the other assertions existing)
- review-and-merge / Head from a fork → n/a: the outcome is the platform's secret rule and the repository's approval setting, not code of the process; ADR 0027 carries the source and the API call that set it
