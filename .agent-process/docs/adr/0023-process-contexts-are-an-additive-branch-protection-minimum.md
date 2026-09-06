---
status: "accepted"
date: 2026-09-06
decision-makers: ekolvah
---

# Process contexts are an additive branch-protection minimum

## Context and Problem Statement

The process needs three required checks on a consumer's default branch, but a
consumer may already require unrelated checks with specific GitHub App bindings
and may carry review, bypass, push, history, deletion, or other protection policy.
A full `required_status_checks` replacement containing only process contexts can
silently remove that repository-owned configuration. The old verifier also called
every additional check drift and printed exactly such a replacement command.

Classic required-context names do not authenticate the workflow definition that
reported them. [ADR 0012](0012-ci-logic-is-referenced-not-copied.md) records that
separate trust limitation; installing contexts must not overstate what they prove.

## Considered Options

* Replace the complete branch-protection document with a canonical process policy.
* Read the complete policy, merge process contexts locally, and write it all back.
* Treat the process contexts as a minimum and use GitHub's additive and narrow
  branch-protection subresources.
* Migrate installation and verification to GitHub rulesets.

## Decision Outcome

Chosen: **process contexts are a required minimum, while every additional check
and policy field remains consumer-owned.**

For an already protected branch,
`install_branch_protection.py` uses GitHub's additive status-context endpoint for
missing names, the status-check subresource for strict checking, and the admin
subresource for administrator enforcement. It never sends the full branch policy
and never replaces an existing `(context, app_id)` pair. The confirmed command
re-reads protection and compares those pairs plus every unowned field with the
pre-write snapshot.

When classic protection is entirely absent, no consumer policy exists to preserve.
Only then may one confirmed full-protection request create the documented baseline:
strict process checks, administrator enforcement, no required reviews or push
restrictions, and force-push/deletion disabled.

The command is a read-only plan unless `--confirm-write` is present. A confirmed
multi-call update is convergent rather than atomic: if a later operation fails, the
command reports the operations that completed, re-reads the observed state, exits
non-zero, and the same command can be rerun safely. A configured rerun writes
nothing.

### Consequences

* Good, because installing or repairing the process cannot intentionally remove a
  consumer check, App binding, review rule, bypass, or push restriction.
* Good, because dry-run output makes the remote-write boundary reviewable and the
  post-write read detects incomplete or collateral changes.
* Bad, because a sequence of narrow GitHub calls is not transactional; a failed run
  can leave visible partial progress until its idempotent rerun succeeds.
* Bad, because adding a check by name lets GitHub select its resulting App binding;
  the installer can report that binding but cannot promise one for a new context.
* Bad, because classic name-based protection is still not a workflow-definition
  trust anchor. A platform or organisation ruleset remains necessary where that
  stronger boundary is required.

Full-list replacement is rejected because stale reads, concurrent changes, or an
incomplete response can destroy unrelated policy. Ruleset migration is rejected for
this issue because it changes the enforcement, availability, and verification model
rather than narrowly making classic protection safe to install.

### Confirmation

`tests/agent_process/test_branch_protection.py` (rendered from the template consumer
suite) covers additive protected updates, strict/admin subresources, the unprotected
baseline, dry-run and preflight failures, partial-failure recovery, idempotence, and
consumer-owned extra checks. Template drift and self-installation tests prove that
the portable source and this repository's rendered copy stay aligned.

