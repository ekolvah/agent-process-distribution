## 0. Delivery start

- [x] 0.1 Run `agent-process start_change add-readme --planner Claude --implementer Claude` (tracking issue 450), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: docs-only, `skip_specs`

## 2. README

- [x] 2.1 Add `LICENSE` with the standard MIT text (2026, `ekolvah`); write `README.md` per design D1–D3 and `git add` both; verify it is under 100 lines, its three install steps equal the `plugin-channel` row of `skills/agent-process/scripts/manual.py`, and `python -m pytest tests/agent_process/test_doc_links.py` passes
- [x] 2.2 Commit the group with its ticks as `docs: add a README`

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change add-readme`, then `gh pr create --title "docs: add-readme" --body-file <report>`; the report names the tracking issue as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (§VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure
- [ ] 4.3 After merge, run `gh repo edit --description "<the README's description>"` (design D3); verify `gh repo view --json description` returns it

## Scenario → test map

- n/a: `skip_specs` — docs-only, no delta scenario.
