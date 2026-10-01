## ADDED Requirements

### Requirement: Init names a failed command's output
When a command `init` runs exits non-zero, the error SHALL name every non-empty captured stream,
stderr before stdout. When neither stream was captured, it SHALL say `output not captured`.

#### Scenario: Output on both streams
- **WHEN** a command exits 1 with text on stderr and different text on stdout
- **THEN** the error names the exit code and both texts, stderr first

#### Scenario: Output not captured
- **WHEN** a command exits 1 and neither of its streams was captured
- **THEN** the error says `output not captured`
