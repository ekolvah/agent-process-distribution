## Why

Step 5 of issue 107 (issue 115). Planning, delivery, review and state are carried by OpenSpec,
the `agent-process` skill, GitHub and the review apps (steps 1–4), so the v1 control plane and
the v1 process documents have no consumer left. While they exist, roles live in three places
(the table of `agent-process.md`, `roles.yaml`, `openspec/specs/roles/`), and they drifted apart
(PR 124 review).

Observed on `main` at `9432f10` (2026-09-25), with archived changes and ADRs excluded:

- `agent_orchestrator.py` is read only by its test, by `AGENTS.md` and by `agent-process.md`;
  `roles.yaml` and `state.example.json` only by the orchestrator and its test.
- `delivery_state.py` no longer exists (deleted in `v2-4a`); `max_runs` occurs only in the
  orchestrator, `roles.yaml` and their test.
- `agent-process-installation.md` is the only reader of `check_review_credentials.py`; install
  is `skills/agent-process/SKILL.md#install`.
- `.github/pull_request_template.md` asks for `Closes #` and for the orchestrator's route and
  invocation counts. The PR body comes from `gh pr create --body-file <report>`, which names the
  issue as a plain reference (`implementation / Delivery steps are tasks of every change`).
- `codex features list` on `codex-cli 0.153.4` prints `hooks  stable  true` and
  `multi_agent  stable  true`. The brief removes `codex_hooks`, but ADR 0027's deletion condition
  says hooks are *restored* once Codex ships them stable. The person decided on 2026-09-25 to keep
  the Codex hooks (design D3).
- The size budget (v2 Q&A, MAINT-7: a script ≤ 1 000 lines, a workflow ≤ 150 lines) holds:
  the largest script is `skills/agent-process/scripts/init.py` (821 lines), the largest workflow
  `reusable-agent-review.yml` (125 lines). `ci_check` already fails a module over 1 000 lines;
  no check covers workflows.

## What Changes

- **BREAKING** (for anyone still following v1 documents): delete
  `.agent-process/docs/architecture/agent-process.md` and `agent-process-installation.md`;
  `.agent-process/docs/architecture/` holds `principles.md` only. Nothing of them moves into
  `principles.md`. Their pointers in `AGENTS.md`, `.claude/rules/*.md`, `principles.md`,
  `hooks.py` and three ADRs point to `openspec/specs/` and `skills/agent-process/SKILL.md`, or are
  removed.
- Delete the advisory control plane: `agent_orchestrator.py`, `.agents/orchestration/roles.yaml`,
  `state.example.json` and their test. `openspec/specs/roles/` is the only home of roles.
- Delete `check_review_credentials.py` and its test, and the PR template.
- `maintenance`: add the workflow size budget, guarded by a test; the script half is already
  `implementation / ci_check limits code complexity`.
- `openspec/config.yaml` `context` stops naming v1 as the enforced process.
- ADR 0027: one Observations block for this step (Codex hooks stable; the size-budget question
  settled).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `maintenance`: adds `Size budget` (workflows).

`implementation` (named in the brief) is unchanged: its only planned edit was the removal of
Codex hooks, which is not made (design D3).

## Impact

- Removed: `.agent-process/scripts/agent_orchestrator.py`,
  `.agent-process/scripts/check_review_credentials.py`, `.agents/orchestration/roles.yaml`,
  `.agents/orchestration/state.example.json`,
  `.agent-process/docs/architecture/agent-process.md`,
  `.agent-process/docs/architecture/agent-process-installation.md`,
  `.github/pull_request_template.md`, `tests/agent_process/test_agent_orchestrator.py`,
  `tests/agent_process/test_review_credentials.py`.
- Edited: `AGENTS.md`, `openspec/config.yaml` (one `context` sentence), `.claude/rules/workflow.md`, `.claude/rules/mindset.md`,
  `.claude/rules/testing.md`, `.agent-process/docs/architecture/principles.md` (header, six
  links, §Governance),
  `.agent-process/scripts/hooks.py` (one message string),
  `tests/publisher/test_reusable_workflows.py` (one test removed, one added), ADR 0003, 0004 and
  0009 (one link each, as ADR 0009 was edited in `v2-1c`), ADR 0027 (Observations).
- Unchanged: `codex_hooks.py`, `.codex/hooks.json`, `agent_policy.py`,
  `check_codex_project_trust.py` and their tests (design D3; the trust preflight's instruction
  moves from the installation guide to one line of `AGENTS.md`); `.agent-process/copier-answers.yml`,
  whose only reader is the telemetry attribution test (step 6, issue 116); `gh_io.py`, still
  imported by the review scripts.
