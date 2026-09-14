## Context

Split from `v2-1-planning-workflow` (PR 121 reached the three-round review cap; the rework
concentrated on the prose rules, so scripts land first, on their own). Verified on OpenSpec
1.13.0 and `gh` on this machine:

- A Codex review is requested by comment (`request_codex_review.py --request <PR>`), is not
  visible in `reviewRequests`, and the v1 `agent-review` required check waits for it before
  it concludes; it must be re-requested after every push, as the check binds to the head.
- The rollup of a new head is empty for a few seconds, then every workflow run attaches at
  once; a fast check can conclude before the others attach. Required contexts are not
  readable without admin.
- `openspec archive -y` leaves `openspec/changes/archive/.openspec-archive.lock` after a
  successful archive on Windows: `releaseArchiveClaim` compares `dev`/`ino` and `fs.lstat`
  reports `dev = 0` (Node v22.14.0), so the unlink is skipped. Upstream fix: Fission-AI/OpenSpec
  pull request 1769 (open).
- `check_red.py` takes pytest paths and spawns pytest (`[--full] path…`).

## Goals / Non-Goals

**Goals:** four scripts an apply loop can call without judgement, each with a visible failure
mode. **Non-Goals:** the `tasks` rule that places them (`v2-1b`), the review and state
rework (`v2-4`), removing the v1 twins (`v2-4`).

## Decisions

- **`wait_for_pr` trusts a concluded rollup only when two consecutive polls of the same
  head list the same checks.** An empty rollup or a running check is "pending"; threads are read only after
  that. Exit 0: nothing unresolved; 1: failed checks or unresolved threads printed;
  3: `--timeout` (default 30 min). Alternative: read the required contexts — needs admin.
- **`set_status.py` resolves the Project from the issue's own item, else from the single
  Project linked to the repository.** An issue whose item sits in a Project the repository
  does not link is an error naming both sides, not a silent fallback. Helpers are duplicated
  from `set_issue_status.py`/`set_issue_priority.py` on purpose: those die in `v2-4`.
- **`finish_change` closes the loop itself.** The apply skill marks a task after running it,
  and `openspec archive` moves `tasks.md`; so the last task is one script that marks its own
  box first. It refuses a worktree that is not clean and an existing lock (exit 2) and removes the lock a
  successful archive leaves (upstream defect above; the removal branch goes when a pinned
  release contains the fix).
- **`check_red --report` reuses the runner's verdict.** A node id selects testcases by
  `classname`/`name`; a node id ending in a class selects every test of that class, nested
  classes included. `AGENTS.md` declares the runner and the report path; nothing else is
  required of the runner.
- **`None` capture is an error**, per `AGENTS.md`: every `subprocess.run` wrapper raises
  before it looks at the return code.

## Risks / Trade-offs

- [Codex has no Stop hook] → `wait_for_pr` is the only end guard; observed on Claude here.
- [Pagination of Projects beyond 20] → visible `ValueError`, not a wrong Project; deferred.
- [Lock removal masks a future real abort] → the removal runs only after a successful
  `archive`; an abort still leaves the lock and the next run exits 2.

## Migration Plan

One PR; the change archives as its last commit through `finish_change`; the person merges.
Rollback: revert the PR.
