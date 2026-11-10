## MODIFIED Requirements

### Requirement: Init replaces the template's areas
`init` SHALL take a repeatable `--area <name>`; an empty name, a name holding `"`, or a repeated
name SHALL exit 2 before any command. With `--area`, a `project-areas` transition SHALL be
`planned` while the linked Project — or the copy the run makes — has the template's `Area`
options and no view named after a given area other than an area view, and `unchanged`
otherwise; an area view is named after a template option or carries no filter or the filter
below. The copy's views are read only at the write, where such a view SHALL fail the step
before any write. A confirmed run SHALL give each given name one view of that name with the
filter `-status:Done area:"<name>"`, SHALL delete the other views named after a template
option, and SHALL then set the `Area` options to exactly the given names; other views SHALL be
unchanged.

#### Scenario: Copy gets the consumer's areas
- **WHEN** a confirmed run with `--area Alpha --area "Beta Two"` copies and links the template Project
- **THEN** the linked Project's `Area` options are exactly `Alpha`, `Beta Two`, its views are the template's `Open`, `Bugs`, `Empty` and `Alpha`, `Beta Two` with their filters, and its output carries no `manual project-areas` row

#### Scenario: Retry completes the views
- **WHEN** a confirmed run with `--area Alpha` meets a Project with the template's options, a view `Alpha` with no filter and the template's `Distribution` view
- **THEN** the transition is `planned`, and the run ends with one view `Alpha` with its filter and no `Distribution` view

#### Scenario: Areas not replaced
- **WHEN** a run with `--area Alpha` meets a linked Project whose options differ from the template's, that is the template, that has no `Area` field, or that has a view `Alpha` with another filter
- **THEN** the transition is `unchanged` and the run issues no Project write

#### Scenario: Copy keeps its other views
- **WHEN** a confirmed run with `--area Bugs` copies and links the template Project
- **THEN** the run exits 1 naming `Bugs`, and the copy keeps the template's options and views

#### Scenario: Invalid area
- **WHEN** `--area` is given an empty name, a name holding `"`, or the same name twice
- **THEN** the run exits 2 and issues no command
