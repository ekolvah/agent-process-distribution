## 0. Continue the active delivery

- [x] 0.1 Reuse tracking issue 112 and pull request 151 for this bounded review correction; do not run `start_change.py` because the issue branch and archived parent change already exist.

## 1. Prove the bootstrap contract RED

- [x] 1.1 Split the reusable-workflow reference test into consumer and publisher scenarios, require a local reference for the publisher, and prove the publisher node RED with `python skills/agent-process/scripts/check_red.py tests/publisher/test_reusable_workflows.py::test_publisher_caller_uses_local_reusable`.

## 2. Implement the bounded correction

- [x] 2.1 Change only the publisher caller to the repository-local reusable workflow while retaining its setup/test inputs; verify both reference tests GREEN.
- [x] 2.2 Amend the archived issue-112 design and scenario map with the bootstrap observation and accepted publisher-only trust boundary; verify the planning workflow tests GREEN.

## 3. Verify and archive

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py` GREEN.
- [x] 3.2 Verify a clean worktree, then run `python skills/agent-process/scripts/archive_change.py publisher-local-quality-bootstrap`.

## 4. Review the correction

- [ ] 4.1 After archive, request the transitional Codex review and run `python skills/agent-process/scripts/wait_for_pr.py 151` on the new settled head. Leave this box unchecked because ticking it would move the reviewed head; the PR is the evidence.

## Scenario → test map

| Capability | Scenario | Test evidence |
|---|---|---|
| distribution | Quality check on a PR | `tests/publisher/test_reusable_workflows.py::test_consumer_caller_pins_release_tag` |
| distribution | Quality check on the publisher PR | `tests/publisher/test_reusable_workflows.py::test_publisher_caller_uses_local_reusable` |
