## MODIFIED Requirements

### Requirement: Protection activation observes quality first
`activate_protection` SHALL exit non-zero before any GitHub write unless two things hold.
The default branch SHALL carry `.github/workflows/agent-process.yml`. The current head of
the given PR against the default branch SHALL have a check run `agent-process / quality`
that concluded `success` from the GitHub Actions app. When the default branch also carries
`.github/workflows/agent-review.yml`, the same head SHALL have a check run
`agent-review / agent-review` that concluded `success` from that app, and the run SHALL
require both contexts. Each required check SHALL bind the integration ID of the app that
reported it.

#### Scenario: Caller absent
- **WHEN** the default branch has no `.github/workflows/agent-process.yml`
- **THEN** the run names the missing caller, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Context not observed
- **WHEN** the PR's base is not the default branch, or its current head has no `agent-process / quality` check run, or that run did not succeed, or another app reported it
- **THEN** the run names what it observed on that head, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Review caller present
- **WHEN** the default branch carries `.github/workflows/agent-review.yml` and the PR head has successful `agent-process / quality` and `agent-review / agent-review` runs from GitHub Actions
- **THEN** the planned ruleset requires both contexts, each with that app's integration ID

#### Scenario: Review context not observed
- **WHEN** the default branch carries `.github/workflows/agent-review.yml` and the PR head has no successful `agent-review / agent-review` run from GitHub Actions
- **THEN** the run names what it observed for that context, exits non-zero, and every GitHub command it issued is a read

### Requirement: Activation reads back what it wrote
After a write, the run SHALL read the ruleset back and SHALL exit non-zero on the first
field that differs, and name it. The checked fields are the default-branch ref, active
enforcement, the pull request, deletion, and non-fast-forward rules, the empty bypass list,
the strict policy, and the exact set of required contexts, each with its integration ID, in
any order.

#### Scenario: Read-back mismatch
- **WHEN** the ruleset read after a write lacks a barrier rule, has a bypass actor, requires another context or integration, or lacks or adds a context
- **THEN** the run exits non-zero and names that field

#### Scenario: Read-back reorders contexts
- **WHEN** the ruleset read after a write returns the written contexts in another order
- **THEN** the read-back passes, and a later dry-run prints `unchanged`
