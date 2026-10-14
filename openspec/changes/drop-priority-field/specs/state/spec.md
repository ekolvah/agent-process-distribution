## MODIFIED Requirements

### Requirement: The board is a copy of the template Project
Project 4 of this repository SHALL be the template a consumer's board is copied from: it
is public; its single-select fields are `Status` and `Area` and nothing else; `Status` has
the options `Todo`, `Planned`, `In Progress`, `Done` and nothing else; `Area`'s options are
this repository's areas; and its built-in workflows *Auto-add to project* (open issues and
pull requests of the repository), *Item added → Todo*, *Item reopened → Todo*, *Item closed →
Done* and *Pull request merged → Done* are enabled.

#### Scenario: Template read
- **WHEN** the template Project is read through the GitHub API
- **THEN** it is public, its single-select fields are exactly `Status` and `Area`, its `Status` options are exactly `Todo`, `Planned`, `In Progress`, `Done`, `Area` has at least one option, and the five workflows are enabled
