## ADDED Requirements

### Requirement: ci_check type-checks
`ci_check` SHALL type-check its Python modules with mypy and SHALL fail on a type error. A test
module that imports a helper module by its package path SHALL NOT stop the check.

#### Scenario: Type error
- **WHEN** a module has a type error, while a test module imports a helper module by its package path
- **THEN** `ci_check` exits non-zero and names the module and the error, and reports no module found twice
