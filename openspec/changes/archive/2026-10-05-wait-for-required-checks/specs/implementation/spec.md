## MODIFIED Requirements

### Requirement: The implementing run ends only after checks and reviews
The implementing run SHALL end only after the PR's checks and reviews are in on its head.
One blocking script, `wait_for_pr`, SHALL read the head's checks as `gh pr checks` reports
them until the head reports every status check the rules of the PR's base branch require and
none is pending, then read the review threads and print the unresolved ones; the run SHALL
apply them and wait again until nothing is unresolved, or reply on a thread it leaves to the
person and end. A check that has not concluded SHALL count as a pending review, and a
required check the head does not report yet SHALL count as one too; a base branch whose rules
require no check SHALL be reported as such before the wait. The wait for a requested review
SHALL be the `agent-review` check's own bounded wait, not the script's; a failed or cancelled
check SHALL count as unresolved; threads SHALL be read only after every check on the head has
concluded. The end state SHALL never be ambiguous: nothing unresolved (exit 0), unresolved
items printed (exit 1), a `gh` failure reported with its message (exit 2), or a timeout
reported with what was still awaited (exit 3).

#### Scenario: Pending review
- **WHEN** the PR is open and a review is pending
- **THEN** the run is blocked in `wait_for_pr` and cannot report completion

#### Scenario: Empty rollup after a push
- **WHEN** `wait_for_pr` runs before any check has attached to the head
- **THEN** it reads again instead of reporting clean or failed, and reads threads only once every check of the head has concluded

#### Scenario: Required check not yet attached
- **WHEN** the head reports only concluded checks of other workflows and a check the base branch requires is absent
- **THEN** `wait_for_pr` reads again naming the absent check, never reports clean, and on timeout exits 3 naming it

#### Scenario: No required checks on the base branch
- **WHEN** the rules of the PR's base branch require no status check
- **THEN** `wait_for_pr` prints a note that it settles on the reported checks only, then waits as for any head
