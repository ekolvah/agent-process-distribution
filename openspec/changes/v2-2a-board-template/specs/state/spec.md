## ADDED Requirements

### Requirement: The board is a copy of the template Project
Project 4 of this repository SHALL be the template a consumer's board is copied from: it
is public; its `Status` field has the options `Todo`, `Planned`, `In Progress`, `Done` and
nothing else; its `Priority` field has `High`, `Medium`, `Low`; and its built-in workflows
*Auto-add to project* (open issues and pull requests of the repository), *Item added →
Todo*, *Item reopened → Todo*, *Item closed → Done* and *Pull request merged → Done* are
enabled.

#### Scenario: Template read
- **WHEN** the template Project is read through the GitHub API
- **THEN** it is public, its `Status` options are exactly `Todo`, `Planned`, `In Progress`, `Done`, its `Priority` options are `High`, `Medium`, `Low`, and the five workflows are enabled

## MODIFIED Requirements

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

### Requirement: Priority is set at creation
Priority SHALL be a Project field set by name in the same call as the first status the
process writes for the tracking issue (`set_status <N> "Planned" --priority <name>` at the
end of the propose run), fields and options resolved by name. The call SHALL take a Status,
a Priority or both: an issue created outside a change gets its `Todo` from the Project and
needs only `--priority`. The Project SHALL be the one linked to the repository; when none
or several are linked the run SHALL report them and change nothing. The propose run SHALL
ask the person for the priority before it creates the tracking issue; no delivery task asks.

#### Scenario: Tracking issue created
- **WHEN** the propose run sets the first status of a new tracking issue with a priority
- **THEN** both fields are set in one call and the issue is an item of the repository's Project

#### Scenario: Priority asked once
- **WHEN** the propose run creates the tracking issue
- **THEN** it asks the person for the priority before the first status and never again

#### Scenario: Priority field drift
- **WHEN** the Project has no option for the given priority
- **THEN** the run reports it before any status is changed

#### Scenario: Priority only
- **WHEN** an issue is created outside a change and the call names a priority and no status
- **THEN** only `Priority` is written and `Status` is left to the Project's workflow

#### Scenario: Several linked Projects
- **WHEN** more than one Project is linked to the repository
- **THEN** the run names them and changes nothing
