## 1. Review

- [ ] 1.1 Review job in the reusable workflow (`claude-code-action`, reviewer instructions with the simplicity triggers); Codex app configured on this repository
- [ ] 1.2 Remove `request_codex_review.py`, `review_gate.py`, `install_branch_protection.py`, `resolve_review_thread.py`, `agent_review_outcome.py` and their tests
- [ ] 1.3 Tests named after `Blocking finding`, `Deferred finding`, `Thread after completion`, `Agent attempts merge`, `Reinvented helper`, `Reviewer unavailable`

## 2. State

- [ ] 2.1 Wire `set_status` into `implement-change`; remove `bootstrap_github_project.py`, `project_settings.py`, `set_issue_priority.py`
- [ ] 2.2 Tests named after `Resuming work`, `Merge`, `New project`, `Person checks progress`, `init without a Project`

## 3. Verify

- [ ] 3.1 On a real PR: both reviewers comment on open, a thread blocks via the ruleset, cycle time from In progress to mergeable has no human step (`PR opened`)
- [ ] 3.2 `openspec archive v2-4-review-and-state` as the last commit of the PR
