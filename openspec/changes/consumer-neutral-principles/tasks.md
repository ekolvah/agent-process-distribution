## 0. Delivery start

- [x] 0.1 Run `agent-process start_change consumer-neutral-principles --planner Claude --implementer Claude` for tracking issue 431. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/consumer-neutral-principles`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 no RED: docs-only (`skip_specs`), principle prose under the `principles.md` §I documentation exception

## 2. Consumer-neutral principles

- [x] 2.1 In `skills/agent-process/principles.md`, apply the design's planned wording to §III, §IV and §VI, keeping their headings. Verify that `grep -nE "ruff|selector|macro|scheduled production|news" skills/agent-process/principles.md` prints nothing. Commit as `docs(principles): state §III, §IV and §VI for any consumer`

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change consumer-neutral-principles`, then `gh pr create --title "docs: consumer-neutral-principles" --body-file <report>`. The report names tracking issue 431 as a plain reference, never `Closes`, names the principles the change interacts with (§III, §IV, §VI; Governance MINOR per design D3) and carries the scenario-to-test map
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- No delta scenarios (`skip_specs: true`): the change edits principle prose only.
