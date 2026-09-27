## Context

`start_change.py` creates and checks out the linked branch in the checkout it runs in
(`gh issue develop -c`). The propose run leaves `openspec/changes/<change>/` untracked in that
checkout. With one checkout per repository, a second agent's Group 0 moves the first agent's
branch and files (proposal **Why**).

## Goals / Non-Goals

**Goals:** two changes are carried at once in one repository without touching each other's
files until their PRs meet on `main`.

**Non-Goals:**
- Isolating the propose run. It writes only its own untracked `openspec/changes/<change>/`;
  two proposes on the shared checkout do not collide, and once every apply runs in its own
  worktree the shared checkout stays on `main`.
- State outside git: the GitHub Project, the issue, `~/.agent-process/`. Two changes on one
  issue are already refused by the `Planned` gate.
- Deleting the local branch of a merged change: the repository forbids force-deleting a
  branch (AGENTS.md), and a squash-merged branch is not "merged" for `git branch -d`.
- Ignoring `.claude/worktrees/` in consumers. The worktree's own `git status`, which
  `archive_change` reads, does not see it; the shared checkout shows it as untracked, a
  visible and harmless listing. Revisit on an observed problem.

## Decisions

**D1 — The branch is created without checkout, then carried in a worktree.**
`gh issue develop N --name <change>` (no `-c`, proposal **Why**: `-c` is what checks out),
`git fetch origin <change>`, then `git worktree add --track -b <change>
.claude/worktrees/<change> origin/<change>`. The explicit `--track -b … origin/<change>`
instead of git's remote-name guessing: guessing depends on exactly one remote matching.
Precondition: a clone with git's default fetch refspec. Observed by the architect review in
probe repositories (git 2.45.1): with `+refs/heads/*:refs/remotes/origin/*` the fetch prints
`* [new branch] mychange -> origin/mychange` and the add prints `branch 'mychange' set up to
track 'origin/mychange'`; in a `git clone --single-branch --branch main` the fetch prints only
`mychange -> FETCH_HEAD` and the add fails `fatal: invalid reference: origin/mychange` (exit
128), and even after an explicit `git fetch origin mychange:refs/remotes/origin/mychange` it
fails `fatal: cannot set up tracking information; starting point 'origin/mychange' is not a
branch`. The process does not support single-branch clones: the failure is exit 1 naming the
steps left (D4), after the remote branch exists — visible, never silent.
The worktree base is the **main** worktree, not the cwd: a session that carried the previous
change is still inside its worktree when it starts the next one. The main worktree is the
first `worktree` entry of `git worktree list --porcelain`, listed from any linked worktree
(observed by the architect review, git 2.45.1); its paths print with forward slashes on
Windows, so paths are compared resolved (`Path(...).resolve()`), never as string prefixes.
The change's files still move from the cwd, where the gate read them. The listing is read
once, after the gate and before any GitHub write; if it fails, the start exits 1 naming the
error before `gh issue develop` — without it there is no base, and `git worktree add` would
fail on the same git.
`.claude/worktrees/` because `EnterWorktree` requires a registered worktree and, when the
session is already in a worktree, one under `.claude/worktrees/` (tool description, proposal
**Why**). All git and gh calls go through the injected `gh` runner, as `ls-remote` does today.
Alternative rejected: keep `-c` and let the agent `EnterWorktree name=<change>` — that tool
creates its own branch from `origin/main`, unlinked from the issue, so the merge would not
close it.

**D2 — The change's planning files move into the worktree.** After the worktree exists,
`openspec/changes/<change>/` of the running checkout is moved to the same path in the
worktree (`shutil.move`). Only that directory: another change's directory and any other
edit stay where they are. Nothing about the gate changes — it reads the files before the move.

**D3 — Group 0 enters the worktree; later tasks run there.** The `ok:` line prints the
worktree path; SKILL.md Group 0 says to enter it with `EnterWorktree` (its `path`) and run
every later task there — `check_red`, `ci_check`, `archive_change`, `gh pr create` resolve
their root from the cwd (`ROOT = Path.cwd()`), so they act on the worktree unchanged.
`pyproject.toml`'s `pythonpath = [".agent-process", "."]` is relative, so tests import the
worktree's code; no editable install exists to point elsewhere.

**D4 — Failure after the branch exists names the worktree steps.** The existing `left` list
becomes: `git fetch origin <change>`, `git worktree add …`, the move, `set_status … "In
Progress"`, `gh issue comment …`; each step that succeeds is dropped, so the message starts
with the one that failed. `git switch <change>` disappears from the script and the resume
text: resuming before the archive is `EnterWorktree` with the worktree path.

**D5 — Every `start_change` removes the worktrees of merged changes.** The merge is the
person's and happens after the run ends, so no step of that run can clean up; the next
change's start is the process's next entry point in the same repository. After the gate and
before `gh issue develop`, `start_change` reads `git worktree list --porcelain`, and for each
worktree under the main worktree's `.claude/worktrees/` with a `branch` line (a detached one
has none and is left), except the worktree that contains the cwd — it may hold the plan
the gate just read and D2 is about to move, and on Windows it is locked as the cwd; it is
left for a later start from elsewhere — it asks `gh pr view <branch> --json state`.
On `MERGED` with an empty `git -C <path> status --porcelain` it runs `git worktree remove
<path>` and prints `removed: <path>`; on `MERGED` with a dirty tree, or when the remove fails
(Windows: a process holds a file), it prints `kept: <path> — <reason>` on stderr and goes on;
any other state (`OPEN`, `CLOSED`) and "no pull requests found" (a change before its PR) are
left untouched. A cleanup failure never blocks the start: it is a visible line, not a gate. (The listing is not cleanup: its failure stops the start, D1.)
Why the PR state and not git: observed on this repository (`gh api
repos/ekolvah/agent-process-distribution --jq '{delete_branch_on_merge,allow_squash_merge,
allow_merge_commit}'` → `{"allow_merge_commit":false,"allow_squash_merge":true,
"delete_branch_on_merge":false}`) — a squash merge is not an ancestor for `git branch
--merged`, and the remote branch is not deleted, so "upstream gone" never fires.
`gh pr view batch-secrets-scan --json state,headRefName` → `{"headRefName":
"batch-secrets-scan","state":"MERGED"}`; `gh pr view no-such-branch-xyz --json state` →
`no pull requests found for branch "no-such-branch-xyz"`, rc 1. `CLOSED` unmerged is kept:
abandoning the work is the person's call. Alternative rejected: a SessionStart hook — a second
entry point with its own install path in consumers, for the same effect one step earlier.

## Risks / Trade-offs

- A move that fails half-way (Windows file lock) leaves files in both places; D4 names the
  move as the step left, and the gate files are still readable in the source.
- D5 removes the worktree of a merged change even if an idle session still has it as cwd;
  that session's work is merged, and it sees a missing directory, not lost work (a dirty
  tree is kept).
- A person who resumes with `git switch` in the shared checkout hits git's own refusal
  ("already checked out at …") — visible, not silent.

**Migration / rollback:** changes already in progress keep their in-place branch; the new
script applies from the next `start_change`. Rollback is reverting the PR.
