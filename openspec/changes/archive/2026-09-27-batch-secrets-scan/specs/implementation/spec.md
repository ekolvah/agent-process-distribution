## ADDED Requirements

### Requirement: ci_check scans secrets within the command-line limit
The `secrets` check of `ci_check` SHALL scan every target it selects, passing them in batches so
that no command line it starts exceeds the Windows limit of 32767 characters, and SHALL fail
when any batch reports a finding.

#### Scenario: Targets beyond one command line
- **WHEN** the targets' single command line would exceed 32767 characters and a secret sits in a file of the last batch
- **THEN** every started command line is at most the limit, the batches together pass every target once, and `ci_check` exits non-zero
