---
status: "accepted"
date: 2026-09-27
decision-makers: ekolvah
---

# Release PRs merge without the person

## Context and Problem Statement

[ADR 0030](0030-releases-go-through-release-please.md) kept the release PR manual: the person
linked an issue, requested `@codex review` and merged. On #202 `quality` failed in 3 s on
"links no issue", `agent-review` waited for a review nobody requested, and fixes reached no one
until the person remembered (#203). Each of those steps re-gates content already linked and
reviewed in the `feat`/`fix` PRs the release collects.

## Considered Options

* Recognise the release PR by its diff; exempt it from the link and the review wait; enable
  auto-merge from the release workflow
* Recognise it by its file set, branch name or author
* Keep the manual steps of ADR 0030

## Decision Outcome

Chosen: **recognise the release PR by its diff, exempt it, and let auto-merge merge it.**

* **D1 — the diff.** `.agent-process/scripts/release_pr.py` reads `release-please-config.json`
  and `.release-please-manifest.json` at the base (a PR cannot widen the set it is judged by).
  A release PR changes only the config's `extra-files`, the manifest and the changelog; the
  manifest changes a version; every changed file but the changelog is `modified`, has as many
  lines as its base, and each line equals its base line or that line with each `old → new`
  version replaced (issue 260: release-please rewrites only the version places, so a comment
  keeping the old version must pass). A compare listing 300 files (the API's limit) is
  not a release PR. A repository without the config has no release PR.
* **D2 — one script from the trusted source.** `quality.yml` job `link` and
  `reusable-agent-review.yml` check out this repository at `job.workflow_sha` (issue 226: the former name was never set) and run the
  script there, publishing `release=true|false` and printing why. A failed read exits 2 and
  fails the step. On a release PR `link` skips the issue check, and `agent-review` skips the
  Codex wait, so the Claude fallback and its verification do not run either; the tests
  (`plan`, `check`) and the P0/P1 thread enforcement run as on every PR.
* **D3 — what stops proving.** The issue link: the changelog entries name the `feat`/`fix` PRs,
  each linked on its own head. The review: D1 passes only lines unchanged or changed by the
  version; a version place left unbumped fails `test_version_drift`, which runs in `check` on
  the same head. The person's look at `CHANGELOG.md`
  before the tag: nothing replaces it, so a wrong but valid type (`docs` on a behaviour change)
  shows in the release notes after the release and the next `fix` corrects it.
* **D4 — auto-merge.** `release-please.yml` runs `gh pr merge --auto --squash` on the PR the
  action created or updated (`prs_created`), with `RELEASE_PLEASE_TOKEN`. The required contexts
  decide the merge. The repository allows auto-merge (`allow_auto_merge=true`, set once by the
  person); without it the step fails red and the person can still merge.

### Consequences

* Good, because a merged `feat`/`fix` becomes a tagged release within minutes, with no step of
  the person.
* Good, because a PR that changes anything beyond version strings meets every gate, and the
  step log names the file.
* Bad, because the release has no pause: consumers are protected only by #199's gate.
* Bad, because it is unobserved whether the auto-merge commit starts the `push` workflow that
  tags the release; the symptom is a merged release PR and `gh release view v<version>`
  failing.

### Pros and Cons of the Options

* File set, branch or author — `init.py` is code and `plugin.json` declares hooks, both in the
  set; the branch name and the PAT identity are pushable by anyone with write.
* The manual steps — the stall of #202, repeated on every release.

### Deletion condition

Remove the exemption, the detection steps and the auto-merge step when releases leave
release-please.

### Confirmation

`tests/publisher/test_release_pr.py` holds D1 and the published verdict;
`tests/publisher/test_reusable_workflows.py::test_quality_skips_the_link_on_a_release_pr`,
`::test_agent_review_skips_the_review_on_a_release_pr` and
`::test_release_workflow_enables_auto_merge` hold D2 and D4. The first release after this ADR
is the live check of D4.
