## Why

PR #151 changed the shared procedure's package location and introduced a stateful installer in
one review, so package path/import regressions could not be isolated from version handoff,
filesystem, platform-link, Project, workflow, and protection failures. The replacement
sequence under parent #112 therefore starts with a package-only foundation whose behavior can
be proven before any installer or remote-write state exists.

## What Changes

- Publish one `agent-process` skill as the portable source of the proposal, specs, design,
  tasks, architect-review, and current delivery procedure for both Claude and Codex.
- Move exactly the seven portable planning/delivery scripts used by that procedure from
  `.agent-process/scripts/` into the shared skill, updating sibling imports, emitted recovery
  commands, and consumer-root resolution without changing their behavior.
- Replace the duplicated procedure bodies in `openspec/config.yaml` with short pointers to
  the shared skill while retaining repository-specific context.
- Expose and dogfood the shared skill through the Claude plugin/marketplace and publisher
  settings with one consistent `2.0.0` package identity.
- Update current adapter guidance, canonical procedure paths, and publisher tests to use the
  shared source while preserving the existing Codex request, fallback review, thread
  resolution, review gate, hooks, workflows, and protection behavior.
- Do not add `init`, installer templates, consumer/user-profile writes, Project operations,
  workflow landing, protection activation, advisory-review migration, or v1 deletion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `roles`: move the one shared procedure source from copied `openspec/config.yaml` rule
  bodies into the carrier-neutral `agent-process` skill while keeping OpenSpec entry points
  and role behavior unchanged.
- `distribution`: make this publisher expose and exercise the shared plugin/skill package
  source before a later change adds consumer installation.

## Impact

- Added: `skills/agent-process/SKILL.md` and `tests/publisher/test_plugin.py`.
- Moved: `.agent-process/scripts/archive_change.py`,
  `.agent-process/scripts/check_red.py`,
  `.agent-process/scripts/create_tracking_issue.py`,
  `.agent-process/scripts/resolve_review_thread.py`,
  `.agent-process/scripts/set_status.py`, `.agent-process/scripts/start_change.py`, and
  `.agent-process/scripts/wait_for_pr.py` to `skills/agent-process/scripts/`.
- Edited: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `.claude/settings.json`, `.claude/rules/testing.md`, `.claude/rules/workflow.md`,
  `AGENTS.md`, `agents/architect-reviewer.md`, `openspec/config.yaml`,
  `.agent-process/docs/architecture/agent-process.md`,
  `tests/publisher/test_delivery_scripts.py`,
  `tests/publisher/test_planning_workflow.py`, and
  `tests/publisher/test_resolve_review_thread.py`.
- Removed: only the seven moved paths under `.agent-process/scripts/`; no installer,
  template, v1 review, workflow, hook, protection, or control-plane file changes.
- External systems: no live GitHub, Project, consumer repository, user-profile, workflow, or
  protection mutation; issue/project metadata changes are the planning record only.
