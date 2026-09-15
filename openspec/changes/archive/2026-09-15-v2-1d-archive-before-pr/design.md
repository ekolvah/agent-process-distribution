## Context

Verified on OpenSpec 1.13.0 and on the three PRs of the previous step (#122–#124):

- `openspec archive -y` moves the whole change directory to
  `openspec/changes/archive/<date>-<change>/` (`moveDirectory`), `tasks.md` included; after
  it `openspec status --change <name>` and `instructions apply` no longer know the change.
- The required `agent-review` check binds to the head SHA; `request_codex_review.py` must
  follow every push until `v2-4` replaces the review.
- `gh issue develop -c` creates the branch on GitHub first, so a plain `git push` from the
  branch reaches it before any PR exists.
- On those PRs the Deliver ticks (4.2 with the round notes) were committed into the
  archived `tasks.md` by hand after `finish_change` — the reviewer never saw them.

## Goals / Non-Goals

**Goals:** the head the review reads is the archived one; no push after the last review
round; the Deliver ticks live in the archived `tasks.md`.

**Non-Goals:** the head-bound check itself (`v2-4`); the review budget; the unfork of the
schema (#126); a priority-only mode of `set_status` (the Claude adapter's `"Todo"` for an
issue created outside an apply run stays — that run has not started).

## Decisions

- **Archive is a Deliver task before the PR, not the last task.** Order: worktree clean →
  `archive_change` → `gh pr create` → review request → `wait_for_pr` loop. Alternative: keep
  the archive last and accept the extra round until `v2-4` — rejected, the archived state
  must be what the reviewer approved, whatever the check does.
- **The tasks after the archive are ticked in the archived `tasks.md`.** The archive commit
  is the first commit the PR shows; every later tick and review-round note is a later commit
  on the same PR (what #122–#124 did by hand). A re-run of the apply on an open PR reads
  `openspec/changes/archive/<date>-<change>/tasks.md` — one sentence in the `tasks` rule, no
  script: `openspec status` cannot track an archived change and a second tracker is a
  second home. Alternative: archive after the review loop but before the last push
  (`finish_change` marks, archives, then one push) — still a push after the last review.
- **`finish_change.py` → `archive_change.py`, shrunk.** Marks its own task, archives,
  removes the lock, commits, pushes; no review request, no `wait_for_pr` (those follow as PR
  tasks the agent runs). Renamed because a "finish" that runs before the PR is a false name
  (§IV). `_mark_own_task` matches the whole task item (its continuation lines included):
  the command sat on the second line of task 4.3 (#124) and the first-line regex left it
  unticked (ticked by hand in `c89e485`).
- **Priority before `gh issue create`** (#123 review): Group 0 asks first, then creates the
  issue, then `set_status "In Progress" --priority`; no later delivery task prompts.

## Risks / Trade-offs

- The PR tasks are not tracked by OpenSpec after the archive; an interrupted run must find
  the archived `tasks.md`. Mitigation: the rule names the path; `wait_for_pr` blocks the run
  until reviews are in, so an interruption is the exception.
- An archive commit on a branch whose PR is never opened — harmless: the branch is deleted
  or the PR opens later from the same head.
- A review fix after the archive edits code, not the change: the archived artifacts stay
  as approved; the round note in `tasks.md` records what the fix was (as now).
