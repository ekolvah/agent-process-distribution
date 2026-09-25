## Context

See proposal.md (Why) for the search that found no caller. The v2 counterparts already
exist and are specified:

- `start_change.py` creates the linked branch with `gh issue develop -c <N> --name <change>`
  and sets `In Progress` (`implementation / Delivery steps are tasks of every change`).
- `set_status.py` resolves the Project, fields and options by name at run time
  (`state / Priority is set at creation`).
- The `quality` check reads `closingIssuesReferences` and fails a PR that links no issue
  (`.github/workflows/reusable-quality.yml`, `v2-2c`).

## Goals / Non-Goals

**Goals:** no v1 issue or state script remains, and no repository file stores Project, field
or option IDs.

**Non-Goals:** the retired installation guide, the PR template, `agent_orchestrator.py`,
`roles.yaml` and `copier-answers.yml` (issue 115). ADR 0020 stays as history, with no edits
(#107, Decisions). `set_status.py` keeps its behaviour.

## Decisions

**D1. The v1 branch and state scripts are deleted: `issue_branch.py`, `new_branch.py`,
`set_issue_status.py`, `set_issue_priority.py` and `project_settings.py`.**
- These guards stop being proven, each with the catcher that remains:
  - `project_settings.require_configured()`, the refusal to branch before activation. The
    catcher is `start_change.py`, which exits 2 with `propose run not finished` before any
    branch exists when the issue is not a Project item in `Planned`. `set_status.py` names
    zero or several linked Projects and changes nothing.
  - `is_valid_branch_name`, the `issue-N-<slug>` shape. Its only reader was the Stop gate,
    deleted in `v2-4a`. The branch name is `--name <change>`, which `start_change.py` passes.
  - The stored field and option IDs. They are resolved by name on every call, so there is no
    stored copy that can drift.
- Alternative: keep them until issue 115. Rejected, because a second, unused way to branch and
  set status is what the step removes, and nothing calls them.

**D2. The v1 PR-body scripts are deleted: `open_pr.py`, `update_pr_body.py` and
`check_orphan_scope.py`.**
- These stop being proven, each with its catcher:
  - The forced `Closes #N` line. The catcher is the `quality` check's `closingIssuesReferences`
    read on every PR head; the linked branch fills that field.
  - The generated `## Deferred scope` block. Nothing has read it since `v2-2c`
    (`agent-process.md`, `## Out of scope`), so no proof is lost.
  - The closing-reference re-verification after `gh pr create`. The same `quality` read covers
    it.
- Open PR 104 (`issue-101-…`, idle since 2026-09-12) keeps its own copies of the scripts on
  its head, and nothing on `main` calls them for it. A body edit there becomes
  `gh pr edit --body-file`. Closing or rebasing that PR is the person's decision.

**D3. The `state` requirement names `start_change`.**
- The behaviour exists: `start_change` exits 1 and names `set_status.py <N> "In Progress"` and
  the comment when the board write fails after the branch
  (`tests/publisher/test_delivery_scripts.py::test_interrupted_start_names_the_continuation`,
  green on `a04859a`). The text is realigned to that behaviour, so no RED test applies.

**D4. Prose.**
- `agent-process.md`: delivery step 4 loses the `open_pr.py` and `update_pr_body.py` sentences,
  and step 3 loses the v1 `issue-*` fallback. The `## Out of scope` paragraph is deleted, and so
  is the last sentence of governance item 5.
- `AGENTS.md` and `.claude/rules/workflow.md`: the activation sentence about
  `project_settings.py` and `issue_branch.py` points to `SKILL.md#install`.
- The `set_status.py` docstring no longer says that the duplicated helpers go in `v2-4`.
- ADR 0027 gains one Observations bullet: the caller search of the proposal and PR 104.

## Risks / Trade-offs

- [A v1 delivery in flight] → PR 104 is the only one, and D2 covers it.
- [A consumer still on v1 scripts] → The Copier mirror is gone (`v2-0b`), so no consumer gets
  these files from this repository. Issue 117 migrates the second consumer through `init`.
- Rollback: `git revert` of the PR. No external state changes.
