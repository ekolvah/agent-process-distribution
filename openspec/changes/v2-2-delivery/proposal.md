## Why

Since `v2-0b` removed the Copier mirror, the process has no supported installation or
update path for a consumer repository. Step 2 of the v2 migration restores that path with
vendor-native distribution: one Claude plugin, one linked Codex skill, one thin workflow
caller, and one idempotent `init` command, after the standard-mechanism work of issues
129–132 has landed.

## What Changes

- Add an `agent-process` skill that is shared by the Claude plugin and Codex and carries
  the planning/delivery procedure plus the standalone delivery scripts. Replace the long
  artifact rules in `openspec/config.yaml` with pointers to that skill.
- Add `/agent-process:init` and the skill's matching install entry point. `init` runs
  OpenSpec 1.13.0 for Claude and Codex, writes only the process-owned configuration, links
  the user-level Codex skill from an updateable checkout, installs the repository ruleset,
  copies and links the template Project, and prints the remaining person-owned setup
  commands/checklist. A second run is idempotent and never overwrites unrelated content.
- Keep the consumer footprint closed: OpenSpec's generated files plus the process
  `config.yaml`, two `.claude/settings.json` keys, one
  `.github/workflows/agent-process.yml`, one Dependabot entry, and the ruleset/Project
  state on GitHub. Do not install hooks, an `AGENTS.md` fragment, a report-path convention,
  or process scripts into the repository.
- Replace the two local workflow callers and bespoke reusable review workflow with one
  caller. Quality invokes the pinned reusable quality workflow with caller-supplied
  `setup` and `test` commands and checks GitHub's PR→issue link; Claude review invokes
  `anthropics/claude-code-action@v1` directly. Codex automatic review is enabled by the
  person from the printed instruction; neither review is a required process check.
- Add a GitHub-native ruleset JSON that requires a PR and the head-bound quality context,
  and blocks deletion and non-fast-forward updates. Required status checks remain
  name-bound; the person reviews changes under `.github/workflows/**` because a
  repository ruleset cannot authenticate the caller file for a personal repository.
- Delete the obsolete Copier answer record and the attribution tests whose only input was
  that record. Version the plugin and marketplace together; callers pin the matching tag
  and Dependabot proposes tag updates.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: define the one-command install/update path, the closed consumer
  footprint, the shared skill, the pinned reusable quality workflow, and publisher
  dogfooding.
- `implementation`: run RED and delivery from the shared skill, use caller-declared
  quality commands, and remove distributed session-hook behaviour.
- `review-and-merge`: install a repository ruleset, make quality the required check, and
  use the official Claude and Codex review apps without a bespoke required review
  workflow.
- `maintenance`: couple release tags, plugin metadata, workflow pins, and Dependabot
  updates.

## Impact

Added:

- `skills/agent-process/SKILL.md`
- `skills/agent-process/scripts/init.py`
- `skills/agent-process/templates/{agent-process.yml,dependabot.yml,config.yaml,settings.json,ruleset.json}`
- `commands/init.md`
- `.github/workflows/agent-process.yml`
- `.github/dependabot.yml`
- `tests/publisher/test_plugin.py`
- `tests/publisher/test_init.py`

Moved into `skills/agent-process/scripts/` and edited for their new stable invocation
path: `archive_change.py`, `check_red.py`, `create_tracking_issue.py`,
`resolve_review_thread.py`, `set_status.py`, `start_change.py`, and `wait_for_pr.py`.

Edited:

- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.claude/settings.json`
- `openspec/config.yaml`
- `.github/workflows/reusable-quality.yml`
- `AGENTS.md`, `.claude/rules/testing.md`, `.claude/rules/workflow.md`
- `.agent-process/docs/architecture/agent-process.md`
- `.agent-process/docs/architecture/agent-process-installation.md`
- `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`
- `tests/publisher/test_delivery_scripts.py`, `tests/publisher/test_planning_workflow.py`,
  `tests/publisher/test_resolve_review_thread.py`,
  `tests/publisher/test_reusable_workflows.py`
- `tests/agent_process/test_ci_check.py`,
  `tests/agent_process/test_delivery_gate_wiring.py`

Removed:

- `.agent-process/copier-answers.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/agent-review.yml`
- `.github/workflows/reusable-agent-review.yml`

External systems affected by `init`: the repository ruleset, a copied and linked GitHub
Project, the repository secret named by the printed `gh secret set` command, the person's
Codex review-app setting, and the Project workflow switches named by the printed checklist.
No new package dependency is added; Node/OpenSpec, Python, `git`, and `gh` are existing
process prerequisites.

Out of scope: migrating the second consumer (issue 117), coverage enforcement (issue 113),
the remaining v1 review/state cleanup (issue 114), and deleting the rest of the v1 control
plane (issue 115).
