## MODIFIED Requirements

### Requirement: A session leads one task
A session already bound to another issue SHALL make `finish_propose`, `start_change`
and `archive_change` exit 2 before any issue, branch, status or archive change. The message
SHALL name both issues and ask for a new session. Otherwise each script SHALL bind the session
named by `CLAUDE_CODE_SESSION_ID` to the change's tracking issue; `finish_propose`
binds a newly created issue once its number is in `tasks.md`. When
`CLAUDE_CODE_SESSION_ID` is unset, the script SHALL print that the session is not bound and
SHALL continue.

#### Scenario: Second task in one session
- **WHEN** a session bound to one issue runs `start_change` for a change of another issue
- **THEN** the script exits 2, names both issues, and creates no branch

#### Scenario: Plan creates the issue
- **WHEN** an unbound session runs `finish_propose` for a change without an issue
- **THEN** the session is bound to the issue the script created

#### Scenario: No session variable
- **WHEN** `start_change` runs without `CLAUDE_CODE_SESSION_ID`
- **THEN** it prints that the session is not bound and starts the change

### Requirement: The archive records the task's sessions
Before the change is archived, `archive_change` SHALL write every session bound to the
change's tracking issue into the change's `sessions` file, one id per line.

#### Scenario: Plan and implementation in two sessions
- **WHEN** one session ran `finish_propose` and another ran `start_change` and
  `archive_change` for the same change
- **THEN** the archived change's `sessions` lists both session ids
