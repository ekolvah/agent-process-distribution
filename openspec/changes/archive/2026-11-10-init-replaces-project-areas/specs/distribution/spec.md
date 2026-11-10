## MODIFIED Requirements

### Requirement: Init's remote writes are the Project and the installation PR
A confirmed run's only GitHub writes SHALL be one copy of the template Project, one link of a
Project to the repository, with `--area` the linked Project's `Area` options and area views as
*Init replaces the template's areas* states, and the writes of *Init opens the installation
PR*: one issue, one push of the installation branch, one PR, and, in a repository with no
commits, one push of a commit with no files to the default branch. The installer SHALL NOT
create, update, or delete a ruleset, branch protection, required check, secret, any other
Project field or option, Status, or a workflow on the default branch, and SHALL NOT otherwise
commit to or push the default branch. A dry-run SHALL issue no GitHub write and SHALL make no
branch, commit, or push.

#### Scenario: Confirmed run
- **WHEN** a confirmed run without `--area` completes in a repository with commits
- **THEN** every GitHub command it issued is a read, the Project copy, the Project link, the issue creation, or the PR creation, its only push is of the installation branch, and the default branch is unchanged locally and on `origin`

#### Scenario: Dry-run
- **WHEN** a dry-run completes, with or without `--area`
- **THEN** every GitHub command it issued is a read, and the consumer repository has no new branch, commit, or push

### Requirement: Project UI actions are printed, not performed
A run SHALL print, as `manual`, setting the Project's visibility while the linked Project is
private, enabling the template's built-in workflows the linked Project lacks or has disabled —
naming only those — and, while a linked Project other than the template has the template's
`Area` options or no `Area` field, replacing the options and area views with the consumer's
own, naming `--area` for the template's options; and `init` SHALL issue no command that changes the visibility or the
workflows, nor, without `--area`, the fields or views.

#### Scenario: Manual actions
- **WHEN** a confirmed run without `--area` completes after copying and linking the template Project
- **THEN** its output carries the three `manual` rows, the workflows row names `Auto-add to project` and no other workflow, the areas row names `--area`, and no command it issued changes a Project's visibility, workflows, fields or views

## ADDED Requirements

### Requirement: Init replaces the template's areas
`init` SHALL take a repeatable `--area <name>`; an empty name, a name holding `"`, or a repeated
name SHALL exit 2 before any command. With `--area`, a `project-areas` transition SHALL be
`planned` while the linked Project — or the copy the run makes — has the template's `Area`
options, and `unchanged` otherwise. A confirmed run SHALL give each given name one view of that
name with the filter `-status:Done area:"<name>"`, SHALL delete the other views named after a
template option, and SHALL then set the `Area` options to exactly the given names; other views
SHALL be unchanged.

#### Scenario: Copy gets the consumer's areas
- **WHEN** a confirmed run with `--area Alpha --area "Beta Two"` copies and links the template Project
- **THEN** the linked Project's `Area` options are exactly `Alpha`, `Beta Two`, its views are the template's `Open`, `Bugs`, `Empty` and `Alpha`, `Beta Two` with their filters, and its output carries no `manual project-areas` row

#### Scenario: Retry completes the views
- **WHEN** a confirmed run with `--area Alpha` meets a Project with the template's options, a view `Alpha` with no filter and the template's `Distribution` view
- **THEN** the transition is `planned`, and the run ends with one view `Alpha` with its filter and no `Distribution` view

#### Scenario: Areas not replaced
- **WHEN** a run with `--area Alpha` meets a linked Project whose options differ from the template's, that is the template, or that has no `Area` field
- **THEN** the transition is `unchanged` and the run issues no Project write

#### Scenario: Invalid area
- **WHEN** `--area` is given an empty name, a name holding `"`, or the same name twice
- **THEN** the run exits 2 and issues no command
