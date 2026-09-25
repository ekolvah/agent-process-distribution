## Context

See proposal.md — Why. The Install section of the skill defines that `skills/agent-process/`
in a command means the skill's own directory in a consumer; a model that loaded the skill knows
that directory, but the `architect-reviewer` subagent does not load the skill, and in a
consumer the Claude plugin lives in the plugin cache
(`~/.claude/plugins/cache/agent-process-marketplace/agent-process/<version>/`, observed on this
machine), not in the repository. Codex performs the review itself with the skill loaded from
`~/.agents/skills/agent-process`, so `principles.md` beside `SKILL.md` resolves for it.

Platform observation (§V), https://code.claude.com/docs/en/plugins/manifest-reference.md
§"Where each variable resolves": the row "Skill, command, and agent content | Anywhere in the
Markdown body", and "In skill, command, and agent content, write the `${...}` reference in the
Markdown body instead, and Claude Code substitutes the path inline when it loads the content."

## Goals / Non-Goals

**Goals:** one principles file readable by publisher and consumer; no instruction to use a
path the installer does not create.

**Non-Goals:** rewording principles beyond the one publisher-only link; shipping or installing
a pre-push hook in consumers; editing archived changes or ADR prose that names
`principles.md` without linking it.

## Decisions

1. **Move, not copy, `principles.md` into the skill.** A copy would give two sources of truth
   that drift. Alternative rejected: the reviewer reads a consumer-declared principles file —
   the skill and `planning` spec bind the review to §I–VII, which the package must then carry.
   Its links to `SKILL.md` become `SKILL.md`; the §VII link to
   `.agent-process/REVIEW_CONTRACT.md` is dropped (a consumer has no such file), keeping the two
   trigger phrases that `test_review_contract_and_principles_stay_coupled_…` asserts.
2. **The reviewer names its package files through `${CLAUDE_PLUGIN_ROOT}`.** Steps 1–2 of
   `agents/architect-reviewer.md` read `SKILL.md`, the schema and `principles.md` from
   `skills/agent-process/` at the repository root when that directory exists (the publisher's
   source, so this repository's reviews exercise the source, per "This repository dogfoods its
   own process"), otherwise from `${CLAUDE_PLUGIN_ROOT}/skills/agent-process/`. Alternative
   rejected: `${CLAUDE_PLUGIN_ROOT}` alone — in this repository it resolves to the cached
   release, so a change to the review contract would be reviewed against the previous one.
3. **Drop the pre-push sentence from Install step 4** rather than ship a hook: the footprint
   requirement forbids copying publisher files and `test_package_contents_are_closed` forbids a
   hook in the package. What stops being asked: a consumer clone running `ci_check` locally
   before push. Catcher reached: `agent-process / quality` on the PR head, required by the
   ruleset `activate_protection` writes. This repository keeps its own hook.
4. **One publisher test** in `tests/publisher/test_plugin.py` over the text files of
   `skills/agent-process/`, `agents/`, `commands/`: fail on `.agent-process/` not preceded by
   `~/` (the user-profile checkout of `init.py` is not a repository path); on a relative
   Markdown link of a skill file that leaves the skill directory (a missing target is already
   `test_doc_links::test_every_internal_link_resolves`); and on an agent file that names
   `skills/agent-process/` without `${CLAUDE_PLUGIN_ROOT}/skills/agent-process/`.
   `test_package_contents_are_closed` gains `principles.md`.
5. **Doc guards follow the move.** The move empties `.agent-process/docs/architecture/`. In
   `test_doc_links.py` and `test_doc_narrative.py` (scope: all tracked files) the non-vacuity
   entry `.agent-process/docs/architecture` becomes `skills/agent-process`. In
   `test_doc_headers.py` the header scope keeps `.claude/rules` and adds the file
   `skills/agent-process/principles.md` (not the whole skill directory: `SKILL.md` carries its
   question as front-matter `description`); `test_every_scoped_directory_contributes` covers it
   as an existing-file check. The `maintenance` requirement "Documents are guarded" names the
   new location. No guard is dropped: `principles.md` stays under the header, link and
   narrative guards.

## Risks / Trade-offs

- [Principles text keeps repository-specific examples (§IV ruff rules)] → accepted; wording is
  out of scope, and they are not paths the agent is told to read.
- [The fallback rule in D2 picks a consumer's own `skills/agent-process/` if one exists] →
  accepted: that directory is the skill's reserved path in the Install convention.
- [Live links in this repo to the old path] → updated in the same PR; archived changes keep
  the historical path.
