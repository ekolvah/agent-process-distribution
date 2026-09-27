## REMOVED Requirements

### Requirement: Area is set at creation
**Reason**: The planner chooses the area; the person is no longer asked.
**Migration**: See "Area is chosen at creation"; the commands are unchanged.

## ADDED Requirements

### Requirement: Area is chosen at creation
Area SHALL be a Project field set by name in the same call as the first status the process
writes for the tracking issue (`set_status <N> "Planned" --area <name>` at the end of the
propose run), fields and options resolved by name. The call SHALL take a Status, an Area or
both: an issue created outside a change gets its `Todo` from the Project and needs only
`--area`. The Project SHALL be the one linked to the repository; when none or several are
linked the run SHALL report them and change nothing. The planner SHALL choose the area
from the Project's `Area` options by the content of the change and SHALL NOT ask the person;
the person re-files a wrong pick on the board.

#### Scenario: Tracking issue created
- **WHEN** the propose run sets the first status of a new tracking issue with an area
- **THEN** both fields are set in one call and the issue is an item of the repository's Project

#### Scenario: Area chosen by the planner
- **WHEN** the propose run creates the tracking issue
- **THEN** it passes an `Area` option it chose itself, asking the person nothing; without `--area` the run exits 2 listing the options and creates no issue

#### Scenario: Area field drift
- **WHEN** the Project has no `Area` field, or no option for the given area
- **THEN** the run exits 2 naming the fields or the options before any issue is created or any status is changed

#### Scenario: Area only
- **WHEN** an issue is created outside a change and the call names an area and no status
- **THEN** only `Area` is written and `Status` is left to the Project's workflow

#### Scenario: Several linked Projects
- **WHEN** more than one Project is linked to the repository
- **THEN** the run names them and changes nothing
