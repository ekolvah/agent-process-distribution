## Context

`README.md` is 73 lines; under 100 lines standard-readme makes the table of contents optional
(archived `add-readme` D1). `tests/agent_process/test_doc_links.py` skips fenced blocks, so diagram
text is never checked as a link. The diagrams restate facts the README and
`skills/agent-process/SKILL.md` own; they add no claim.

## Goals / Non-Goals

**Goals:** a reader sees what runs where and how one issue becomes a merged PR without reading
the prose.

**Non-Goals:** diagrams in `SKILL.md`, specs or ADRs; images or a diagram build step.

## Decisions

**D1 — Architecture diagram under "What it is".** A Mermaid `flowchart LR`, one node per
component group, three subgraphs: the developer machine (the `agent-process` plugin with
`/agent-process:init`, the `architect-reviewer` agent, hooks and launchers; the portable skill), the
adopted repository (`.claude/commands/opsx/`, which `openspec init --tools claude` installs during
init — `skills/agent-process/scripts/init.py`; `openspec/`; `.agent-process/` and the workflows),
and GitHub (the bot account's PR; the required checks and the ruleset; the owner's approval; the
Project). Edges: init installs into the repository; the agent opens PRs under the bot account; the
ruleset gates the merge.

**D2 — Process diagram under "Usage".** A Mermaid `flowchart TD`: issue (Todo) →
`/opsx:propose` (proposal, specs, design, tasks) → architect review, `rework` looping back →
`approve`, issue Planned → owner approves the plan → `/opsx:apply`: worktree and branch, issue
In Progress → RED tests → code → Verify → archive and PR → quality check and Claude review,
findings looping back at most three rounds → owner's approval → merge, issue Done. The two Usage
bullets stay as the diagram's caption.

**D3 — Plain Mermaid, under 100 lines.** No `%%{init}%%`, theme or colour directives, so GitHub's
light and dark themes both render it; node labels in quotes where they hold `/`, `(` or `:`. Each
diagram is at most 14 lines with its fences. Text the diagrams carry is removed: the three "What it
is" bullets become one sentence pointing at the diagram, and the Why table's "that moves Todo →
Planned → In Progress → Done" clause goes, since D2 shows it. That keeps the README under 100 lines
with no table of contents. Alternative: SVG or PNG images — a second source that drifts and a render step;
ASCII art — unreadable at phone width.

## Risks / Trade-offs

- A Mermaid syntax error shows as an error box only in the browser: GitHub renders it client-side,
  so the agent cannot see it, and no local renderer is added (§VII). The PR report asks the owner to
  confirm both diagrams render on the PR's README before approving.
- The diagrams duplicate facts owned by `SKILL.md`; drift is accepted like the Install block's
  (archived `add-readme` D2), and no check is added.
