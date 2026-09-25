## Why

Issue #185. Observation (#117 step 7a, `ekolvah/agent-process-sandbox`): after a clean
`init --confirm` the consumer has no `.agent-process/` directory, as the `distribution`
requirement "The installed footprint is closed" demands, yet the package points into it:

- `agents/architect-reviewer.md` step 2 reads `.agent-process/docs/architecture/principles.md`;
  the package carries no copy, so the reviewer judges a consumer's plan against principles it
  cannot read (the sandbox run only worked from a manual clone of the tag).
- `skills/agent-process/SKILL.md` Install step 4 tells each clone to run
  `git config core.hooksPath .agent-process/.githooks`; the installer creates no such path,
  and `test_package_contents_are_closed` forbids a hook in the package.

Root cause: the principles file stayed in the publisher-only root when the procedure moved
into the skill, and no test checks that a path the package names resolves in a consumer.

## What Changes

- Move `.agent-process/docs/architecture/principles.md` to `skills/agent-process/principles.md`
  (one copy, publisher and consumer read the same file); its links become package-relative,
  and the link to the publisher-only `REVIEW_CONTRACT.md` is dropped from §VII.
- `agents/architect-reviewer.md` reads `SKILL.md`, the schema and `principles.md` from the
  repository's `skills/agent-process/` when present, otherwise from
  `${CLAUDE_PLUGIN_ROOT}/skills/agent-process/` (design D2).
- The doc guards' scope follows the move (design D5).
- Install step 4 loses the pre-push hook sentence: the package ships no hook; the consumer's
  `agent-process / quality` check remains the gate.
- A publisher test fails when a package file names a `.agent-process/` path, a skill file's
  relative link leaves the skill directory, or an agent names a package file without
  `${CLAUDE_PLUGIN_ROOT}`.
- This repository's live links to the old principles path follow the move.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: adds "Package paths resolve in a consumer".
- `maintenance`: "Documents are guarded" names the principles' new location.

## Impact

- Moved: `.agent-process/docs/architecture/principles.md` → `skills/agent-process/principles.md`.
- Edited: `agents/architect-reviewer.md`, `skills/agent-process/SKILL.md`, `AGENTS.md`,
  `openspec/config.yaml`, `.claude/rules/mindset.md`, `.claude/rules/testing.md`,
  `.agent-process/docs/adr/0011-agentic-process-distribution-mechanism.md`,
  `.agent-process/docs/adr/0021-the-end-of-an-agent-turn-is-a-gated-event.md`,
  `tests/publisher/test_plugin.py`, `tests/publisher/test_reusable_workflows.py`,
  `tests/agent_process/test_doc_links.py`, `tests/agent_process/test_doc_narrative.py`,
  `tests/agent_process/test_doc_headers.py`.
- Added: the change directory with `specs/distribution/spec.md` and `specs/maintenance/spec.md`.
- Unchanged: archived changes and ADR prose that names `principles.md` without a link.
