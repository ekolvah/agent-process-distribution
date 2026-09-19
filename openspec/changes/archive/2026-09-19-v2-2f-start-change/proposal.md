## Why

Step 2d of the v2 plan (issue 107), the third of three changes the step was split into
(2026-09-19; the first is `v2-2d-check-red-test`, the second `v2-2e-wait-for-pr-checks`).
This change is the two new scripts that take the delivery order out of prose.

The delivery order lives in five copies (the `tasks` rule, every `tasks.md`, the
architecture page, the tests of the rule and the scripts) because the rule spells out shell
steps instead of naming a script: Group 0 of the `tasks` rule lists a `grep -q "^approve"`,
`gh issue view --json projectItems`, a `propose run not finished` stop, `gh issue develop
-c`, `set_status` and `gh issue comment`; the architect-review tail lists `gh issue
create`, `set_status --priority` and a `sed -i` over `tasks.md`. Each condition is prose
the agent evaluates, and the order is copied into every `tasks.md` and asserted by
`test_planning_workflow.py`. The retrospective of issue 137 (ADR 0027) found the same
shape in the review loop: every review found the copy that lagged, until
`resolve_review_thread.py` took the order.

Observations the design rests on:

- `gh issue develop --help`: "the new development branch will be created from the specified
  remote branch" — `--base` defaults to the default branch, so the branch starts from
  `origin/main` without a fetch step in the rule.
- `gh issue view 132 --json projectItems` returned
  `{"projectItems":[{"status":{"optionId":"…","name":"Todo"},"title":"…"}]}`; the Priority
  field of issue 132 reads `High` (GraphQL `fieldValueByName(name:"Priority")`).
- `gh issue create --help`: no `--json`; the command prints the issue URL, whose last path
  segment is the number.
- `set_status.py --help`: `set_status.py [-h] [--priority PRIORITY] issue [status]`.

## What Changes

- New `start_change.py <change> --planner --implementer`: the Group 0 gate as exit codes —
  verdict not `approve` → 2, `<N>` still in `tasks.md` or Status not `Planned` → 2 with
  `propose run not finished` — then `gh issue develop -c N --name <change>`,
  `set_status "In Progress"`, the provenance comment.
- New `create_tracking_issue.py <change> [--priority]`: the architect-review tail —
  `gh issue create` from `proposal.md`, `set_status "Planned" --priority`, the number
  written into `tasks.md`; on an existing number `set_status "Planned"` alone.
- `openspec/config.yaml` `tasks` rule: Group 0 names `start_change <change>`, the
  architect-review entry names `create_tracking_issue <change>`; the shell steps and
  conditions leave the rule; the person's parts (PR body, three rounds, the merge) stay
  prose. The agent runs no more steps than today.
- ADR 0027: "Native alternatives considered" rows for `start_change` and
  `create_tracking_issue`, with deletion conditions.
- `resolve_review_thread.py`, `archive_change.py`, `request_codex_review.py` were read and
  stay as they are: one mutation, one archive, one review request each.
- Tests and the architecture page follow the rule text.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `implementation`: "Delivery steps are tasks of every change" (Group 0 is `start_change`;
  its conditions are exit codes).
- `planning`: "Architect review is the last step of the propose run" (the tail is
  `create_tracking_issue`).

## Impact

Edited: `openspec/config.yaml`, `.agent-process/docs/architecture/agent-process.md`,
`.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
`tests/publisher/test_delivery_scripts.py`, `tests/publisher/test_planning_workflow.py`,
`openspec/specs/implementation/spec.md`, `openspec/specs/planning/spec.md` (by the
archive). Added: `.agent-process/scripts/start_change.py`,
`.agent-process/scripts/create_tracking_issue.py`. Removed: nothing. One PR (the rule text
and the scripts it names are one logical unit).
