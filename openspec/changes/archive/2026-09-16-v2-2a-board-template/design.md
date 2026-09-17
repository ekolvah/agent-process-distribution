## Context

See proposal.md — Why. Constraints that shape the approach:

- GitHub exposes Project workflows read-only: `ProjectV2.workflows { name enabled }` in
  GraphQL, no mutation and no `gh` command; enabling one is a UI action. Single-select
  options are editable only through `updateProjectV2Field` with the whole option list
  (ids, colors, descriptions) or the UI.
- `gh project copy` copies a Project of another owner only when the caller can read it; a
  consumer under another owner needs Project 4 public. `markProjectV2AsTemplate` exists
  for organization Projects only; a user Project is copied as is.
- `gh repo view --json projectsV2` returns the linked Projects as `{"projectsV2":
  {"Nodes": [{id, number, title, …}]}}` — capital `Nodes`, observed on gh 2.87.3.
- `set_status.py` is imported by `tests/publisher/test_delivery_scripts.py` through a
  fake `gh` callable keyed on the command's first three words (§II); the script's public
  seam is `set_status(number, status, *, priority, gh)` and `main(argv, *, gh)`.
- Project 4 is private and already carries `Planned` (v1 wrote it after plan approval,
  ADR 0024); `openspec/config.yaml` `rules` are the extension point OpenSpec keeps across
  `openspec update`, and the architect review already runs from there as the last step of
  the propose run.

## Goals / Non-Goals

**Goals:**
- The process writes two Statuses (`Planned` at the end of propose, `In Progress` at the
  start of apply) and one Priority; every other transition is a GitHub workflow, verified
  once on the template and recorded.
- One observation settles what `gh project copy` carries before `init` (#112) is designed.

**Non-Goals:**
- Any script that enables workflows or edits options (no API; the person does it once).
- Restricting the Status names `set_status.py` accepts: the rules call it with `Planned`
  and `In Progress`, the script resolves any option by name as before.
- A gate on `Planned`: `/opsx:apply` by the person is still the approval; the column is
  visibility, and task 0.1 still reads the verdict file.
- Touching the v1 board scripts or the installation guide (#115).

## Decisions

1. **The Project is the one linked to the repository, read with `gh repo view`.**
   `_lookup` (GraphQL) and `_project_for` (membership by Project id) are replaced by one
   `gh repo view --json owner,name,projectsV2` call: exactly one linked Project is the
   board; zero or several → `ValueError` naming them (exit 2, nothing written). The
   issue's URL comes from `gh issue view <N> --json url`. Alternatives: keep the membership
   branch (an issue on a foreign board) — it guarded a case *Auto-add* removes (every issue
   of the repository is an item of the linked Project) and `item-add` on an existing item
   is a no-op returning the same id, so the branch and its two tests go (§VII);
   `gh project list --owner` — lists the owner's Projects, not the repository's link.

2. **Status becomes an optional positional; at least one of Status/Priority.**
   `set_status.py <N> ["In Progress"] [--priority <name>]`; `main` exits 2 with the usage
   when both are absent. `set_status(number, status=None, *, priority=None, gh)` writes
   only the fields given, all names resolved before the first write as today. Alternative:
   a second script for priority — one more file for one fewer argument.

3. **The template is verified by a read, not asserted by a test.** The Verify group runs
   one `gh api graphql` query (`public`, `fields { name options { name } }`,
   `workflows { name enabled }`) against Project 4 and the task compares it with the
   spec's list; the output is pasted into ADR 0027. Tests run offline and must not depend
   on GitHub state (§II); a script for a one-time check is a script without a second run.

4. **The observation is one task with two confirmed remote writes.** `gh project copy …
   --title scratch --format json` (returns the new number), the same GraphQL read on the
   copy (`fields`, `views { name }`, `workflows`), then `gh project delete <n> --owner
   @me`. The person confirms before the copy and before the delete (shared state under
   their account). What the copy lacks is what `init` (#112) must print as a checklist.

5. **Visibility and workflow edits on Project 4 are the person's, in the UI:** set
   visibility public, enable *Auto-add to project* (this repository, open issues and PRs),
   *Item reopened → Todo*, and confirm the three already enabled. The agent's task is the
   read of decision 3 before and after, so the diff is visible in the PR's ADR observation.
   Alternative: `gh project edit --visibility PUBLIC` from the agent — possible for one of
   the four edits only; one route for all four is simpler to follow.

6. **`Planned` is written by the propose run through the `tasks` rule, not by a hook or a
   schema.** The architect-review entry of `rules.tasks` ends with: on `approve`, the
   tracking issue exists (else ask the priority, `gh issue create --title "<change>"
   --body-file openspec/changes/<change>/proposal.md`), then `set_status.py <N> "Planned"
   --priority <P>`; the propose run ends there. Group 0 becomes: verdict → `gh issue
   develop -c <N>` → `set_status.py <N> "In Progress"` → provenance. Alternatives: a
   forked schema artifact (rejected in `v2-1e` — `openspec update` stops following it); a
   Claude hook on the review file (Claude-only, Codex has none); a Project workflow (none
   triggers on a file or a branch). The `planning` spec already places the review in this
   rule, so the status write is one more sentence of the same entry, and
   `test_planning_workflow.py` proves the order (`approve` before `"Planned"`, `gh issue
   create` in the review entry and absent from Group 0).

7. **ADR 0027 is appended, not edited.** Records are immutable after acceptance
   (`maintenance` spec); the earlier steps appended observation paragraphs and so does
   this one. The `set_status` row stays; the observation states what it did not know:
   built-in workflows set `In Progress` too, but only when a pull request is linked — the
   process needs it at delivery start, before a PR exists — so the deletion condition
   (a native trigger at that point) is not met.

## Risks / Trade-offs

- [Making Project 4 public exposes its items' titles and fields] → the repository and its
  issues are public already; draft items are not copied (`--drafts` off).
- [`gh project copy` needs the `project` scope on the person's token] → `gh auth status`
  is read in the observation task; a missing scope is the printed `gh auth refresh -s
  project` line, not a retry.
- [The `Nodes` key of `gh repo view --json projectsV2` may change case in a later gh] →
  the reader accepts `Nodes` and `nodes`, and the fake in the tests uses the observed form.
- [Auto-add sets `Todo` on every new PR as well as issues] → intended: PRs on the board
  move to `Done` on merge by the same workflows; the filter is the person's choice in the
  UI and recorded in the ADR.
- [A change proposed without an issue gets one from the planner, with a body of the
  proposal] → the same command the apply used until now, moved one step earlier; the
  person is asked the priority once, as before.
- [`Planned` is a custom option a consumer's copy must carry] → observed in decision 4;
  if the copy drops it, `init` (#112) prints it with the workflow checklist.
