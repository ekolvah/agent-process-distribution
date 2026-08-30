---
status: "accepted"
date: 2026-08-30
decision-makers: ekolvah
---

# Established-project adoption owns reserved paths, not consumer configuration files

## Context and Problem Statement

The Copier payload began as a root overlay. In an established repository,
`--force` could replace product CI, dependency manifests, ignore rules, pull
request guidance, and agent instructions. Copier conflict handling is not a
transaction: an update can leave `.rej` files or inline conflict markers.

## Decision Outcome

The distribution owns only `.agent-process/**` and
`.github/workflows/agent-process-*.yml` as complete files. Product configuration
remains consumer-owned. Adoption completes preflight before writing and rejects
every collision and unresolved Copier artifact. The three reserved callers keep
the published composed check names. A named shared text file may use one
delimited managed fragment; malformed or duplicate delimiters stop the operation.
Updates may replace a path only after the ownership manifest proves that the
process installed it.

We rejected `_skip_if_exists` and manual prompts because either can leave
required integration absent. We rejected a generic YAML/TOML merge engine
because it would guess product semantics and become a separate support surface.
Copier remains the ADR 0011 distribution mechanism; this narrows its safe
payload boundary, complements ADR 0012, and preserves ADR 0013's drift boundary.

### Consequences

* An ownership-class change requires an explicit migration and clean plus
  established-project update coverage before release.
* Remote branch-protection mutation remains issue #18's responsibility.
* Publisher/consumer test ownership remains issue #20's responsibility.
