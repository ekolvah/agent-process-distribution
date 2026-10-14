## Context

Project 4 is both this repository's board and the template `init` copies. The earlier change
`replace-priority-with-area` stopped the process writing `Priority` but kept the field for
manual use; that use has moved to the board position (proposal, Why).

## Goals / Non-Goals

**Non-Goals:** removing the field from consumer boards already installed; a script that orders
items; a requirement on board position (no step of the process reads it); editing ADR 0027,
which records the template as observed when it was written.

## Decisions

**D1 — delete the field before the archive, not after the merge.** The live read of task 2.2
then proves the new `Template read` scenario on the head the PR opens on. Alternative: delete
after merge — rejected: tasks after the archive leave no tick, so nothing would record that the
board matches the merged spec. The command is `gh project field-delete --id <field id>`
(`gh project field-delete --help`, 2026-10-14: `--id string  ID of the field to delete`).

**D2 — the spec closes the set of single-select fields instead of naming the removed one.**
Alternative: "it has no `Priority` field" — rejected: it records a dead field and lets the next
unused field reach the template unnoticed.

## Risks / Trade-offs

- [The PR is not merged after the field is deleted] → re-create it with
  `gh project field-create 4 --owner ekolvah --name Priority --data-type SINGLE_SELECT
  --single-select-options High,Medium,Low` (`gh project field-create --help`, 2026-10-14:
  `--data-type ... {TEXT|SINGLE_SELECT|DATE|NUMBER}`, `--single-select-options strings`); its three
  values are lost either way.

## Migration Plan

Merge needs no consumer action. Rollback: revert the PR and re-create the field as above.
