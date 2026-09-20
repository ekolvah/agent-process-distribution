## Context

See proposal.md — Why. GitHub Actions run `35523639249` for the issue-112 pull request ended with
`startup_failure` and zero jobs. The head caller passed `setup` and `test` to
`reusable-quality.yml@main`; the default branch's callee has no `workflow_call.inputs`
because the new interface is part of the same unmerged PR.

## Goals / Non-Goals

**Goals:** make the publisher's initial v2 PR runnable while retaining immutable tagged
callees for every installed consumer.

**Non-Goals:** changing consumer templates, creating the release tag before merge,
weakening the quality ruleset, or adding a second quality workflow.

## Decisions

The publisher caller uses `./.github/workflows/reusable-quality.yml`; the consumer
template continues to use
`ekolvah/agent-process-distribution/.github/workflows/reusable-quality.yml@v2.0.0`.
GitHub resolves the local reusable workflow from the same commit as its caller, which
allows the first release PR to compile and exercises the callee that the PR changes.

The publisher therefore does not receive the consumer callee's immutable-ref proof. The
actual catcher is the existing terminal inspection of every `.github/workflows/**` diff
on the settled head, followed by the person's merge decision. The required ruleset still
binds `quality / quality` to GitHub Actions integration `15368`.

Keeping `@main` was rejected because GitHub validates passed inputs against the old
default-branch interface before creating jobs. Creating or moving `v2.0.0` before merge
was rejected because the release tag is immutable and person-owned after merge. A
temporary branch or prerelease ref was rejected because it would leave the merged
publisher caller dependent on a mutable or disposable ref.

## Risks / Trade-offs

- [A publisher PR can edit both caller and callee] → the settled-head workflow diff is a
  mandatory human inspection and the limitation is explicit in the archived design and
  PR report.
- [A local reusable syntax error still prevents the required context] → GitHub exposes a
  startup failure; the delivery loop reads Actions runs when the status rollup is empty.

## Migration Plan

Change only the publisher caller and its contract test, amend the archived issue-112
design and scenario map, validate the delta, and archive it in pull request 151. Rollback restores
`@main`, but that also restores the reproduced startup failure until the new reusable
interface exists on `main`.
