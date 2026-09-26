## ADDED Requirements

### Requirement: The PR title carries a Conventional Commit type
The Deliver group of every `tasks.md` SHALL open the PR with the title `<type>: <change>`,
where `<type>` is the Conventional Commit type the planner chose for the change: `feat` or
`fix` when behaviour changes, otherwise a type that cuts no release (`docs`, `test`,
`refactor`, `chore`). The squash commit of the PR on `main` SHALL carry that title. In this
repository a `pr-title` check SHALL run on every opened, edited, pushed, or reopened PR and
SHALL fail when the title is not a Conventional Commit of one of those types; a ruleset of its
own, beside the process ruleset, SHALL require that check for a merge into `main`.

#### Scenario: Behaviour change delivered
- **WHEN** a change that alters behaviour is merged
- **THEN** its commit on `main` is titled `feat: <change>` or `fix: <change>`, and the next release PR counts it

#### Scenario: Title without a type
- **WHEN** a PR into `main` is titled without an allowed Conventional Commit type
- **THEN** its `pr-title` check fails and the PR cannot be merged until an edited title passes the re-run check
