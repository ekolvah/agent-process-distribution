# state Specification

## Purpose
Where the process records which task is in which stage, and what moves it.

## Requirements

### Requirement: Project Status is the lifecycle field
The GitHub Project's built-in `Status` field SHALL be the lifecycle field with the built-in
options `Todo`, `In Progress`, `Done` and one option the process adds, `Planned`. `Todo`
and `Done` SHALL be written by the Project's built-in workflows (added or reopened →
`Todo`; closed or merged → `Done`); the process writes `Planned` (the propose run, on an
approved review) and `In Progress` (the apply run, at its start) and nothing else.

#### Scenario: Linking an existing Project
- **WHEN** the process is linked to an existing Project
- **THEN** the Project's built-in `Status` options are required and preserved, and `Planned` is present

#### Scenario: Issue closed
- **WHEN** a tracking issue is closed or its pull request merges
- **THEN** the Project's workflow moves it to `Done` and the process writes nothing

### Requirement: Branch creation moves the issue to In Progress
Creating the linked branch of a change's tracking issue (`start_change <change>`) SHALL move
the issue's Status to `In Progress`; a board failure stops delivery visibly instead of leaving
the branch without a status.

#### Scenario: Board failure
- **WHEN** the status move fails after the branch is created
- **THEN** the delivery stops with a non-zero exit whose message names the steps left, not with a silent branch

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
