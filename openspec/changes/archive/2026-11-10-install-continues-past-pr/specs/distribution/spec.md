## ADDED Requirements

### Requirement: Install continues past the installation PR
The Install procedure of the shared skill SHALL, after the confirmed run opens the installation
PR, run `agent-process wait_for_pr <PR>`. On a first exit 3 it SHALL rerun once; a failing
`agent-process / quality` it SHALL fix by a commit on the PR and run it again; review threads and
any other failure, a second exit 3 included, it SHALL show the person, proposing a P0/P1 thread on
an installer-managed file as an issue in `ekolvah/agent-process-distribution`. Once the checks are
green it SHALL ask the person to merge; then, or on exit 4, it SHALL read
`gh pr view <PR> --json state`, on `MERGED` run steps 5 and 6 in the same session, and on any
other state show the person the state and stop install.

#### Scenario: Installation PR merged
- **WHEN** the agent follows the skill's Install procedure and the installation PR it opened is merged
- **THEN** `activate_protection` and `agent_identity` run in the same session, without a new request from the person
