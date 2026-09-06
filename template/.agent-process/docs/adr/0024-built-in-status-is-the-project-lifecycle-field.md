---
status: "accepted"
date: 2026-09-07
decision-makers: ekolvah
---

# Built-in Status is the Project lifecycle field

## Context and Problem Statement

The process previously wrote Planned/In Progress to a custom Agent status field
while GitHub's default board used built-in Status. One issue could therefore be
planned yet appear in Todo; a live Project also contained Done plus legacy In
Progress, proving a blind value copy would regress terminal state.

## Considered Options

* Retain two lifecycle fields.
* Replace the built-in Status option list or all item values.
* Use built-in Status, preserve option identities, and migrate explicitly.

## Decision Outcome

Chosen: **built-in Status is the only lifecycle field.** Bootstrap appends
Planned while supplying all existing option ids, names, colours, and descriptions
to GitHub's replacement-style field mutation. The process owns Planned/In
Progress; GitHub automations own Todo/Done.

Migration is read-only until --confirm-write, preserves Done, re-reads item
postconditions before generated settings change, and reports partial progress
instead of inventing rollback. Agent status retirement and view edits are not
normal migration work; deletion needs a separate confirmed, view-free report.

### Consequences

* Good, because board columns and process state have one source of truth.
* Good, because option identities and terminal values are retained.
* Bad, because legacy migration is an explicit operational step with visible
  partial-state recovery rather than an automatic bootstrap side effect.

### Confirmation

Publisher migration and bootstrap tests cover option preservation, Status subset
validation, terminal preservation, report-only default, and rerun planning.
