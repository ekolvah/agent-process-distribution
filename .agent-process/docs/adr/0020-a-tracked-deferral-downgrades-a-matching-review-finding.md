---
status: "accepted"
date: 2026-09-02
decision-makers: ekolvah
---

# A tracked, gate-verified deferral downgrades a matching review finding

## Context and Problem Statement

`agent-review` audits the whole file a PR touches, not the PR's diff, and has
no memory across PRs. When a PR lands code that carries known, deliberately
deferred findings — split into a separate issue because
`verify_pr_link.py` forces one issue per PR — the reviewer re-reports them as
`BLOCKING` on every round, because no channel tells it what was deferred and
where. Observed on PR #63 (issue #59): two of three `BLOCKING` findings in its
fourth review round were near-verbatim re-reports of findings already raised
on PR #57, already carved into issue #61, and already documented in #61's own
body. PR #63 spent 4 review rounds and its full fixer budget, and escalated to
the maintainer with a green local CI.

A hand-written pilot (`## Deferred scope` section added by hand to PR #63's
body, review re-triggered on an unchanged head) proved the *data* channel
works — the PR body reaches both carriers — but the *rule* is missing: the
reviewer re-reported all three findings verbatim as `BLOCKING` anyway (run
`33623988547`, attempt 2), because neither `AGENTS.md` nor
`REVIEW_CONTRACT.md` told it that a declared deferral changes anything.

## Considered Options

* Tune the reviewer down generally (e.g. instruct it to be less strict about
  re-flagging). Rejected: the reviewer's findings were accurate; the defect is
  missing scope context, not excess precision.
* Teach the reviewer to fetch the linked tracking issue itself at review time.
  Rejected: neither carrier's issue-read capability is verified (the Claude
  fallback's tool grants, the Codex primary's native review scope), and a
  review that silently cannot fetch degrades to today's behaviour with no
  visible signal.
* Add a new required issue section (e.g. `## Known open findings`) as the
  deferral source. Rejected: a ninth-plus required heading on every issue of
  every class, to serve a rare case, is not worth its token cost; a
  `deferred:` marker on the existing `## Out of scope` section restores
  "cannot be triggered by accident" without one.
* Generate a sentinel-delimited `## Deferred scope` PR-body block from the
  linked issue's `deferred:`-marked `## Out of scope` bullets, verify the
  block is gate-sound against the issue, and add one gate-verified,
  one-directional exception to `REVIEW_CONTRACT.md`'s "never from PR-body
  text" rule.

## Decision Outcome

Chosen: **generate, verify, and judge** — three parts, one per trust
boundary:

1. **Generate.** `open_pr.py` (create and already-open-PR paths) and
   `update_pr_body.py` render a `<!-- agent-process:deferred-scope -->`
   sentinel-delimited `## Deferred scope` block from the linked issue's
   `## Out of scope` bullets that opt in with a literal `deferred:` prefix —
   not any bullet that merely mentions a tracking issue number, since the
   section is a severity-downgrade licence and a false positive weakens a
   gate (`check_orphan_scope.deferred_scope_bullets`). Each entry carries the
   tracker's number, title, and bounded acceptance-criteria bullets, so a
   generic tracker title alone is never relied on for matching. A closed
   tracker is omitted and reported on stderr rather than silently kept.
2. **Verify.** The required `pr-link` check
   (`verify_pr_link.deferred_scope_mismatch`) verifies every entry in the
   PR body's block is currently backed by an open `deferred:` bullet in the
   linked issue — soundness, not byte-equality, so a benign retitle or reword
   of the tracking issue does not red a merge-ready PR. `reusable-pr-link.yml`
   and its callers gain `issues: read`; a `DEFERRED_SCOPE_CHECK_SUPPORTED`
   marker (same shape as `PUBLISH_PR_COMMENT_SUPPORTED`) lets the workflow
   notice, not silently no-op, when the trusted default-branch checkout
   predates the check.
3. **Judge.** `REVIEW_CONTRACT.md` gains one coherent rule, replacing the
   contract's previous absolute "never from PR-body text, which this contract
   already forbids as merge authority": a finding that matches, with high
   confidence, a gate-verified `## Deferred scope` entry may downgrade by
   exactly one severity step (`blocking`→`should-fix`, never upgrade, never
   dropped) — an uncertain match, a missing section, or no corresponding entry
   all leave the finding at its default severity. `reusable-agent-review.yml`'s
   prompt gains a one-line pointer to this rule, since the pilot showed a
   plausible data channel changes nothing without one, and the contract's
   near-neighbour rule ("do not re-raise a finding already answered by a
   correct recorded rationale") did not fire on its own.

Rejected alternatives above are recorded with their reasons rather than left
implicit, per this repository's own review-contract discipline for scope
decisions.

### Consequences

* Good, because a deliberately deferred, already-tracked finding no longer
  costs a full review round on every PR that carries it.
* Good, because the verification step is soundness-checked against live issue
  state, so the exception cannot silently rot into an unconditional downgrade
  license as the linked issue's wording drifts.
* Good, because the rule is fail-closed by construction: any uncertainty
  (missing section, unmatched entry, ambiguous match) resolves to the
  reviewer's default, unmodified severity.
* Bad, because generation, verification, and the contract rule are three
  separate surfaces that must stay coupled by hand; a future edit to one
  without the others reintroduces the pilot's exact failure mode (data
  present, rule absent, or rule present, data unverified).
* Bad — **residual risk, stated plainly.** This gate raises the forgery cost
  from "edit the PR body" to "edit the PR body *and* the linked issue" — it
  does **not** make the downgrade unforgeable. The same author who opens the
  PR can also edit the linked issue's `## Out of scope` section to add a
  `deferred:` bullet backing whatever finding they want downgraded, and the
  `pr-link` check would find it sound. This is the same authority level this
  process already grants an issue everywhere else (an issue's body is
  self-authored, trusted input to planning and delivery); this decision does
  not raise or lower that trust level, it only extends where it applies.

**Assumption and rollback.** Assumes both review carriers, once instructed,
apply the downgrade rule as specified — matched entries downgrade by exactly
one step, unmatched or uncertain findings do not. Falsification signal:
criterion 8 of issue #64 requires re-triggering `agent-review` on a PR
carrying a generated block after this ADR's contract change reaches `main`,
and recording the run id, resulting severities, and which carrier answered.
If the observed behaviour diverges from the rule (over-downgrades, or still
fails to downgrade a sound match), revert the contract clause and keep only
the generate/verify halves inert until the rule wording is revised.

### Confirmation

`tests/publisher/test_deferred_scope.py` and the three new nodes in
`tests/publisher/test_reusable_workflows.py`
(`test_pr_link_grants_issues_read`,
`test_pr_link_feature_detects_deferred_scope_support`,
`test_agent_review_prompt_points_at_the_contract_rule`) cover generation,
verification, and the workflow wiring. The contract rule itself has no test
node — `REVIEW_CONTRACT.md` prose cannot be pytest-verified — which is why
criterion 8's live re-trigger, recorded in issue #64 after this merges, is not
optional: it is the only observation that closes the exact gap the pilot
exposed. Relates to
[ADR 0015](0015-owner-requested-codex-primary-with-claude-fallback.md) (Codex
primary / Claude fallback carrier split, both bound by this rule) and
[ADR 0016](0016-review-gate-blocks-on-narrow-simplicity-violations.md) (the
contract's existing narrow, worktree-verifiable exception pattern that this
decision extends into gate-verified PR-body data).
