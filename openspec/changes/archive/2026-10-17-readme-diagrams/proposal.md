## Why

`README.md` explains the architecture (plugin, skill, gates, GitHub) and the process (issue →
plan → PR → merge) in prose and tables only; a reader has to assemble both pictures in their head.

GitHub renders Mermaid in Markdown — observed on
[Creating diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams):
"You can create diagrams in Markdown using four different syntaxes: mermaid, geoJSON, topoJSON,
and ASCII STL." and "To create a Mermaid diagram, add Mermaid syntax inside a fenced code block
with the `mermaid` language identifier."

## What Changes

- Add an architecture diagram to `README.md` (design D1).
- Add a process diagram to `README.md` (design D2).
- Shorten the prose the diagrams now carry so the README stays under 100 lines (design D3).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Docs-only: `skip_specs: true`.

## Impact

- Edited: `README.md`.
