## Context

See proposal.md — Why. `init`'s `plugin-channel` row is printed only while `_plugin_channel`
does not observe the channel done, and Install's step 4 enumerates the rows the person does
after the PR opens.

## Decisions

### D1. Prepare carries the commands; `init` keeps the row

The Prepare bullet lists the three steps in the row's order (edits: proposal.md — What Changes).
The row stays in `init` as the check for a machine that skipped Prepare; step 4's "do those
rows" still covers it without naming it.

Prepare holds the Install section's one copy of the commands: the plugin paragraph says "by
Prepare" and "a machine that followed Prepare" instead of copying `claude plugin install` and
naming the row, and the release-tag migration sentence becomes "set `ref` to `stable`, do
Prepare's plugin step, then re-run Install in each repository".

Alternative: remove the row from `init`. Rejected: it is the only observation of a machine whose
channel is off `stable` or without auto-update; dropping it loses that proof (§IV).

### D2. Out of scope: README, `init.py` docstring, row text

The README's once-per-machine block stays: a reader reaches it before the skill, and it already
matches Prepare. The `init.py` docstring and the row text describe the row, which is unchanged.

## Risks / Trade-offs

- [Prepare and the README list the same three commands] → a later channel change edits both;
  `test_install_names_the_skill_marker` pins the Prepare copy, the only one left in Install.
