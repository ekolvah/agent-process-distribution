## 1. Plugin and Codex

- [ ] 1.1 `.claude-plugin/plugin.json` + `marketplace.json`; skills, `agents/architect-reviewer.md`, `rules/principles.md`, `settings.json` deny-list
- [ ] 1.2 Hooks: PostToolUse lint, PreToolUse navigation, Stop (open PR with pending checks or unresolved threads)
- [ ] 1.3 Codex: document the checkout link `$CODEX_HOME/skills/<skill>/`
- [ ] 1.4 Tests named after `One skill directory serves both agents`, `Lint error`, `Clean PR`, `Session start`, `Force push`

## 2. Workflows and ruleset

- [ ] 2.1 `.github/workflows/agent-process.yml` reusable: checkout this repository at the pinned tag, run the consumer's `ci_check`
- [ ] 2.2 `ruleset.json`: required checks, conversation resolution, PR required, no direct push
- [ ] 2.3 Tests named after `CI run`, `Push`, `Direct push`, `Breaking change`

## 3. init

- [ ] 3.1 `/agent-process:init`: workflow caller, `AGENTS.md` append, pre-push hook, ruleset apply, repository variable, `openspec init --tools claude,codex` + this process's `config.yaml` and schema
- [ ] 3.2 Tests named after `Fresh repository`, `Re-running init on an established repository`, `Consumer-specific value survives update`, `Update is a native command`

## 4. Delete the mirror

- [ ] 4.1 Remove `template/`, `copier.yml`, `template_drift.py`, `adopt_agent_process.py`, `template-drift-allowlist.yml`, `tests/publisher/test_template_drift.py`, `test_existing_project_*`
- [ ] 4.2 Test named after `Repository inventory`; this repository installs its plugin from the local marketplace (`Process change`)
- [ ] 4.3 Verify: `init` on an empty repository in ≤ 10 minutes; `openspec archive v2-2-delivery` as the last commit of the PR
