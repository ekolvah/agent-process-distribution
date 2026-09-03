---
status: "accepted"
date: 2026-08-23
decision-makers: ekolvah
---

# CI workflow logic is referenced, while target Python enforcement is copied

## Context and Problem Statement

The process declared required branch-protection contexts but shipped neither
workflows nor the manifests and hook those checks needed. Copying Actions YAML
through Jinja would duplicate CI logic for every consumer and make `${{ }}`
expressions part of the template escaping contract. A composite action cannot
declare the job that GitHub branch protection requires, while a template
repository has no maintained update path.

## Considered Options

* Copy complete YAML workflows through Copier.
* Use a composite action.
* Use a GitHub template repository or an organisation `.github` repository.
* Publish reusable workflows and retain thin target callers.
* Package the Python enforcement scripts.

## Decision Outcome

The source repository publishes called-only reusable workflows. A Copier
answer carries each complete `uses:` reference; the target renders one caller
per required context. GitHub composes a called run name as `caller / callee`,
so those names are the protection declaration and are observed on a source PR
before protection is enabled. Offline checks validate the caller key and
state the unresolved callee composition explicitly.

References were originally pinned to a recorded commit SHA — a trust anchor
against a PR that edits its own review/CI logic and is validated by that same
edited logic before anyone notices. Issue #72 dropped that pin in favour of
`@main`, both for this source repository's own three callers and for the
`copier.yml` default every downstream adopter inherits on a fresh `copier
copy` (an existing consumer's `copier update` reuses its already-recorded
`workflow_references` answer, so it keeps a persisted SHA until that answer
is explicitly refreshed): the SHA had to be
bumped by hand on every `reusable-*.yml` change and nothing enforced that the
bump land in the same PR, so it silently went stale (observed in #64/PR#66,
where a stale pin kept failing every subsequent PR's `pr-link` check until
#70/#71 caught it) — and a same-PR bump cannot fully close that gap by
construction, since the SHA to pin to is that PR's own not-yet-existing merge
commit. `caller/repo@ref` always resolves `ref` against the target repo, never
against the calling PR's own branch content, whether `ref` is a SHA or `main`
— so a PR editing a `reusable-*.yml` file could never govern the review of
that same PR under either scheme. What the SHA pin bought was a manual
checkpoint: a change landed on `main` needed its SHA deliberately copied into
the callers before it governed *any* PR, giving a human a chance to notice in
that bump commit. Under `@main`, the same change governs every PR opened
after it merges, with no separate bump step to notice it at — accepted as a
narrow residual risk for this repository's single-committer trust model, in
exchange for eliminating an entire class of recurring drift bugs. This is a
repository-specific tradeoff, not a retraction of the pin as a valid trust
anchor for a multi-committer or adversarial-contributor context: a fresh
adopter now starts on `@main` and must consciously re-pin to a SHA in their
own `workflow_references` answer if their trust model needs it.

The target still copies Python. `check_branch_protection.py` is rendered from
target answers and `review_gate.py` also runs locally, so publishing it as a
foreign workflow dependency would split one enforcement contract. The review
caller maps the carrier secret explicitly and grants the published permission
contract; the callee may restrict but cannot escalate that grant. No conditional
secret guard is permitted: an unavailable carrier must red the required check.

### Consequences

* Good, because reusable workflow fixes have one home. `pr-link`/`quality`
  callers and this repository's own `agent-review` caller track `@main`
  directly (issue #72); a target that keeps a SHA pin still moves it through
  a reviewed update.
* Good, because the workflow keeps its default-branch contract and enforcement
  scripts in an isolated trusted checkout while it reviews the PR-head
  worktree. This protects an invoked callee, not the PR-head caller that
  invokes it.
* Bad, because organisations may block external reusable workflows and every
  target must provision the named credential before its first review.
* Bad, because changing composed context names or callee permissions is a
  breaking release for existing callers.
* Bad, because classic name-only required contexts do not authenticate their
  caller workflow. A PR can replace that caller and still publish the same
  context name. A target needs an external workflow-definition trust anchor
  before it treats these contexts as a security boundary; this payload does not
  use `pull_request_target`, because the review carrier has a credential and
  consumes untrusted PR material.

### Confirmation

Source tests parse callee schemas, caller-to-callee inputs/secrets and both
permission sides; rendered-suite tests execute the formerly skipped workflow
and hook checks. A live source PR records GitHub's actual composed run names
before #7 activates branch protection.
