## Context

See `proposal.md` — Why, and the `distribution` delta. `init.py` on `main` (issue 155)
classifies steps 1–8 from observed state, prints the plan, exits 2 on any `conflict` before
the first write, and applies the steps in order; a different version hands off after step 3,
so the requested release's own installer runs every consumer and remote step. Every
executable goes through `Context.call` (`shutil.which`, the injected runner). The
`state` spec's `The board is a copy of the template Project` fixes Project 4 and its five
built-in workflows; `set_status.py` needs exactly one Project linked to the repository.

Observations this design rests on (gh 2.87.3, 2026-09-23, token scopes `gist, project,
read:org, repo, workflow`):

- `gh repo view --json owner,name,projectsV2` printed
  `{"name":"agent-process-distribution","owner":{…,"login":"ekolvah"},"projectsV2":{"Nodes":[{"id":…,"title":"agent-process-distribution agent process","number":4,"resourcePath":"/users/ekolvah/projects/4","closed":false,"url":…}]}}`
  — linked Projects under `Nodes` (already on record in ADR 0027, v2-2a).
- `gh api graphql -f query='query($login:String!){repositoryOwner(login:$login){... on ProjectV2Owner{projectsV2(first:100){totalCount nodes{number title closed repositories{totalCount}}}}}}' -f login=ekolvah`
  printed `{"data":{"repositoryOwner":{"projectsV2":{"totalCount":2,"nodes":[{"number":4,"title":"agent-process-distribution agent process","closed":false,"repositories":{"totalCount":1}},{"number":1,…,"repositories":{"totalCount":1}}]}}}}`;
  the same query with `login=github` (an organization) printed `{"data":{"repositoryOwner":{"projectsV2":{"totalCount":16}}}}`.
  `gh project list --format json` carries `totalCount` but no linked repositories, so it
  cannot tell an unlinked copy from one linked elsewhere.
- `gh project copy --help`: `--source-owner`, `--target-owner`, `--title`, `--format json`;
  `gh project link --help`: "Link monalisa's project 1 to her repository "my_repo"" —
  `gh project link 1 --owner monalisa --repo my_repo`, the repository named under the
  Project's owner.
- `gh project view 4 --owner ekolvah --format json` printed `"public":true`; ADR 0027
  (v2-2a) records that `gh project copy` reads a user Project only when public, that the copy
  is private, unlinked, and keeps the source's enabled workflows, and that workflows are
  read-only in the API.

## Goals / Non-Goals

**Goals:** the Project phase is decided from remote reads in the same preflight as the local
steps, and every fault of its two commands — before or after the effect — is a test row.

**Non-Goals:** reading or migrating the copy's fields and Status (issue 114); verifying the
template itself (the `state` spec's `Template read`); a Project owned by someone other than
the repository's owner; deleting or unlinking a Project; a live copy from this PR.

## Decisions

### D1. Two transitions, last, in the one preflight

Steps 9 `project-copy` and 10 `project-link` follow `settings`. Their classification reads
the remote state during preflight, so an ambiguous remote state exits 2 before step 1 writes
anything, and a dry-run shows the same rows. Writes stay last: the local steps are idempotent
and complete first, and the remote writes run only after them.

Reads, both through `Context.call` in `root`:

1. `gh repo view --json owner,name,projectsV2` — owner login, repository name, linked
   Projects (`Nodes` or `nodes`, as `set_status.py` reads them).
2. only when read 1 shows no linked Project: the GraphQL query of Context with
   `login=<owner>` — the owner's Projects with `closed` and `repositories.totalCount`.
   `totalCount` greater than the nodes read is an `InstallError` (exit 1, before any write):
   the uniqueness of the title cannot be proven from a partial list. A repository with a
   linked board never issues it, so its reruns do not depend on the owner's Project count.

Alternative: classify only at apply time, as PR 151 did. Rejected: its ambiguity checks ran
after the local writes, and the plan could not show what the confirmed run would do.

### D2. Classification

`T = "<repository name> agent process"` — Project 4's own title for this repository (observed),
so the publisher's own run reads its board as linked. Candidates: the owner's Projects titled
exactly `T`; reusable: open with `repositories.totalCount == 0`.

| Linked | Same-titled candidates | `project-copy` | `project-link` |
|---|---|---|---|
| 1 | any | `unchanged` #N | `unchanged` #N |
| ≥2 | any | `conflict` naming them | `conflict` |
| 0 | none | `planned` copy of 4 as `T` | `planned` |
| 0 | exactly one reusable | `unchanged` #N | `planned` #N |
| 0 | several reusable | `conflict` naming them | `conflict` |
| 0 | only closed or linked elsewhere | `conflict` naming them | `conflict` |

The last row refuses rather than creating a second `T`, which would make the next run's
candidates ambiguous.

### D3. The commands and their recovery

- Copy: `gh project copy 4 --source-owner ekolvah --target-owner <owner> --title <T>`. Its
  output is not parsed: the copy's number is observed state, not a response.
- Link: re-read (D1, read 2), take the one reusable candidate — anything else is an
  `InstallError` naming what was found — then
  `gh project link <N> --owner <owner> --repo <name>`.

The target owner is the repository's owner because `gh project link` names the repository
under the Project's owner (help text above). Alternative `--target-owner @me`: for an
organization repository the board would be the user's and `--repo` would name a user
repository; unobserved and rejected.

Recovery follows from D2 alone: a copy that failed before its effect is `planned` again; one
that took effect is the reusable candidate (`unchanged`); a link that failed before its effect
is `planned` again with no copy; a link that took effect is the linked row. No local marker
records a remote write, so nothing local can disagree with GitHub.

Alternative: read the linked Projects back after `gh project link`. Rejected as redundant: a
non-zero exit is already an error, and the retry's read 1 is the proof the spec names.

### D4. Manual rows

The plan ends with two rows whose status is `manual` and which have no apply:

- `manual project-visibility: <Project URL or "the new copy">/settings — a copy is private; set its visibility as intended`
- `manual project-workflows: <…>/workflows — check Auto-add to project (this repository), Item added → Todo, Item reopened → Todo, Item closed → Done, Pull request merged → Done`

The workflow names are those of the `state` spec's template requirement. They are printed on
dry-run and confirm alike, and after a `conflict` too, so the preview is complete.

### D5. New input and what it takes away

The local lifecycle now needs `gh` on `PATH`, authenticated with `read:project` for the
reads and `project` for the writes, and a GitHub repository at `root`. Failure modes: `gh`
missing → `error: gh not found on PATH`, exit 1; unauthenticated, scope missing, or no GitHub
remote → the `gh` command's own message, exit 1. All occur in preflight, before any write.
No existing guard is dropped: `test_no_remote_write` proved "no `gh` at all" and its rename
(`test_only_project_writes_remote`) proves the narrower allowed set in this PR's `quality`
run.

### D6. Tests: a fake GitHub at the runner

`tests/publisher/test_init.py`'s `Runner` gains a `FakeGitHub` that answers the two reads in
the observed shapes above (`Nodes` capital, the GraphQL envelope), applies `copy` and `link`
to its Projects, and can inject per command `fail-before` (exit 1, no effect) or
`fail-after` (effect, then exit 1 — the lost response). It starts with template Project 4
owned by `ekolvah` and linked to the publisher. This is the process boundary (§II); nothing
inside `init.py` is replaced.

- The lifecycle and `test_retry_after_each_write` tables pick up the two labels through
  `on_write`; `_final` includes the fake's Projects and links, and `state_changing` keys
  `gh-copy` and `gh-link`, so each remote write is proven once across interrupt and retry.
- `test_project_states` is D2's table plus the truncated list, asserting rows, exit code, and
  an unchanged snapshot of `root`, `home`, and the fake on every conflict; its linked rows
  also assert that read 2 was never issued.
- `test_only_project_writes_remote` asserts that a fresh confirmed run issued exactly one
  copy and one link and no other GitHub write; `test_dry_run_writes_nothing_remote` asserts
  that a fresh dry-run issued both reads and no write. Both therefore fail on `main`, which
  issues no `gh` at all.
- `test_project_command_faults` is {copy, link} × {fail-before, fail-after}, asserting the
  copy and link counts across run and retry.

The fake cannot prove the live shapes. Task 3.2 (a dry-run in this repository, where Project
4 is linked) runs read 1 live; read 2's shape rests on the output recorded in Context, and its
first live run is issue 117's first real copy.

## Risks / Trade-offs

- [The fake drifts from gh] → its shapes are the cited outputs; the live dry-run of task 3.2
  exercises read 1 on this head, and read 2 runs live first at issue 117.
- [Unobserved: whether a fresh copy appears in read 2 at once] → if it lags, the link's
  re-read finds no candidate and the first install exits 1 at `project-link`; the retry
  reuses the copy (D3). Observed at issue 117's first real copy; no mechanism is added
  before then.
- [A concurrent run copies between preflight and link] → the link's re-read sees two
  candidates and stops with an error; the rerun reports the `conflict` for the person.
- [An owner with more than 100 Projects cannot install] → visible exit 1 naming the count;
  pagination is added when such an owner is observed.
- [A repository whose owner is not the person's account] → the copy needs project rights on
  that owner; gh's permission error surfaces, exit 1.

## Migration Plan

1. RED: the fake and the new tests; rename `test_no_remote_write`.
2. `init.py` D1–D4, then the `## Install` text; live read-only dry-run.
3. Strict OpenSpec validation and `python .agent-process/scripts/ci_check.py`; deliver under
   the unchanged workflow and review gate.
4. Rollback: revert the PR. It creates no Project; a consumer's copy made by a released
   installer stays the person's to delete.
