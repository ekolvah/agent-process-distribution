## REMOVED Requirements

### Requirement: Priority is set at creation
**Reason**: The backlog is ordered by area and board position; the process no longer writes
`Priority`.
**Migration**: `--priority <name>` becomes `--area <name>` on `set_status` and
`create_tracking_issue`; see "Area is set at creation".

## ADDED Requirements

### Requirement: Area is set at creation
Area SHALL be a Project field set by name in the same call as the first status the process
writes for the tracking issue (`set_status <N> "Planned" --area <name>` at the end of the
propose run), fields and options resolved by name. The call SHALL take a Status, an Area or
both: an issue created outside a change gets its `Todo` from the Project and needs only
`--area`. The Project SHALL be the one linked to the repository; when none or several are
linked the run SHALL report them and change nothing. The propose run SHALL ask the person for
the area before it creates the tracking issue; no delivery task asks.

#### Scenario: Tracking issue created
- **WHEN** the propose run sets the first status of a new tracking issue with an area
- **THEN** both fields are set in one call and the issue is an item of the repository's Project

#### Scenario: Area asked once
- **WHEN** the propose run creates the tracking issue
- **THEN** it asks the person for the area before the first status and never again

#### Scenario: Area field drift
- **WHEN** the Project has no `Area` field, or no option for the given area
- **THEN** the run exits 2 naming the fields or the options before any issue is created or any status is changed

#### Scenario: Area only
- **WHEN** an issue is created outside a change and the call names an area and no status
- **THEN** only `Area` is written and `Status` is left to the Project's workflow

#### Scenario: Several linked Projects
- **WHEN** more than one Project is linked to the repository
- **THEN** the run names them and changes nothing

## MODIFIED Requirements

### Requirement: The board is a copy of the template Project
Project 4 of this repository SHALL be the template a consumer's board is copied from: it
is public; its `Status` field has the options `Todo`, `Planned`, `In Progress`, `Done` and
nothing else; its `Priority` field has `High`, `Medium`, `Low`; it has a single-select
`Area` field whose options are this repository's areas; and its built-in workflows
*Auto-add to project* (open issues and pull requests of the repository), *Item added →
Todo*, *Item reopened → Todo*, *Item closed → Done* and *Pull request merged → Done* are
enabled.

#### Scenario: Template read
- **WHEN** the template Project is read through the GitHub API
- **THEN** it is public, its `Status` options are exactly `Todo`, `Planned`, `In Progress`, `Done`, its `Priority` options are `High`, `Medium`, `Low`, it has a single-select `Area` field with at least one option, and the five workflows are enabled
