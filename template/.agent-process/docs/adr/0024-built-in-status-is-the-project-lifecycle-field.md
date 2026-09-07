---
status: "accepted"
date: 2026-09-07
decision-makers: ekolvah
---

# Built-in Status is the Project lifecycle field

## Context and Problem Statement

The process previously wrote Planned/In Progress to a custom Agent status field
while GitHub's default board used built-in Status. One issue could therefore be
planned yet appear in Todo. Existing Agent status values are stale, are not a
source of truth, and are deliberately not retained by this decision.

## Considered Options

* Retain two lifecycle fields.
* Replace the built-in Status option list or migrate all item values.
* Use built-in Status, preserve option identities, and delete the legacy field.

## Decision Outcome

Chosen: **built-in Status is the only lifecycle field.** Bootstrap appends
Planned while supplying all existing option `id`, name, colour, and description
values to GitHub's replacement-style field mutation. The process owns Planned/In
Progress; GitHub automations own Todo/Done.

For an activated Project, `--confirm-status-setup` uses its generated settings,
resolves a persisted `@me` owner from the stored Project node rather than the
current viewer, and rejects a Project-number mismatch before reading fields. It
appends Planned only after a full option read, and re-reads the field before
generated settings change. It validates In Progress before any mutation and does
not inspect or transform item values. After source and generated settings receive
current-head review, a separate live preflight confirms no view uses Agent status;
only then is the obsolete field deleted. Its values are intentionally discarded.

### Consequences

* Good, because board columns and process state have one source of truth.
* Good, because option identities are retained and stale secondary data is gone.
* Bad, because deleting the legacy field permanently discards its values.

### Confirmation

Publisher bootstrap tests cover option preservation, Status subset validation,
confirmed existing-project setup, and preflight failure before settings writes.
