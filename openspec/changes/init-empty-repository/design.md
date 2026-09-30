## Context

See proposal.md — Why for the observations. `init` reads the default branch once, in
`_repository()` (`init.py:641`), from `gh repo view`, and hands it to `onboarding.Target.default`;
every onboarding hint, the `origin/<default>` of `_commit_step` and the PR's `--base` read that
field. `onboarding.plan` classifies the starting point before any write; any conflict makes
`init` exit 2 before the first write (`init.py:888`); a confirmed run applies the planned steps
in order (`_perform`).

## Goals / Non-Goals

**Goals:** a clean clone of a repository with no commits installs through the same PR as any
other repository; every starting point `init` cannot use names a command that resolves it.

**Non-Goals:** installing into a repository without a GitHub `origin`; files in the initial
commit (a README or `.gitignore` of the installer's choosing).

## Decisions

### D1 — Create the base, not a refusal (person's decision, 2026-09-30)

In a repository with no commits, `plan` returns a step `onboarding-root` before
`onboarding-branch`. Its apply commits the empty tree — `git write-tree` of the unborn checkout,
whose index is empty because the worktree is clean — with `git commit-tree -m "Initial commit"`,
pushes that commit with `git push origin <sha>:refs/heads/<default>`, and runs
`git fetch origin <default>`. The installer's files then reach the default branch only through
the installation PR, as in any repository.

Alternatives:
- A conflict asking the person to push an initial commit (the first plan of #271): rejected by
  the person — every install into a fresh repository would stop at a manual step.
- Push the installation branch first: it becomes the default branch (proposal — Why, probe-1),
  and the installer's files land without the PR.
- Commit the installer's files directly to the default branch: they skip the review.
- `git commit --allow-empty` on the unborn branch: runs the consumer's commit hooks and leaves a
  local branch named by the local `init.defaultBranch`, which may differ from the settings name.

Dropped guard (SKILL.md — Design): "the installer SHALL NOT commit to or push the default
branch" now has one exception.
- What stops proving: that the default branch is unchanged, in a repository with no commits.
- Failure modes: the default branch gains a commit between plan and apply; the push goes to a
  name other than the settings' default.
- Catchers: the plan creates `onboarding-root` only when `defaultBranchRef.name` is empty; the
  push has no `+` and no `--force`, so git refuses it if the branch appeared in between — observed
  on a local bare `origin` whose `main` has a commit: `git push origin <root>:refs/heads/main` →
  `! [rejected]        8ed2b66… -> main (non-fast-forward)`, `error: failed to push some refs`,
  exit 1 — and `Context.call`'s `check=True` (`init.py:309-312`) raises `InstallError`, which
  `install` prints as `error: …` and exits 1; `onboarding-root` is the first applied step, so
  nothing was written before it. The empty-repository test asserts the pushes of the run are
  exactly the root commit to `refs/heads/<settings name>` (one commit, the empty tree, no parent)
  and the installation branch; `test_remote_writes_are_project_and_pr` keeps asserting the single
  push in a repository with commits.

### D2 — The default branch's name comes from the repository's settings

When `defaultBranchRef.name` is empty, `init` reads `gh api repos/<owner>/<name>` and uses its
`default_branch` (observed `main` on the empty probes); `Target.empty` records the case. A
missing or empty `default_branch` is an unexpected shape: `InstallError`, exit 1, before any
write. So no hint and no command receives an empty name.

Alternatives: the checkout's unborn branch name — it comes from the local `init.defaultBranch`,
and a push of a different name becomes the default (probe-1); `isEmpty` in the `repo view`
fields — a second signal for the fact the empty name already carries, and it names no branch.

### D3 — The installation branch starts from `origin/<default>` in the empty case

`onboarding-branch` runs `git switch --no-track -c <branch> origin/<default>` after
`onboarding-root` (probe-2: the PR then opens), and `git switch -c <branch>` from `HEAD`
otherwise, as today. `_commit_step`'s `origin/<default>` resolves because the root step fetched it.

### D4 — Three starting points of the empty case are conflicts

In the empty case `plan` does not compare the checked-out branch with `to.default`: an unborn
branch has no commits to lose and cannot be switched to the settings name (`git switch <name>`
exits 1 while `origin/<name>` does not exist), and D3 starts the installation branch from
`origin/<default>` whatever is checked out. The empty case checks, in order:

- `origin` has no commits and the checkout has: a root would not share their history. Hint:
  `` `origin` has no commits and the checkout has; `git push -u origin HEAD:<default>`, then rerun ``.
- `origin` has commits and the checkout has none (also the rerun after a root push whose later
  steps failed): `` the checkout has no commits; `git pull origin <default>`, then rerun ``
  (verified: `git pull origin main` into an unborn clone exits 0 and checks out `main`).
- `origin` has no commits and the worktree has changes: `git stash` needs a commit, so the hint
  is `` the worktree has changes and the repository has no commits; move them out of the worktree, then rerun ``.

`test_unsafe_starting_point` asserts, for every row, that the conflict line has no empty code
span (`` `` ``).

### D5 — The fake GitHub follows the observed shapes

`FakeGitHub` gains `default_branch` (`"main"`, the settings name `api repos/<repo>` answers) and
`empty` (`False`; `True` makes `repo view` print the empty `defaultBranchRef.name`), and its
`pr create` exits 1 when `--base` is not a branch on `origin`, as `Base ref must be a branch`
does. An empty `origin` is the standard sandbox with `refs/heads/main` deleted on `origin`,
`empty = True` and `default_branch = "trunk"`; an empty repository adds the deletion of
`refs/heads/main` and `refs/remotes/origin/main` in the clone — the refs of a clone of an empty
repository, whose unborn branch stays `main`. The settings name differs from the checkout's
branch on purpose: the tests then fail for the alternative D2 rejects and for a `current`
check D4 drops.

## Risks / Trade-offs

- [GitHub changes the empty-repository shapes] → a different `repo view` shape already fails
  `_repository()` as unexpected; a missing `default_branch` fails D2's read; both before any write.
- [The consumer has no git identity] → `git commit-tree` fails like today's `git commit` of the
  installation, before the push.

## Migration Plan

None: a new plan step in `init` for a state it refused before; rollback is the revert.
