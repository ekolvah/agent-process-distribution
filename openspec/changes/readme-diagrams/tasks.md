## 0. Delivery start

- [x] 0.1 Run `agent-process start_change readme-diagrams --planner Claude --implementer Claude` (tracking issue 453), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: docs-only, `skip_specs`

## 2. Diagrams

- [x] 2.1 Add the architecture diagram under "What it is" and replace its bullets with one sentence (design D1, D3)
- [x] 2.2 Add the process diagram under "Usage" and drop the Why table's status clause (design D2, D3); verify each diagram is at most 14 lines, `wc -l README.md` prints under 100 and `python -m pytest tests/agent_process/test_doc_links.py` passes
- [x] 2.3 Commit the group with its ticks as `docs: add architecture and process diagrams to the README`

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change readme-diagrams`, then `gh pr create --title "docs: readme-diagrams" --body-file <report>`; the report names the tracking issue as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (§VII), and asks the owner to confirm both diagrams render on the PR's README before approving (design Risks)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- n/a: `skip_specs` — docs-only, no delta scenario.
