## ADDED Requirements

### Requirement: Bare openspec runs the pin
The plugin SHALL ship `openspec` as an executable of its `bin/`, which SHALL run
`npx -y @fission-ai/openspec@<pin>` with all its arguments and propagate the exit code, where
`<pin>` is the OpenSpec version `init` installs. Outside `openspec/changes/`, no tracked file
other than `bin/openspec` SHALL write an OpenSpec version after `@fission-ai/openspec@`.

#### Scenario: Bare command
- **WHEN** `openspec <args>` runs with the plugin's `bin/` on `PATH` and no other `openspec` before it
- **THEN** `npx` runs with `-y @fission-ai/openspec@<pin> <args>`, each argument intact, and its exit code is the command's

#### Scenario: One pin
- **WHEN** the publisher tests read the tracked files outside `openspec/changes/`
- **THEN** `bin/openspec` names `@fission-ai/openspec@<pin>`, and any other file that writes a version after `@fission-ai/openspec@` fails naming the file
