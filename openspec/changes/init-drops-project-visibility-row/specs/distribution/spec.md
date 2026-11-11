## MODIFIED Requirements

### Requirement: Project UI actions are printed, not performed
A run SHALL print, as `manual`, enabling the template's built-in workflows the linked Project
lacks or has disabled — naming only those — and, while a linked Project other than the template
has the template's `Area` options or no `Area` field, replacing the options and area views with
the consumer's own, naming `--area` for the template's options; and `init` SHALL issue no
command that changes the visibility or the workflows, nor, without `--area`, the fields or views.

#### Scenario: Manual actions
- **WHEN** a confirmed run without `--area` completes after copying and linking the template Project
- **THEN** its output carries the `project-workflows` and `project-areas` `manual` rows, the workflows row names `Auto-add to project` and no other workflow, the areas row names `--area`, and no command it issued changes a Project's visibility, workflows, fields or views

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secrets `CLAUDE_CODE_OAUTH_TOKEN` and `GRAFANA_SERVICE_ACCOUNT_TOKEN` and the variable `GRAFANA_URL` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, the default branch requiring both process checks, this clone's settings carrying `env.GH_TOKEN`, the repository allowing auto-merge, and a linked private Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`
