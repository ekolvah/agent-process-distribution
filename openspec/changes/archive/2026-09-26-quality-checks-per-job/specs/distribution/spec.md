## MODIFIED Requirements

### Requirement: The quality callee runs the caller's commands
The reusable workflow `quality.yml` SHALL take an optional `setup`, a required `test`, and an
optional `checks` command from its caller. A job SHALL verify that the PR links its issue.
When `checks` is given, its output SHALL be a JSON array of check names, and each name SHALL
run `setup` when one is given and then `test --only <name>` on the PR's checkout, in a job of
its own named after the check. A failing check job SHALL NOT cancel another. Without `checks`,
one job SHALL run `setup` and then `test`. The job `quality` SHALL succeed only when the link
job, the listing job, and every check job succeeded, and SHALL fail otherwise, including when
one of them was skipped or cancelled.

#### Scenario: Consumer test fails
- **WHEN** a caller's `test` command exits non-zero on a PR that links its issue
- **THEN** the `quality` job fails

#### Scenario: One check fails
- **WHEN** a caller gives `checks`, and on a PR that links its issue one listed check exits non-zero
- **THEN** that check's job fails, every other listed check's job runs to its own conclusion, and the `quality` job fails

#### Scenario: Listing fails
- **WHEN** the `checks` command exits non-zero or prints anything but a non-empty JSON array of check names
- **THEN** the `quality` job fails

### Requirement: A context the PR cannot change gates every head
Every head of this repository SHALL be gated by a required context that the PR cannot
change: `agent-review / agent-review`, which reviews that head. A required context that runs
the PR's own driver, `agent-process / quality`, SHALL be required only beside it. Each PR
SHALL run each check of the quality driver once.

#### Scenario: PR weakens its own driver
- **WHEN** a PR of this repository changes the driver that `agent-process / quality` runs
- **THEN** the contexts the repository declares required for that head still include `agent-review / agent-review`

#### Scenario: Quality runs once per PR
- **WHEN** a PR of this repository opens or receives a push
- **THEN** only jobs of the `agent-process` caller execute the quality driver on its head, and each check of its registry runs in exactly one of them
