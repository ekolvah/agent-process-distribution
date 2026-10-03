## 0. Delivery start

- [x] 0.1 Run `agent-process start_change skill-carries-harness-context --planner Claude --implementer Claude` for tracking issue 315. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/skill-carries-harness-context`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py`, add `test_skill_carries_principles_core_and_harness_tactics`. It checks the text of `SKILL.md` before `## Proposal` (spec *A consumer reads principles and tactics from the skill*):
  - it holds `## Principles` and `## Claude harness`;
  - `## Principles` holds the goal names `bug-fixing`, `token spend` and `user control`;
  - `## Principles` holds one relative link into `principles.md`, with that heading's anchor, for each `### I.` … `### VII.` heading of `principles.md`, with the anchors derived from that file;
  - `## Claude harness` holds `gh issue view` and `git branch --show-current`, and no `/compact`.
- [x] 1.2 In `tests/publisher/test_reusable_workflows.py` (spec *Instructions live in Claude Code channels*):
  - make `test_review_contract_is_a_file_not_an_agents_section_parser` read `ROOT / "CLAUDE.md"`;
  - add `test_agent_instructions_live_in_claude_code_channels`: `ROOT / "AGENTS.md"` does not exist; `.agent-process/REVIEW_CONTRACT.md` and the `prompt` of `reusable-agent-review.yml` each contain `CLAUDE.md` and `.claude/rules/`; neither contains `AGENTS.md`.
- [x] 1.3 Run `agent-process check_red` with the node ids of 1.1 and 1.2, quoted. Verify that each fails in its body (missing heading, `CLAUDE.md` absent, `AGENTS.md` present), and that the two files fail nowhere else. Commit as `test(roles): the skill carries principles and harness tactics`

## 2. Skill and repository instructions

- [x] 2.1 In `skills/agent-process/SKILL.md`, after the opening paragraph, add `## Principles` and `## Claude harness` per design D1 and D2.
  - Each section has one line per item.
  - `## Principles` ends with one line saying that `principles.md` decides.
  - Links into `principles.md` stay relative, as `test_plugin.py:106` requires.
  - Keep the whole addition at about 2 KB.
  - Name none of the tokens that `test_planning_workflow.py:285-299` keeps out of the procedure.

  Verify that `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py -q` passes. Commit as `feat(skill): carry the principles core and harness tactics`
- [x] 2.2 Run `git mv AGENTS.md CLAUDE.md` (D4). Add the two pointers of D3 to `CLAUDE.md`, then delete `.claude/rules/mindset.md`. Then make three text edits:
  - in `.agent-process/REVIEW_CONTRACT.md`, the policy source becomes "`CLAUDE.md`, `.claude/rules/` and the documents they link to", and its untrusted line names `CLAUDE.md`;
  - in the `reusable-agent-review.yml` prompt, write "Every CLAUDE.md, `.claude/rules/` file, README or doc";
  - drop the `AGENTS.md` mentions in `tests/publisher/openspec_cli.py:16` (point to `CLAUDE.md`), `tests/publisher/test_pr_delivery.py:215` (`CLAUDE.md:`) and the comment at `tests/publisher/test_planning_workflow.py:281`. Keep `"AGENTS.md"` in that test's absent-token list.

  Verify that `python -m pytest tests/publisher tests/agent_process/test_doc_links.py -q` passes. Commit as `refactor(roles): Claude Code instructions replace AGENTS.md`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes
- [ ] 3.3 Live check (Principle V): from the worktree, run `claude -p --plugin-dir <worktree> --disallowedTools "Read,Grep,Glob,Bash" "Invoke the agent-process skill and quote its '## Claude harness' section verbatim."`. With the read tools disallowed, the Skill tool is the only path to the text. Verify that the reply carries the `gh issue view` recovery line. Record the command and its output in the PR report

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change skill-carries-harness-context`. Verify that it archives the delta into `openspec/specs/roles/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "feat: skill-carries-harness-context" --body-file <report>`. The report:
  - references the tracking issue plainly (#315), never with `Closes`;
  - carries the scenario → test map and the live check of 3.3;
  - names the consumer follow-up: `kinozal_scraper` deletes its `.claude/rules/mindset.md` after the release.
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push.
  - Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`.
  - Answer P2/P3 without resolving.
  - If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding.
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `roles` / Another carrier named → `tests/publisher/test_start_change.py::test_codex_carrier_is_rejected` (unchanged)
- `roles` / Instructions live in Claude Code channels → `tests/publisher/test_reusable_workflows.py::test_agent_instructions_live_in_claude_code_channels`, `tests/publisher/test_reusable_workflows.py::test_review_contract_is_a_file_not_an_agents_section_parser`
- `roles` / A consumer reads principles and tactics from the skill → `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics`
