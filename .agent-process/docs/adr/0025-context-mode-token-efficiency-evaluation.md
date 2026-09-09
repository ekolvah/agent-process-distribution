---
status: "accepted"
date: 2026-09-09
decision-makers: ekolvah
---

# Context Mode is not adopted for token efficiency

## Context and Problem Statement

The owner's goal is lower effective token spend for agent work in this
repository, and `mksglu/context-mode` was the named hypothesis: an MCP sandbox
that routes large tool payloads, persists session state in SQLite, and restores
it after compaction, advertising 96-98% "context savings". The scope evaluated
is a developer using the tool locally while working on this repository — not
shipping it with the process.

This record is Stage A: a static evaluation at a pinned snapshot, with nothing
executed. No `npm install` of the candidate ran, with or without
`--ignore-scripts`, and no hook, MCP server, or sandbox was started. The
artefact was obtained with `npm pack`, its published `dist.integrity` digest was
verified before unpacking, and its contents were read. Upstream claims and
locally observed results are separated throughout: what follows as evidence was
read in the verified tarball or in documentation that is cited.

## Considered Options

* **Adopt through a separate narrow issue** — requires that no stop condition
  fired, no open condition remains, a rollback path, and a named upgrade owner.
* **Retain for future re-evaluation** — the ceiling whenever a condition that
  cannot be closed statically is still open.
* **Not planned** — any one stop condition ends the evaluation here, with no
  pilot and no follow-up issue.

## Decision Outcome

Chosen: **not planned.** The first stop condition fired on the verified
artefact: the install path writes outside its own package directory, into the
agent configuration and plugin registration of the machine that would adopt it.
That is decisive on its own, and by the rule the evaluation set for itself it
ends the question without a pilot.

The other two stop conditions did not fire, and both are recorded rather than
omitted, because a condition that was checked and held is evidence a later
proposal can reuse. The two conditions that cannot be closed by reading — Codex
per-hook trust, and whether the host publishes per-session billed-token
categories — remain open; they would have capped the outcome at retention even
if nothing had fired, so no pilot could have been authorised from Stage A in any
case.

Nothing was adopted, installed, or configured as an outcome. Neither is the
candidate judged bad software: it is judged unfit for this repository at this
snapshot, on an install path that claims write authority over the same agent
configuration this process owns.

## Evaluation record

```text
snapshot-commit: 95b4e08bf07c5e16690d8669643f9d1b825d51be
snapshot-package: context-mode@1.0.169
snapshot-digest: sha512-94JIaFuLjF9SO2BsGTrbGtyT44K95+9OC8BdbaL/UT76xOkanJLfUR5CzmNw+GELXZQqH4nBrKg9wjBnSFkVnQ==
route: the Claude route carries navigation_policy.py through hooks.py PreToolUse alongside agent_policy.py and the ADR 0021 Stop gate; the Codex route carries agent_policy.py and the same Stop gate through codex_hooks.py but imports no navigation or read-budget hint, so it has no incumbent token-economy mechanism and the candidate-versus-incumbent framing does not hold there.
metric: the upstream 96-98% figure is a ratio of raw fixture bytes supplied to bytes returned per isolated tool call, with no billed-token category, no cache-read or cache-write accounting, no round-trip count, and no task-success rate, so it is never restated here as a token or cost saving; the document carrying it is in the upstream repository at the snapshot commit and is not part of the published package.
stop-1: fired — scripts/postinstall.mjs in the verified tarball resolves homedir() and writes outside its own package directory: it heals ~/.claude/settings.json enabledPlugins, rewrites ~/.claude/plugins/installed_plugins.json and its plugin cache, creates directory junctions at npm shim locations, and sweeps .mcp.json files it judges stale; CODEX_HOME and CONTEXT_MODE_DIR cannot bound a script that resolves the home directory itself.
stop-2: not-fired — Codex documents that "if more than one hook source exists, Codex loads all matching hooks. Higher-precedence config layers don't replace lower-precedence hooks", and that project-local hooks load when the project layer is trusted, so a user-level hook set installed under CODEX_HOME would run beside project-level .codex/hooks.json rather than displace the ADR 0021 Stop gate; on the Claude side the candidate's PreToolUse hook is deny- and modify-capable, which makes it a competitor to navigation_policy.py, not a replacement for it, and the Layer 1 deny-list is settings rather than a hook — reachable only through the settings writes already recorded under stop-1.
stop-3: not-fired — the one outbound path found in the artefact is hooks/platform-bridge.mjs, which POSTs sanitised hook events only when an operator-created config file supplies a ctxm_-prefixed key and a platform URL; without that file every event returns before a request is built, and no install script writes it. This is a read of a bundled build, which can show a gated path but cannot prove absence of egress at runtime.
licence: Elastic-2.0 restricts only providing the software to third parties as a hosted or managed service, circumventing licence-key functionality, and removing notices; it carries no copyleft, so local development use in this repository is unrestricted and the licence is recorded here as a fact rather than evaluated as a gate.
revives-if: a later issue proposes that the process itself ship, render, or require the package for consumer repositories — that shape, and only that shape, makes the licence a live question; separately, and not as a licence matter, the upstream's hosted Insight dashboard and commercial site are a business-model signal bearing on egress and on maintenance risk.
open-a: open — Codex gates hook execution behind a per-hook trusted_hash in $CODEX_HOME/config.toml computed by a private, unversioned algorithm with no supported non-interactive read path; this repository deliberately refuses to compute or infer it (check_codex_project_trust.py), so only an operator running codex interactively can confirm it.
open-b: open — whether the host exposes per-session input, cache-read, cache-write and output token categories was not established; the candidate reads adapter session databases and prices them from its own bundled model-prices.json, which presumes such categories rather than demonstrating that the host publishes them, and Stage A executed nothing that could observe one.
decision: not planned — stop condition 1 fired on the verified artefact, which by the rule this evaluation set for itself ends the question with no pilot and no follow-up issue.
rollback: nothing was installed or configured, so there is no machine state to undo; the change is this record, its rendered root copy, and one publisher test, and reverting the merge removes all three.
follow-up: none: a fired stop condition opens no follow-up. A future proposal starts from a new issue that re-verifies the install path at its own pinned snapshot and settles open-a and open-b before any runtime pilot is authorised, since a pilot whose billed-token categories are unavailable is pure token spend.
```

### Consequences

* Good, because the repository's agent configuration, plugin registration, and
  `.mcp.json` state stay under the process's own control.
* Good, because the byte-ratio claim is recorded as a byte ratio, so a later
  proposal starts from the measurement that was actually made.
* Bad, because the Codex route still has no token-economy mechanism at all, and
  this decision supplies none; that gap is unaddressed, not resolved.
* Neutral, because the snapshot is pinned: a later release with a bounded
  install path is a new evaluation, not a contradiction of this one.

### Confirmation

`tests/publisher/test_context_mode_evaluation_record.py` holds this record to
the pinned snapshot identifiers, a recorded verdict for every stop and open
condition, the raw-bytes versus billed-token distinction, and the internal
consistency between the verdicts and the decision — a fired stop condition
cannot stand beside an adoption, and a `not planned` outcome cannot claim a
follow-up issue. The rendered root copy is proved by
`tests/publisher/test_template_drift.py`.

## More Information

Working notes and the fetched tarball stay under Git-ignored `evidence/`; only
the summaries above enter this record. The Codex hook-layer rule is quoted from
the Codex hooks documentation at `https://learn.chatgpt.com/docs/hooks`
(retrieved 2026-09-09); every other statement of evidence was read in the
package whose digest is recorded above.
