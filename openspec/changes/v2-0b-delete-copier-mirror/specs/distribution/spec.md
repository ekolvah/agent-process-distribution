## REMOVED Requirements

### Requirement: Layered delivery through Copier
**Reason**: The Copier render has no consumer other than this repository, and its
self-hosting drift gate doubles the diff of every v2 step that deletes a root file. The
mechanism is retired before v2-1 instead of inside v2-2 (#119, step 0b of #107).
**Migration**: None for existing consumers — the one migrated project (#117) keeps its
copied files and moves to the v2 delivery after v2-2. New installations wait for `init`
(v2-2); the Claude plugin marketplace (`.claude-plugin/`) and the pinned reusable workflows
(`.github/workflows/reusable-*.yml`) stay in place and are restated by the v2-2 delta.
