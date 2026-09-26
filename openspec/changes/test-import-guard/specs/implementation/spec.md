## ADDED Requirements

### Requirement: ci_check forbids test-to-test imports
`ci_check` SHALL fail when a test module imports another test module. A test module MAY import
a non-test helper module.

#### Scenario: Test module imports a test module
- **WHEN** a test module imports another test module, while another imports only a helper module
- **THEN** `ci_check` exits non-zero and names the importing and the imported test module, and reports nothing for the helper import
