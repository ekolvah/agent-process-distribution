## 0. Delivery

- [ ] 0.1 Tracking issue for this change (ask the person for the priority, set the Project field); `gh issue develop -c <N>`; `set_status <N> "In progress"`

## 1. Delete

- [ ] 1.1 Remove `agent_orchestrator.py`, `delivery_state.py`, `roles.yaml`, `codex_hooks.py`, `.codex/hooks.json`, `max_runs` handling and their tests
- [ ] 1.2 Reduce `.agent-process/docs/architecture/` to `principles.md`; README points to the plugin, skills and `openspec/specs/`
- [ ] 1.3 Tests named after `Looping agent`, `First failure`, `Non-Python consumer`, `Budget exceeded`, `New prohibition`, `Internal refactor`

## 2. Verify

- [ ] 2.1 Core scripts ≤ 1 000 lines, workflows ≤ 150 lines; `test_doc_links` green

## 3. Deliver

- [ ] 3.1 `ci_check` green; open the PR (body: change name, tracked deferrals as issue links)
- [ ] 3.2 `wait_for_pr`; apply every unresolved thread or reply on the one left to the person; repeat until nothing is unresolved
- [ ] 3.3 `finish_change v2-5-delete-control-plane` — marks this task, `openspec archive v2-5-delete-control-plane -y`, commit, push, `wait_for_pr` on that head
