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
answer carries each complete `uses:` reference pinned to the recorded release;
the target renders one caller per required context. GitHub composes a called
run name as `caller / callee`, so those names are the protection declaration
and are observed on a source PR before protection is enabled. Offline checks
validate the caller key and state the unresolved callee composition explicitly.

The target still copies Python. `check_branch_protection.py` is rendered from
target answers and `review_gate.py` also runs locally, so publishing it as a
foreign workflow dependency would split one enforcement contract. The review
caller maps the carrier secret explicitly and grants the published permission
contract; the callee may restrict but cannot escalate that grant. No conditional
secret guard is permitted: an unavailable carrier must red the required check.

### Consequences

* Good, because reusable workflow fixes have one home and move through a
  reviewed tag/SHA update.
* Good, because enforcement restores a default-branch checkout after reviewing
  the head, preserving ADR 0004's residual-trust compensation.
* Bad, because organisations may block external reusable workflows and every
  target must provision the named credential before its first review.
* Bad, because changing composed context names or callee permissions is a
  breaking release for existing callers.

### Confirmation

Source tests parse callee schemas, caller-to-callee inputs/secrets and both
permission sides; rendered-suite tests execute the formerly skipped workflow
and hook checks. A live source PR records GitHub's actual composed run names
before #7 activates branch protection.
