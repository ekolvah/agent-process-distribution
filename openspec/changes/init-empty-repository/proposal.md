## Why

`init` cannot install into a repository with no commits, the state of a repository created
without "Add a README" (#271). Its dry-run prints a conflict whose hint names an empty branch:

```
conflict onboarding-branch: on `main`, not ``; `git switch `, then rerun
```

Observations (2026-09-30, private probe repositories `ekolvah/agent-process-empty-probe-1`
and `-2`, created empty):

- `gh repo view --json defaultBranchRef,isEmpty` → `{"defaultBranchRef":{"name":""},"isEmpty":true}`;
  `gh api repos/<repo> --jq .default_branch` → `main`.
- A clone of it: `git branch --show-current` → `main`, `git status --porcelain` → empty,
  `git rev-parse --verify --quiet HEAD` → exit 1 (unborn).
- Pushing another branch first makes it the default: after `git push -u origin probe-head`,
  `defaultBranchRef.name` → `probe-head`. `gh pr create --base main --head probe-head` →
  `GraphQL: … Base ref must be a branch (createPullRequest)`, exit 1. The REST reference states
  `base` "should be an existing branch on the current repository"
  ([Create a pull request](https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request)).
- Pushing a commit of the empty tree (`git write-tree` of the clean unborn checkout →
  `4b825dc6…`, `git commit-tree`) to `refs/heads/main`, then `git switch -c
  agent-process/install-probe origin/main`, one commit, push: `defaultBranchRef.name` → `main`,
  `rev-list --count origin/main..HEAD` → `1`, `gh pr create --base main` → a PR opened, exit 0.

Root cause: the installation PR needs an existing default branch as its base, and a repository
with no commits has none; `_repository()` (`init.py:641`) passes the empty `defaultBranchRef.name`
on, and `_unsafe_start` (`onboarding.py:104`) formats it into a hint written for "another branch
is checked out". Reproduction: the RED test's fixture, an `origin` with no refs and a fake
`gh repo view` returning that empty name.

## What Changes

- In a repository with no commits, `init` plans a new step `onboarding-root`: one commit with no
  files pushed to the default branch named by the repository's settings, the installation branch
  then created from it. Everything the installer writes still reaches the default branch only
  through the installation PR.
- A repository with no commits whose checkout has commits, and a checkout with no commits of a
  repository that has some, are `onboarding-branch` conflicts naming the command that resolves
  each. No conflict line names an empty branch.
- **Changes an invariant:** *Init's remote writes are the Project and the installation PR* allows
  that one push to the default branch, in a repository with no commits only.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: *Init's remote writes are the Project and the installation PR* (the initial
  commit's push) and *Init opens the installation PR* (installing into a repository with no
  commits; the two new unsafe starting points).

## Impact

- Edited: `skills/agent-process/scripts/onboarding.py` (`Target.empty`, the `onboarding-root`
  step, the start point of the branch, the two conflicts), `skills/agent-process/scripts/init.py`
  (the settings read of the default branch when `defaultBranchRef.name` is empty; module
  docstring: step list, conflicts, the default-branch sentence), `tests/publisher/init_harness.py`
  (`FakeGitHub`: `default_branch`, `api repos/<repo>`, a `pr create` base that must exist on
  `origin`), `tests/publisher/test_init_remote.py` (the empty-repository test, three `UNSAFE` rows,
  the no-empty-name assertion, `_gh_kind`, `_git_state` of an unborn checkout),
  `openspec/specs/distribution/spec.md` (through the archived delta).
- Added / removed: none. No ADR: the exception is local to `init` and recorded in design.md D1.
- Outside the repository: the probe repositories above stay until the person deletes them.
