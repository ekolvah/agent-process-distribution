## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py release-drift-check --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 190. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 `tests/publisher/test_init.py`: add `test_config_block_records_release` — a confirmed run into a fresh repository and the rerender of `test_rerender_replaces_only_owned_content` both leave `# agent-process release: <init.VERSION>` inside the block
- [x] 1.2 `tests/publisher/test_delivery_scripts.py`: `_change` writes `openspec/config.yaml` with `init.render_config_block("t")`. Add `test_release_drift`, parametrized over both scripts × recorded release (no block, block without the line, `abc`, older, newer than `VERSION`, a config with mixed line endings): `main` exits 2, stderr names both releases and the direction's fix (`re-run Install` / `/plugin marketplace update`), and the fake `gh` recorded no call; one more case per script with a `rework` review and an older release asserts the drift message, not the verdict, is printed (design: Placement). Add `test_publisher_checkout_is_exempt`: `release_drift(root, root / "skills/agent-process/scripts")` is `None` for a config without a release, and `release_drift(root, root / "scratch/skills/agent-process/scripts")` is a message
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py` with every test of 1.1–1.2 (a `release_drift` stub returning `None`, so failures land in the test bodies), verify all RED, commit as `test(distribution): delivery entry scripts refuse release drift (RED)`

## 2. Release line and check

- [ ] 2.1 `templates/config.yaml` gains `# agent-process release: ${version}` after the pin line; `init.py` gains `RELEASE`, renders it from `VERSION` in `render_config_block`, and gains `release_drift` (design: One module owns the line; Comparison and messages; Exemption by path). Verify `python -m pytest tests/publisher/test_init.py -q` is green
- [ ] 2.2 `start_change.py` and `create_tracking_issue.py` call `release_drift(root, SCRIPT_DIR)` first and return 2 with its message (design: Placement); the module docstrings name the exit. Verify `python -m pytest tests/publisher -q` is green, commit Group 2 as `feat(distribution): delivery entry scripts refuse release drift`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py release-drift-check`. Verify that it applies the `distribution` delta, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "release-drift-check" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`), carries the scenario → test map, and names the accepted gap (scripts after Group 0 stay unchecked)
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution / Release recorded` → `tests/publisher/test_init.py::test_config_block_records_release`
- `distribution / Release drift` → `tests/publisher/test_delivery_scripts.py::test_release_drift`
- `distribution / Publisher checkout` → `tests/publisher/test_delivery_scripts.py::test_publisher_checkout_is_exempt`
