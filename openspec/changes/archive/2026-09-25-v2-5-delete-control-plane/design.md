## Context

See proposal.md (Why) for the caller search and the observations. After this change the
process is described in three places, each with one question: `openspec/specs/` (what it does),
`skills/agent-process/SKILL.md`, reached through the `rules` of `openspec/config.yaml` (how to
plan and deliver), and `.agent-process/docs/architecture/principles.md` (goal function,
principles §I–VII, quality gates). ADRs keep the why.

## Goals / Non-Goals

**Goals:** no v1 process document or control-plane file remains; every pointer to one resolves
to a v2 home or is gone.

**Non-Goals:** the Codex self-review artifact and the `wait_for_pr`-only guard, which ADR 0027
also ties to stable Codex subagents (D3); `copier-answers.yml` and the telemetry attribution test
that reads it (step 6); the `## Quality Gates` text of `principles.md`, which this change does not
reach; the historical comment of `navigation_policy.py` that names the old orchestrator test as
the size driver of an incident.

## Decisions

**D1. The advisory control plane is deleted: `agent_orchestrator.py`, `roles.yaml`,
`state.example.json`, `test_agent_orchestrator.py`.**
- It printed advice and authorized nothing (`AGENTS.md`: "It never authorizes bypassing its
  required delivery gates"). No proof is lost. What it described has a v2 home that is already
  enforced: roles and carriers in `openspec/specs/roles/`; the bound of three review rounds in
  `SKILL.md` §Delivery and `implementation / Delivery steps are tasks of every change`; route
  selection is the person's (`roles / Route selection is the person's`).
- `AGENTS.md` loses its advisory-control-plane bullet.
- Alternative: keep `roles.yaml` as a machine-readable role list. Rejected: a second home for
  roles is what drifted (PR 124 review), and nothing reads it.

**D2. `agent-process.md` and `agent-process-installation.md` are deleted; nothing moves.**
- Pointers are retargeted, not rewritten:
  - `AGENTS.md`: the source-of-truth sentence names `openspec/specs/` and
    `skills/agent-process/SKILL.md`; the delivery-flow link goes to `SKILL.md` §Delivery.
  - `.claude/rules/workflow.md`: the enforced contract is `openspec/specs/`, the procedure is
    the skill; the planning and delivery links go to `SKILL.md` §Architect review and
    `SKILL.md` §Delivery.
  - `.claude/rules/mindset.md`: the "Procedure" pointer goes to `SKILL.md`.
  - `.claude/rules/testing.md`: the RED contract link goes to `SKILL.md` §Tasks.
  - `openspec/config.yaml` `context`: the sentence "until they archive, the enforced process is
    v1 (`.agent-process/docs/architecture/`)" names `openspec/specs/` and the skill instead; every
    propose and apply run reads it.
  - `principles.md`: its six links to "the agent process" go to `SKILL.md` (the architect-review
    link to `SKILL.md` §Architect review); the header and §Governance drop "the other
    architecture docs" and name the skill and `openspec/specs/` as the home of the delegated
    procedure.
  - The link guard does not see folder-level mentions; task 3.1 greps for them.
  - `hooks.py`: the `pip-compile` reminder drops its pointer; the message states the rule itself.
  - ADR 0003, 0004, 0009: the link becomes plain text naming the removed section and ADR 0027,
    as `v2-1c` did in ADR 0009. The link guard reads every tracked `.md`, ADRs included.
- Content that has no v2 home, and what catches its absence:
  - Test-suite ownership (publisher vs consumer): v2 drops the split (Q&A MAINT-4); the
    directories stay and `pytest` collects both.
  - Type labels and the trivial-change skip: no script or check ever read them; dropped.
  - `pip-compile` in the same commit: the `requirements` step of `ci_check` fails on lockfile
    drift, and the `hooks.py` reminder stays.
  - The caller-workflow trust boundary text is dropped (PR 178 review): one person commits,
    the revisit condition of ADR 0004. The boundary itself stays tested by
    `test_quality_executes_a_trusted_driver_against_the_pr_worktree`,
    `test_callees_declare_workflow_call_without_pull_request_trigger` and
    `test_caller_permissions_are_a_superset_of_callee_permissions`.
  - The review-credential preflight `check_review_credentials.py`, read only by the installation
    guide: a repository without `CLAUDE_CODE_OAUTH_TOKEN` gets a red `agent-review` check on the
    first PR head that Codex does not review (`reusable-agent-review.yml`, comment beside the
    secret). Deleted with its test.
  - `.github/pull_request_template.md`: `gh pr create --body-file` does not use it, its
    `Closes #` contradicts `implementation / Delivery steps are tasks of every change`, and its
    Route and invocation fields are orchestrator output (D1). Deleted.
- Alternative: keep a short `agent-process.md` as an index. Rejected: an index is a fourth place
  that must track the other three, the drift that step 5 removes.

**D3. Codex hooks stay.**
- Observation: `codex features list` on `codex-cli 0.153.4` (2026-09-25) prints
  `hooks  stable  true` and `multi_agent  stable  true`. ADR 0027's deletion condition restores
  hooks once they are stable, so deleting `codex_hooks.py` now would be followed by restoring it.
  The person chose to keep them (2026-09-25).
- Kept unchanged: `codex_hooks.py`, `.codex/hooks.json`, `agent_policy.py`,
  `check_codex_project_trust.py` and their tests. The trust preflight's instruction lived in the
  installation guide; it becomes one line in the Codex adapter section of `AGENTS.md`, which is
  where this repository's Codex setup lives (consumers do not receive `.agent-process/scripts`).
- The rest of that deletion condition (the Codex self-review artifact, the `wait_for_pr`-only
  guard) is not in this change: it changes `roles` and `implementation` requirements and needs its
  own observation of Codex subagents. ADR 0027 records it as open.

**D4. The size budget is enforced only by a standard tool.**
- Open question of issue 115, settled. The script half is already the requirement
  `implementation / ci_check limits code complexity` (pylint `max-module-lines = 1000`).
- The workflow half (150 lines) gets no check. No standard linter bounds a workflow's length,
  the largest workflow is 125 lines, and a check of our own without an observed problem is the
  bespoke this step removes. The planned requirement and its test were dropped in PR 178
  review; ADR 0027 records the answer.

**D5. ADR 0027 gets one Observations block for step 5:** the D3 observation and the open rest of
its deletion condition; the D4 answer; the second open question of issue 115 (compare review
rounds via telemetry) moves to step 6 (issue 116), which provides the telemetry.

## Risks / Trade-offs

- [A reader follows a v1 link from outside the repository] → the link 404s; the v2 homes are
  named in `AGENTS.md`, the first file an agent reads.
- [A second committer joins] → ADR 0004's revisit condition brings the trust anchor back.
- [A consumer lacks the review secret] → caught by the red `agent-review` check, not ahead of
  time (D2).
- Rollback: `git revert` of the PR. No external state changes.
