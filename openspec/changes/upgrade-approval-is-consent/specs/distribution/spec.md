## ADDED Requirements

### Requirement: An upgrade's PR approval is its consent
The Install procedure of the shared skill SHALL, after showing the dry-run, run `--confirm`
without asking when the dry-run plans no `project-copy`, `project-link`, `pre-push`,
`task-readings-url`, `task-readings-token` or `task-readings-dashboard` transition and prints no
`manual agent-identity` row; it SHALL then run `gh pr merge <PR> --auto --squash` on the PR the
run opened and ask the person to approve it. Otherwise it SHALL ask once before `--confirm`.

#### Scenario: Upgrade with the agent's identity
- **WHEN** the dry-run plans only consumer-file and PR transitions and prints no `manual agent-identity` row
- **THEN** the agent runs `--confirm` unasked, runs `gh pr merge <PR> --auto --squash` on the PR it opened, and asks the person to approve it

#### Scenario: Write outside the PR or no agent identity
- **WHEN** the dry-run plans a `project-copy`, `project-link`, `pre-push` or `task-readings-*` transition, or prints a `manual agent-identity` row
- **THEN** the agent asks once before `--confirm`

## MODIFIED Requirements

### Requirement: Install continues past the installation PR
The Install procedure of the shared skill SHALL, after the confirmed run opens the installation
PR, run `agent-process wait_for_pr <PR>`. On a first exit 3 it SHALL rerun once; a failing
`agent-process / quality` it SHALL fix by a commit on the PR and run it again; review threads and
any other failure, a second exit 3 included, it SHALL show the person, proposing a P0/P1 thread on
an installer-managed file as an issue in `ekolvah/agent-process-distribution`. Once the checks are
green it SHALL ask the person to merge; then, or on exit 4, it SHALL read
`gh pr view <PR> --json state`, on `MERGED` run steps 5 and 6 in the same session — after a
confirm run without asking, only step 5 and only when that run printed the `manual protection`
row — and on any other state show the person the state and stop install.

#### Scenario: Installation PR merged
- **WHEN** the agent follows the skill's Install procedure and the installation PR it opened is merged
- **THEN** `activate_protection` and `agent_identity` run in the same session, without a new request from the person

#### Scenario: Unasked upgrade PR merged
- **WHEN** the PR of a confirm run without asking is merged and that run printed no `manual protection` row
- **THEN** install stops without running `activate_protection` or `agent_identity`
