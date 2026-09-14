## 1. Delete

- [ ] 1.1 Remove `agent_orchestrator.py`, `delivery_state.py`, `roles.yaml`, `codex_hooks.py`, `.codex/hooks.json`, `max_runs` handling and their tests
- [ ] 1.2 Reduce `.agent-process/docs/architecture/` to `principles.md`; README points to the plugin, skills and `openspec/specs/`
- [ ] 1.3 Tests named after `Looping agent`, `First failure`, `Non-Python consumer`, `Budget exceeded`, `New prohibition`, `Internal refactor`

## 2. Verify

- [ ] 2.1 Core scripts ≤ 1 000 lines, workflows ≤ 150 lines; `test_doc_links` green
- [ ] 2.2 `openspec archive v2-5-delete-control-plane` after merge
