---
status: "accepted"
date: 2026-09-27
decision-makers: ekolvah
---

# The review gate is installed in every consumer

## Context and Problem Statement

`reusable-agent-review.yml` had one caller, this repository's own `agent-review.yml`, so a
consumer installed by `init.py` had no review check, and activation required
`agent-review / agent-review` only where the caller happened to exist (#215). The review gate
of the process reached no consumer.

## Considered Options

* Install a managed review caller in every consumer and require its context unconditionally
* Merge the caller and the reusable review into one installed workflow
* Keep the review optional per consumer

## Decision Outcome

Chosen: **install a managed review caller in every consumer and require its context.**

* **D1 — the caller.** `init.py` renders `templates/agent-review.yml` into
  `.github/workflows/agent-review.yml` as step `review`, after `workflow`, under the
  `# agent-process:managed` first line: `pull_request` `[opened, synchronize]`, the permissions
  the callee needs, `uses: …/reusable-agent-review.yml@v<version>` with no inputs, and the
  consumer's `CLAUDE_CODE_OAUTH_TOKEN` passed as `claude_code_oauth_token`. An existing file
  without the marker is a `conflict`.
* **D2 — the secret.** `init` never reads or writes a secret; its plan ends with a
  `manual review-secret:` row naming the repository's secrets page and
  `CLAUDE_CODE_OAUTH_TOKEN`.
* **D3 — activation.** `activate_protection.py` refuses (exit 2) when the default branch lacks
  the review caller, naming the file, and always requires both `agent-process / quality` and
  `agent-review / agent-review`. This is breaking: a consumer installed before this ADR reruns
  `init`, sets the secret and merges the result before activation succeeds.

### Consequences

* Good, because every installed consumer has the same review gate as this repository.
* Good, because a missing secret is visible: the install PR's `agent-review` is red and
  activation refuses, instead of a repository that silently has no review.
* Bad, because a consumer needs a Claude token before its first protected merge.

### Pros and Cons of the Options

* One merged workflow — rejected by the person; a `pull_request` run takes the workflow file
  from the PR, so a PR could rewrite the review steps it is judged by.
* Optional review — the state of #215: a consumer can be protected with no review at all.

[ADR 0020](0020-a-tracked-deferral-downgrades-a-matching-review-finding.md),
[0022](0022-the-fixer-resolves-the-thread-its-correction-addresses.md) and
[0031](0031-release-prs-merge-without-the-person.md) stay valid: they describe the callee,
which is unchanged.

### Deletion condition

Remove the review caller, its `manual` row and the activation requirement when the process
stops depending on a review check.

### Confirmation

`tests/publisher/test_init.py::test_review_caller_render`,
`tests/publisher/test_init_conflicts.py::test_conflict_fails_closed[review-unmanaged-*]`,
`tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed` and
`::test_installed_footprint_is_closed` hold D1 and D2;
`tests/publisher/test_activate_protection.py::test_review_caller_absent` and the ruleset tests
requiring both contexts hold D3.
