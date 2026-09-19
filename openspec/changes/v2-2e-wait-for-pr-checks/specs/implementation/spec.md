## MODIFIED Requirements

### Requirement: The implementing run ends only after checks and reviews
The implementing run SHALL end only after the PR's checks and reviews are in on its head.
One blocking script, `wait_for_pr`, SHALL read the head's checks as `gh pr checks` reports
them until the head reports at least one check and none is pending, then read the review
threads and print the unresolved ones; the run SHALL apply them and wait again until
nothing is unresolved, or reply on a thread it leaves to the person and end. A check that
has not concluded SHALL count as a pending review; the wait for a requested review SHALL be
the `agent-review` check's own bounded wait, not the script's; a failed or cancelled check
SHALL count as unresolved; threads SHALL be read only after every check on the head has
concluded. The end state SHALL never be ambiguous: nothing unresolved (exit 0), unresolved
items printed (exit 1), a `gh` failure reported with its message (exit 2), or a timeout
reported with what was still awaited (exit 3).

#### Scenario: Pending review
- **WHEN** the PR is open and a review is pending
- **THEN** the run is blocked in `wait_for_pr` and cannot report completion

#### Scenario: Empty rollup after a push
- **WHEN** `wait_for_pr` runs before any check has attached to the head
- **THEN** it reads again instead of reporting clean or failed, and reads threads only once every check of the head has concluded
