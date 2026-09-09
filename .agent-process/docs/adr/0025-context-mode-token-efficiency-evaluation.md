---
status: "accepted"
date: 2026-09-09
decision-makers: ekolvah
---

# Context Mode is retained until a token baseline exists

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

One ruling shapes the outcome and is recorded because it is the owner's, not the
evaluation's. The install path's reach beyond its own package directory is a
**coexistence problem to be designed once a saving is shown**, not a gate that
ends the question before one is measured: the agent-process architecture is
itself expected to change, and a mechanism that demonstrably lowers spend is
worth designing around. What Stage A therefore owes is not a verdict on the
installer but an honest account of what the installer does and of whether the
saving can be measured at all.

## Considered Options

* **Adopt through a separate narrow issue** — requires that no stop condition
  fired, no open condition remains, a rollback path, and a named upgrade owner.
* **Retain for future re-evaluation** — the ceiling whenever a condition that
  cannot be closed statically is still open.
* **Not planned** — any one stop condition ends the evaluation here, with no
  pilot and no follow-up issue.

## Decision Outcome

Chosen: **retain for future re-evaluation.** No stop condition fired on the
verified artefact, and one open condition remains, which caps the outcome below
adoption exactly as the evaluation's own rule requires.

The install path is the condition that came closest and is the one worth stating
plainly, because the reach is real and the bound is also real. Every heavy write
into the machine's agent configuration sits behind a guard that a local install
inside this Git working tree does not pass; what runs unconditionally is narrow
and stays within a cache directory the package already owns. That is a bounded
install path, not an unbounded one, so the condition does not fire — and the
residual write authority is carried forward as a coexistence requirement for any
runtime pilot rather than as an ending.

What is not yet known is whether there is a saving at all. The upstream figure
is a byte ratio and cannot answer it. Both hosts do publish per-session
billed-token categories on local disk, so the question is measurable without
installing anything — that is the one open condition Stage A could close, and
issue #94 turns it into a baseline, a best-case ceiling, and a threshold fixed
before the numbers are read.

Nothing was adopted, installed, or configured as an outcome, and nothing here
authorises a pilot: Codex per-hook trust is still unresolved, and a pilot whose
result cannot be scored is pure token spend.

## Evaluation record

```text
snapshot-commit: 95b4e08bf07c5e16690d8669643f9d1b825d51be
snapshot-package: context-mode@1.0.169
snapshot-digest: sha512-94JIaFuLjF9SO2BsGTrbGtyT44K95+9OC8BdbaL/UT76xOkanJLfUR5CzmNw+GELXZQqH4nBrKg9wjBnSFkVnQ==
route: the Claude route carries navigation_policy.py through hooks.py PreToolUse alongside agent_policy.py and the ADR 0021 Stop gate; the Codex route carries agent_policy.py and the same Stop gate through codex_hooks.py but imports no navigation or read-budget hint, so it has no incumbent token-economy mechanism and the candidate-versus-incumbent framing does not hold there.
metric: the upstream 96-98% figure is a ratio of raw fixture bytes supplied to bytes returned per isolated tool call, with no billed-token category, no cache-read or cache-write accounting, no round-trip count, and no task-success rate, so it is never restated here as a token or cost saving; the document carrying it is in the upstream repository at the snapshot commit and is not part of the published package. The unit this decision needs is a billed-token category measured on this repository's own sessions, which issue #94 produces: a hand count over a single local session placed cache reads at roughly two thirds of converted session cost, output next, fresh input negligible — the shape that would make an offloading mechanism plausible, but one session priced with unconfirmed multipliers, recorded here as a reason to measure rather than as a result.
stop-1: not-fired — the install path does reach outside its own package directory, and it is bounded. In scripts/postinstall.mjs at the verified snapshot every heavy write — healing ~/.claude/settings.json enabledPlugins, rewriting ~/.claude/plugins/installed_plugins.json and its plugin cache, sweeping .mcp.json files judged stale, normalising hook registrations, and rewriting npm .cmd shims — sits inside an isGlobalInstall() guard that returns false whenever npm_config_global is not "true" or a .git directory is found within four levels above the package root, which is precisely the shape of a local install in this working tree; the author's comment gives keeping contributors' local installs from rewriting their HOME registry as its purpose. What runs unconditionally is narrow: one step re-creates a junction or symlink only for paths already registered under the context-mode@context-mode key beneath ~/.claude/plugins/cache/, refusing any target that does not resolve inside that cache root, and a native-binding heal that stays inside the package directory. The condition asks whether the install path can be bounded by available means; a local, non-global install inside this Git working tree bounds it, so it does not fire. The residual write authority over the agent configuration this process owns is carried forward as a coexistence requirement for any runtime pilot, on the owner's ruling that the agent-process architecture will itself change and that a demonstrated saving is worth designing around.
stop-2: not-fired — Codex documents that "if more than one hook source exists, Codex loads all matching hooks. Higher-precedence config layers don't replace lower-precedence hooks", and that project-local hooks load when the project layer is trusted, so a user-level hook set installed under CODEX_HOME would run beside project-level .codex/hooks.json rather than displace the ADR 0021 Stop gate; on the Claude side the candidate's PreToolUse hook is deny- and modify-capable, which makes it a competitor to navigation_policy.py, not a replacement for it, and the Layer 1 deny-list is settings rather than a hook — reachable only through the global-install settings writes recorded under stop-1, which a local install does not perform.
stop-3: not-fired — the one outbound path found in the artefact is hooks/platform-bridge.mjs, which POSTs sanitised hook events only when an operator-created config file supplies a ctxm_-prefixed key and a platform URL; without that file every event returns before a request is built, and no install script writes it. This is a read of a bundled build, which can show a gated path but cannot prove absence of egress at runtime.
licence: Elastic-2.0 restricts only providing the software to third parties as a hosted or managed service, circumventing licence-key functionality, and removing notices; it carries no copyleft, so local development use in this repository is unrestricted and the licence is recorded here as a fact rather than evaluated as a gate.
revives-if: a later issue proposes that the process itself ship, render, or require the package for consumer repositories — that shape, and only that shape, makes the licence a live question; separately, and not as a licence matter, the upstream's hosted Insight dashboard and commercial site are a business-model signal bearing on egress and on maintenance risk.
open-a: open — Codex gates hook execution behind a per-hook trusted_hash in $CODEX_HOME/config.toml computed by a private, unversioned algorithm with no supported non-interactive read path; this repository deliberately refuses to compute or infer it (check_codex_project_trust.py), so only an operator running codex interactively can confirm it.
open-b: closed — both hosts publish per-session billed-token categories on local disk, so a pilot can be scored rather than guessed. The Claude route writes one JSONL per session under ~/.claude/projects/<repo-slug>/ whose assistant messages each carry usage with input_tokens, cache_creation_input_tokens, cache_read_input_tokens and output_tokens; the Codex route writes rollout-*.jsonl under ~/.codex/sessions/ whose token_usage_record events carry input_tokens, cached_input_tokens, cache_write_input_tokens, output_tokens and reasoning_output_tokens at turn and thread level. 53 Claude transcripts and 118 Codex rollouts for this repository already exist, so the baseline is computable with nothing installed; a reader must not sum the Claude iterations array on top of the message-level usage, nor Codex turn totals on top of thread totals.
decision: retain for future re-evaluation — no stop condition fired and the install path is bounded for local use, but open-a is unresolved, which caps the outcome below adoption; the candidate is held, uninstalled and unconfigured, pending the measurement that decides whether a saving exists at all.
rollback: nothing was installed or configured, so there is no machine state to undo; the change is this record, its rendered root copy, and one publisher test, and reverting the merge removes all three. Retention adds no runtime surface of its own: if the measurement finds no saving, this record is re-recorded as not planned in place, and no rollback beyond that edit is owed.
follow-up: #94 measures the per-category token baseline of this repository's existing sessions and the best-case ceiling of the offloading mechanism against a threshold fixed before the numbers are read; a runtime pilot stays unauthorised until that ceiling clears the threshold and open-a is resolved.
```

### Consequences

* Good, because the question the owner actually asked — is there a saving — is
  now a measurement with a named issue and a pre-committed threshold, instead of
  an unexamined claim on either side.
* Good, because the byte-ratio claim is recorded as a byte ratio, so the
  measurement starts from the unit it needs rather than from the vendor's.
* Good, because the install path is recorded as it is: reaching, but bounded by
  a guard whose condition a local install in this working tree does not meet.
* Bad, because retention keeps an unresolved condition alive: `open-a` can be
  closed only by an operator running `codex` interactively, and until then no
  pilot is authorisable however good the ceiling looks.
* Bad, because the Codex route still has no token-economy mechanism at all, and
  this decision supplies none; that gap is unaddressed, not resolved.
* Neutral, because the snapshot is pinned: a later release changes what the
  install path does and is a new reading, not a contradiction of this one.

### Confirmation

`tests/publisher/test_context_mode_evaluation_record.py` holds this record to
the pinned snapshot identifiers, a recorded verdict for every stop and open
condition, the raw-bytes versus billed-token distinction, and the internal
consistency between the verdicts and the decision — a fired stop condition
cannot stand beside an adoption, an unresolved open condition cannot stand
beside one either, and a retained outcome must name a tracked follow-up issue
rather than trailing off. The rendered root copy is proved by
`tests/publisher/test_template_drift.py`.

## More Information

Working notes and the fetched tarball stay under Git-ignored `evidence/`; only
the summaries above enter this record. The Codex hook-layer rule is quoted from
the Codex hooks documentation at `https://learn.chatgpt.com/docs/hooks`
(retrieved 2026-09-09); every other statement of evidence was read in the
package whose digest is recorded above, or in this machine's own session files,
which were read locally and never transmitted.
