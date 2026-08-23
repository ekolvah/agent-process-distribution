# Agent-process installation

**Question this document answers:** How does a repository install and activate
the agent process before its first issue delivery?

This document describes the one-time repository setup. It is separate from
the [delivery flow](agent-process.md): installation prepares the repository;
delivery flow handles one issue at a time.

## Bootstrap exception

Until this payload is installed and its GitHub Project is activated, a
repository's first process-installation issues may create their branches and
publish their PRs manually. Those bootstrap changes must still state the issue
number and use the normal tests and review workflow. Once activation succeeds,
all later delivery uses `python scripts/issue_branch.py <N>`; do not retain a
manual-branch bypass as a second process.

## CI prerequisites

The payload installs three thin caller workflows. They reference the published
reusable workflows pinned in `workflow_references`; Python enforcement scripts
remain copied because they are parameterized by the target's answers and also
run locally. Before the first PR, configure the carrier-1 repository secret
`CLAUDE_CODE_OAUTH_TOKEN`, install the Codex GitHub connector, and ensure the
organisation permits this publisher under its Actions "Allow specified actions
and reusable workflows" policy. A missing credential is deliberately a red
review check, not a skipped job.

Enable the copied local pre-push probe after reviewing it:

```bash
git config core.hooksPath .githooks
```

The caller permission grants (`contents: read`, `pull-requests: write` for
review) are part of the published contract. A release that requires a wider
callee permission is breaking until callers are re-rendered.

## Workflow-definition trust

Thin callers are part of the PR head. Classic branch protection matches a
check's displayed name, so it cannot prove that a PR did not replace a caller
with a different job that reports the same name. Before treating these checks
as a security boundary, configure an organisation or platform trust anchor
that requires the intended workflow definition (for example, a Ruleset
Required Workflow where that GitHub feature is available). Do not switch these
review workflows to `pull_request_target` as a shortcut: the review carrier has
a credential and reads untrusted PR material. Until an external anchor is
configured, required contexts remain delivery evidence, not proof that an
untrusted contributor ran the publisher's policy.

## Activation

`copier copy` copies the payload but does not create or alter GitHub resources.
The copied process is inactive until its GitHub Project is configured. Run:

```bash
python scripts/bootstrap_github_project.py --confirm-create
```

In `existing` mode, bootstrap reads the selected Project and verifies that it
has `Priority` (`High`, `Medium`, `Low`) and either `Agent status` or `Status`
(`Planned`, `In Progress`). It writes no configuration until all checks pass.

In `create` mode, `--confirm-create` is an explicit approval for the remote
write. Bootstrap checks GitHub authentication, creates a Project, links the
repository, and adds the required fields. If a later setup operation fails,
it deletes the Project created in that invocation. If deletion also fails, it
prints the exact `gh project delete` command for the maintainer.

On successful activation bootstrap atomically writes
`scripts/project_settings.py`. Review and commit that file. It contains the
real, repository-owned Project and field IDs that every process runner uses.

## Updating the process

Run `copier update` from the target repository and review both the copied
scripts and the referenced workflow tag/SHA. This release changes required
contexts to GitHub's composed `caller / callee` names, so after updating run
the activation/protection step again; existing v0.1.x protection otherwise
points at contexts that no workflow publishes.

## Incomplete activation

If bootstrap exits with an error, the process remains inactive: its prior
settings file is unchanged and `python scripts/issue_branch.py <N>` stops
before creating a branch. Correct the reported GitHub access, Project number,
or field configuration, then rerun bootstrap. Do not edit IDs by hand.
