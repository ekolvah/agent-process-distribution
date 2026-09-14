## ADDED Requirements

### Requirement: Project Status is the lifecycle field
The GitHub Project's built-in `Status` field SHALL be the lifecycle field. No process-owned
state file SHALL exist.

#### Scenario: Resuming work
- **WHEN** an agent or a person resumes a change
- **THEN** the stage is read from the Project, not from a local file

### Requirement: Built-in automations move items
Transitions SHALL use the Project's built-in automations where they exist: item added → Todo,
issue closed or PR merged → Done.

#### Scenario: Merge
- **WHEN** the PR merges
- **THEN** the item moves to Done without a process script

### Requirement: set_status resolves by name
One script, `set_status`, SHALL move an issue to In progress when implementation starts,
resolving field and option IDs by name at run time from the Project number in a repository
variable. Nothing SHALL be generated per project.

#### Scenario: New project
- **WHEN** `set_status` runs in a project for the first time
- **THEN** it works with only the Project number configured

### Requirement: Delivery stage is readable from GitHub alone
The stage of a delivery SHALL be readable from Project status, linked branch, PR checks and
review threads.

#### Scenario: Person checks progress
- **WHEN** the person opens the issue and its PR
- **THEN** the stage is evident without running anything

### Requirement: No custom statuses and no Project creation
The process SHALL NOT add status values beyond the Project's own and SHALL NOT create the
Project; `init` links to an existing one.

#### Scenario: init without a Project
- **WHEN** `init` runs and no Project number is given
- **THEN** it asks for one and does not create a Project
