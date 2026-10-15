## Context

See proposal.md, Why. The plugin cannot ship always-on instructions: a plugin-root
`CLAUDE.md` is not loaded, and a skill body loads only when invoked. The documented always-on
carriers are the repository's `CLAUDE.md` and unscoped `.claude/rules/*.md`, both re-injected
from disk after compaction. `init` already installs managed files whose first line is
`# agent-process:managed` (`_managed_text`), and `create_tracking_issue` and `start_change`
exit 2 on release drift until Install re-runs, so an installed copy follows each release.

## Goals / Non-Goals

**Goals:** the goal function and the Claude harness tactics are in context from the first
prompt of every session in an installed repository, and again after compaction.

**Non-Goals:**

- Repositories that have not run Install. Their sessions get the harness when the skill's
  link to `always-on.md` is followed.
- §I–VII in every session. Their summary stays in `SKILL.md#principles`, read with the
  skill by the roles that apply them; the full `principles.md` costs about 3,400 tokens.

## Decisions

### D1 — One canonical file, `skills/agent-process/always-on.md`

The `## Goal function` section of `principles.md`, with its `### Scripts over instructions`,
and the `## Claude harness` section of `SKILL.md` move into `always-on.md`, verbatim but for
D3. About 2,200 characters, roughly 600 tokens. It holds no relative link: its one link,
`[the agent process](SKILL.md)`, becomes the plain words "the `agent-process` skill", because
the consumer's copy sits in `.claude/rules/`, where a relative link would resolve to nothing.

- `principles.md` keeps a `## Goal function` heading whose body is one line linking
  `always-on.md#goal-function`, so the existing `#goal-function` anchors still resolve.
  Governance names `always-on.md` as the file that holds the canon's goal function. That edit
  moves no rule between canon and delegation, so it is not a change of the delegation itself.
- `SKILL.md` keeps its goals list under `## Principles`; line 17 links
  `always-on.md#goal-function`. Its `## Claude harness` section becomes one line linking
  `always-on.md#claude-harness`.
- Links to the old anchors are repointed: `principles.md` §VII ("whose reviewer reads the
  goal function") to `always-on.md#goal-function`, ADR 0021 (`#scripts-over-instructions`),
  `CLAUDE.md` (`#claude-harness`).
- `agents/architect-reviewer.md` step 2 reads `principles.md` because "as a subagent you do not
  load the always-load rules". Custom subagents do load the project's `CLAUDE.md` and rules
  (sub-agents docs, What loads at startup), so the clause is false; the step becomes: read
  `principles.md` and `always-on.md` from the same directory in full. The reviewer's contract
  then names its goal-function source and does not depend on how a subagent expands imports,
  which the docs do not state.

The file has no frontmatter, so it is valid as an unscoped rule as is.

### D2 — `init` step `rules` copies it

A file step after `check`: `_file_step(ctx, "rules", RULES, _rules_text)` with
`RULES = ".claude/rules/agent-process.md"`. `_rules_text` reuses `_managed_text` and renders
`MANAGED + "\n\n" + (PACKAGE / "always-on.md").read_text(encoding="utf-8")`, read directly
rather than through `_template`, whose `string.Template` would treat `$` as a placeholder.
A file without the marker line is a `conflict`, as for every managed file. The docstring
inserts step 13 `rules` and renumbers the later steps.

The release-drift exit of the delivery scripts forces Install after a plugin release, so the
copy follows the release. Accepted gap: a session between a plugin update and the next Install
reads the previous release's text, which is what the consumer has committed.

Alternatives, rejected:

- A plugin `SessionStart` hook printing the sections. A workaround for a missing native
  channel, which the platform's memory docs advise removing once native reading works; its
  output is invisible in `/context` Memory files, and it needs a parser of the headings.
- An output style with `force-for-plugin`. It overrides the person's own style, and output
  styles shape the reply format.
- `AGENTS.md`. This repository's roles spec keeps instructions in `CLAUDE.md` and
  `.claude/rules/`.
- `init` extracting the sections from `principles.md` and `SKILL.md`. A heading parser in
  `init`, for text that a moved file avoids.
- Importing `principles.md` whole from the consumer's `CLAUDE.md`. About 3,400 tokens per
  session, and an owned block in a consumer-owned file.
- `additionalContext` from `skill_check.py`. Its contract is to stay silent when nothing needs
  action.
- A managed-policy `CLAUDE.md`. It needs administrator rights on each machine.

### D3 — Where the three rules land

- **Brief answers by default:** no edit. The harness already says "Be concise by default, in
  replies and in files", and D2 delivers it.
- **Do not redo a subagent's work:** the subagent bullet of the harness becomes "Spawn a
  subagent only for independent work, or for research that needs more than three round trips;
  do not redo the work it reports." Goal 2 already states the principle ("Watch for work for
  work"); the harness holds the subagent tactic.
- **A standard tool over a script of our own:** *Scripts over instructions* says a
  deterministic step "becomes a script". It becomes: "becomes a standard, maintained tool where
  one does the job (a new dependency is still asked first, §VII), otherwise a script with an
  exit code and unit tests …". After the trigger heuristic it adds: "When a tool causes
  friction, look first for the architectural choice that causes it, not for a workaround
  script." Placing it in §VII instead would conflict with this section. The edit widens the
  goal function's scope, a MINOR amendment under Governance.

### D4 — This repository imports the file

This repository is the publisher, not an installed consumer, and keeps no copy: `CLAUDE.md`
gets the line `@skills/agent-process/always-on.md`.

- memory docs, Import additional files: "Imported files are expanded and loaded into context
  at launch alongside the CLAUDE.md that references them", and "Relative paths resolve
  relative to the file containing the import". The approval dialog is for an import that is
  "external when its path resolves outside your working directory"; this one does not.
- Survival of an import through compaction is not stated; the docs say only that
  "Project-root CLAUDE.md survives compaction". Observed on 2026-10-15, Claude Code 2.1.296 on
  Windows: in a scratch repository whose `CLAUDE.md` held only `@sub/note.md`, one
  `claude -p --input-format stream-json` process received "Reply with just: ok", `/compact`
  (`compact_result: success`, then a `compact_boundary` event), and a request to quote, without
  tools, the instruction line starting with "Probe marker". It answered with the line of
  `sub/note.md` verbatim.

### D5 — Tests

- `tests/publisher/init_harness.py`: `CONSUMER_FILES` gains `.claude/rules/agent-process.md`,
  `LABELS` gains `rules` after `check`. The footprint tests then cover the new file.
- `tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file`: after a fresh
  confirmed run, and after a run over a rules file with another body, the file is
  `MANAGED + "\n\n" + always-on.md`; `always-on.md` does not start with `---`, holds
  `## Goal function` and `## Claude harness`, and has no relative Markdown link (no `](`
  followed by anything but `http`).
- `tests/publisher/test_init_conflicts.py`: a case `rules-unmanaged` writes
  `.claude/rules/agent-process.md` with `mine\n` and expects a `rules` conflict.
- `tests/publisher/test_plugin.py`: `test_package_contents_are_closed` gains `always-on.md`;
  `test_skill_carries_principles_core_and_harness_tactics` reads the harness and the three
  goals from `always-on.md` and asserts the skill body links `always-on.md#claude-harness`;
  `test_publisher_dogfoods_process` asserts the `CLAUDE.md` import line.

## Risks / Trade-offs

- Install runs from a session that has no rules file yet → that session reads the harness
  only through the skill's link; the next session has it.
- The file grows → every installed session pays for it; additions to `always-on.md` are
  reviewed as runtime token spend (goal 2).
- A consumer keeps its own `.claude/rules/agent-process.md` → `conflict`, exit 2 before any
  write.

## Migration Plan

Each consumer gets the file on its next Install, which the release-drift exit already
requires. Rollback is reverting the PR; the consumer's file is then removed by hand or left
as committed text.
