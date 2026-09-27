## MODIFIED Requirements

### Requirement: Project UI actions are printed, not performed
The plan of a dry-run and of a confirmed run SHALL print, as `manual`, setting the Project's
visibility, checking the template's built-in workflows, and replacing the template's `Area`
options and area views with the consumer's own, and `init` SHALL issue no command that
changes any of them.

#### Scenario: Manual actions
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries the three `manual` rows and no command it issued changes a Project's visibility, workflows, fields or views
