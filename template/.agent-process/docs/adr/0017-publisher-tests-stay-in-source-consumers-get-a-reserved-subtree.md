---
status: "accepted"
date: 2026-08-30
decision-makers: ekolvah
---

# Publisher regression tests stay in the distribution source; consumers receive only target-dependent conformance tests, rendered under one reserved subtree

## Context and Problem Statement

Before this record, every process-related test file lived loose directly
under `tests/` (root copy) and `template/tests/` (template source), with no
structural marker separating two different kinds of test: publisher-only
tests that prove the template source, a reusable workflow, publication, or
this repository's own self-application (for example the drift gate's own
render-and-compare logic, or reusable-workflow pin checks), and consumer
tests that prove a rendered answer or a contract depending on the target
repository's own files (for example ADR-record structure, doc-link/anchor
validity, or branch-protection configuration). A copied production script was
not by itself justification for shipping all of its publisher unit tests, but
nothing enforced that distinction, so every `copier copy`/`copier update`
carried the full, undifferentiated set to every consumer. The same flat
`tests/` root also gave `copier update` no reserved space of its own: a
target repository's pre-existing, unrelated `tests/test_adr_records.py` (a
plausible product test name, coincidentally shared with a template path)
would collide with the template's own file at that path, invisibly to
Copier's `--conflict` handling, which only marks a conflict for a path it
previously tracked through a prior render's diff.

## Decision Drivers

* One reviewable classification rule, not a per-file judgment call repeated
  at every future test addition.
* A `copier update` must never silently overwrite a target repository's own,
  unrelated file.
* The self-hosting drift gate (this repository's own ADR 0013, not shipped to
  consumers) already declares root-only files one at a time, with its own
  `reason:`; the chosen shape must not need a directory-wide exemption that
  would hide a stray file dropped into the wrong place.
* No new tooling dependency beyond what `copier` and the existing drift gate
  already provide.

## Considered Options

* Flat layout kept, with a naming or prefix convention (e.g. `test_process_*`)
  marking publisher-only files by name instead of by location.
* Export the full, undifferentiated test suite to every consumer.
* Export no tests to consumers at all.
* Physical split: publisher-only tests live under `tests/publisher/` (never
  rendered); consumer tests originate under `template/tests/agent_process/`
  and render only below a reserved `tests/agent_process/` subtree — the one
  path a process test may occupy in a consumer's `tests/` root.

## Decision Outcome

Chosen: **the physical split**. Location, not a naming convention, carries
the classification, so `git ls-files tests/` and `git ls-files
template/tests/` answer "is this publisher-only or consumer" without reading
file contents or trusting a prefix nobody is forced to use correctly. The
reserved `tests/agent_process/` subtree gives `copier update` one narrow,
declared destination instead of the whole `tests/` root, so a pre-existing,
unrelated file elsewhere in a consumer's `tests/` tree can never collide with
a template path. `.agent-process/scripts/check_consumer_test_collision.py` renders the
current template against a target repository's own recorded answers and
reports any reserved-subtree path that already differs, closing the one gap
Copier's own `--conflict` handling leaves open. The drift-gate allowlist
still declares each publisher test file's own `root_only_paths` row with its
own `reason:` — never a directory-wide exemption — so a stray file dropped
into `tests/publisher/` still fails the gate as an undeclared extra file.

A naming convention was rejected: it is enforceable only by review discipline,
the same unenforced-convention gap [ADR 0011](0011-agentic-process-distribution-mechanism.md)
rejected a hand-rolled sync script for. Exporting the full suite was
rejected: it ships publisher-only assertions (this repository's own
self-application, its reusable-workflow pins) that cannot pass in a target
repository and were never meant to run there. Exporting no tests was
rejected: it silently drops the conformance coverage a target repository
needs to catch its own drift after later edits.

### Consequences

* Good, because the classification rule is physical and one-directional: a
  new test's directory decides its fate, with no separate manifest to keep in
  sync.
* Good, because `copier update` gets a narrow, collision-checkable
  destination instead of the whole `tests/` root.
* Bad, because every existing test file needed a `git mv` and, for the ones
  now one directory deeper, a fixed-depth root-path constant to update by
  hand — a one-time migration cost this record accepts rather than amortizes.
* Bad, because a future contributor can still place a publisher-only test
  under `tests/agent_process/` by mistake; the drift gate catches the
  reverse case (a stray file in `tests/publisher/`) but nothing rejects this
  direction beyond code review.

### Confirmation

In the distribution source repository, `tests/publisher/test_test_suite_ownership.py`
guards the physical split directly: every process test has exactly one owner,
publisher tests never render to a consumer, consumer tests render only under
the reserved subtree resolving correctly when nested, a flat-layout
consumer's `copier update` preserves its own unrelated tests while migrating
template-owned ones into the subtree, and a foreign file already occupying a
reserved-subtree path is visible to `.agent-process/scripts/check_consumer_test_collision.py`
before the update runs. This file itself is publisher-only and is not part of
a rendered consumer's own test suite; a consumer confirms the split holds for
its own repository by running `python -m pytest tests/agent_process`. Before
an update, the collision check itself runs from a distribution checkout, not
the consumer's own — a pre-split consumer does not yet have the script that
`copier update` is about to install.
Relates to [ADR 0011](0011-agentic-process-distribution-mechanism.md) (the
copier distribution mechanism this split rides on) and this repository's own
ADR 0013, not shipped to consumers (the drift gate whose per-file allowlist
declaration this split reuses without change) — this record narrows where
tests physically live, without changing either decision.
