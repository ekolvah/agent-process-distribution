## Why

`agent-process / quality` now reports on PRs, but no process step makes it required. The
frozen PR [151](https://github.com/ekolvah/agent-process-distribution/pull/151) put the
ruleset upsert inside `init`, so one local command also wrote live protection before any
PR had shown the required context. Its run `35523639249` created zero jobs, and a strict
context that never reports blocks every merge. Root cause: activation depended on a context
it did not first observe. This change makes activation its own command. It writes only after
it observes the caller on the default branch and the context on a real PR head
([issue 154](https://github.com/ekolvah/agent-process-distribution/issues/154), parent 112).

Observations (commands and output in `design.md`, Observations):

- Ruleset `23732345` is the repository's only ruleset. It is active on `refs/heads/main` with
  no bypass actors, and it has the rules deletion, non-fast-forward, pull request, and strict
  `quality / quality` from integration `15368`.
- Classic protection still requires `quality / quality` and `agent-review / agent-review`.
  Issue 112 says that PR 151 removed the second one. The live read disagrees, and this change
  preserves the live state.
- On head `9be0cbb` of PR 165, the check run `agent-process / quality` concluded `success`
  from app `github-actions` (id `15368`).

## What Changes

- Add `skills/agent-process/scripts/activate_protection.py --pr <N> (--dry-run | --confirm)`
  and the ruleset body `skills/agent-process/templates/ruleset.json`. The ruleset requires
  `agent-process / quality` from the integration it observed, together with pull request,
  deletion, and non-fast-forward rules and no bypass actors.
- The preflight fails before any write when the default branch has no
  `.github/workflows/agent-process.yml`, or when the PR's current head has no successful
  `agent-process / quality` from GitHub Actions.
- The plan prints one line per ruleset transition (`planned`, `unchanged`, `conflict`) with
  its rollback command. It also prints the classic protection read, which the script never
  writes. Several rulesets with the process name, or one that is not repository-owned, are a
  `conflict`, and the run writes nothing.
- A confirmed write is read back. A mismatch on the default branch, a barrier rule, bypass
  actors, strictness, the context, or the integration exits non-zero and names the field.
- `distribution`: name the catcher that lets the publisher's own driver become required.
  Classic `quality / quality` (trusted driver) and `agent-review / agent-review` stay
  required on the same head.
- Delivery runs the activation on this repository, with the person's confirmation, against
  this change's own PR. That converts ruleset `23732345` in place.
- Removing classic `quality / quality` and deleting v1 `ci.yml` are a follow-up issue: one
  PR, and the person runs the reference `DELETE` call.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: modify `CI runs the trusted driver, not the PR's copy` (the same-head
  catcher). Add `Protection activation observes quality first`, `Activation previews every
  remote write`, `Activation converges one ruleset`, and `Activation reads back what it wrote`.

## Impact

- Added: `skills/agent-process/scripts/activate_protection.py`,
  `skills/agent-process/templates/ruleset.json`, `tests/publisher/test_activate_protection.py`.
- Edited: `skills/agent-process/SKILL.md` (`## Install` step 5),
  `tests/publisher/test_plugin.py` and `tests/publisher/test_delivery_scripts.py` (the
  package gains the script and template, and `ruleset` and `protection` leave the forbidden
  file-name tokens), `tests/publisher/test_reusable_workflows.py` (the catcher test),
  `.agent-process/scripts/check_branch_protection.py` (the reason text in `NOT_REQUIRED`),
  ADR 0027 (a *Native alternatives considered* row).
- Removed: nothing.
- Docs: the installation guide describes v1 until issue 115.
- External systems: ruleset `23732345` changes its required context from `quality / quality`
  to `agent-process / quality`, on the person's confirmation. Classic protection is not
  written.
