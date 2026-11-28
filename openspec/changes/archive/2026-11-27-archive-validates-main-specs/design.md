## Context

`archive_change` (`skills/agent-process/scripts/archive_change.py`) is the only place the
process runs `openspec archive`; it then commits `openspec/` and pushes. Validation happens
earlier (Verify runs `openspec validate --strict --all` on the unarchived change) and never in
CI: `quality.yml` runs only the repository's declared `test`. The reproduction in `proposal.md`
shows the archive is where a placeholder Purpose first exists.

## Standard approach

- OpenSpec (https://github.com/Fission-AI/OpenSpec, pinned 1.13.0): the stock `/opsx:archive`
  runs `openspec-sync-specs`, whose step 5 is "Validate updated main specs: Run `openspec
  validate --specs`" and whose summary lists "Any new main spec left with a TBD Purpose
  placeholder". `archive_change` calls the CLI `openspec archive -y` instead, which writes the
  main specs and moves the change in one step and has no such step.
- The stock skill itself is not a replacement: it merges deltas by an agent and prompts the
  user, where the CLI merges deterministically, and it carries none of `archive_change`'s lock,
  clean-worktree, session and push steps.
- `openspec archive --help` (1.13.0) offers no dry run and no sync-only mode, so the main specs
  an archive writes can only be validated after it ran.

## Goals / Non-Goals

**Goals:** an archive whose new or changed main specs would not validate strictly never reaches
a commit; the fix and a re-run of `archive_change` are the whole recovery.

**Non-Goals:** a CI check of `openspec/specs/` on every PR head; repairing the reporting
consumer's existing placeholders (their Verify already reports them).

## Decisions

1. **Validate the touched main specs after the archive, before the commit.** Closes issue 525.
   After `openspec archive <change> -y` and the lock removal, `archive_change` runs `openspec
   validate <capability> --type spec --strict` for each `spec.md` under the archived change's
   `specs/` whose main spec exists (a retired capability has none), the capability named by its
   parent path relative to `specs/` in forward slashes (`as_posix()`), and on a
   failure exits 2 printing OpenSpec's findings and one line: nothing was committed; replace the
   placeholder Purpose in `openspec/specs/<capability>/spec.md`, then re-run. Strict, unlike the
   stock non-strict step, because a placeholder is a warning that only strict mode fails on
   (scratch project, 1.13.0: `validate --specs` reports `2 passed` with the placeholder warning,
   rc=0; `validate beta --type spec --strict` reports `Specification 'beta' has issues` and the
   warning on stderr, rc=1, so `_runner`'s `RuntimeError` carries the findings).
   Touched specs only, so a pre-existing invalid spec elsewhere does not block every delivery.
   Only the validate calls are caught; a failing archive stays exit 1 as today.
   - Alternative: preview the archive on a temporary copy of the touched specs before the real
     one. Rejected: a bespoke mechanism with no stock counterpart and two extra `npx` runs per
     delivery, against one more `npx` run per touched capability here.
   - Alternative: on a failure, restore `openspec/` from `HEAD` so the fix goes into the delta.
     Rejected: it discards the uncommitted Verify ticks, and a placeholder in an existing spec
     has no delta fix anyway (decision 3).
   - Alternative: a `quality.yml` step on the PR head. Rejected: Node and an `npx` download in
     every consumer's required check, and the placeholder is caught only after the push.
   - Deletion condition: when `openspec archive` validates the main specs it writes, or
     `openspec validate --strict` of a change rejects a new capability without `## Purpose`.
2. **A re-run resumes an uncommitted archive.** A refusal leaves the change moved and nothing
   committed, so a re-run cannot archive again. When `openspec/changes/<change>/` is gone and
   `git status --porcelain` lists its `openspec/changes/archive/<date>-<change>/` as
   uncommitted, `archive_change` skips the session binding, the tick and the archive (the
   archived `sessions` and `tasks.md` already carry them) and continues from the validation; it
   accepts uncommitted paths under `openspec/` only and exits 2 naming any other.
3. **A placeholder Purpose is fixed by a direct edit.** OpenSpec 1.13.0's validate warning:
   "editing the main spec directly: a `## Purpose` in a delta is read only when the capability
   is created, so it cannot replace this one"; `openspec instructions specs`: "To change an
   existing capability's Purpose - including a leftover `TBD` placeholder - edit
   `<planningHome.root>/openspec/specs/<capability-path>/spec.md` directly". After the archive
   this holds for a new capability too, so `SKILL.md` Delivery's "never a direct edit of
   `openspec/specs/`" gains that one exception.

## Risks / Trade-offs

- One more `npx` run per touched capability per delivery, a few seconds each.
- A refusal leaves an uncommitted archive in the worktree until the re-run; the refusal message
  names the re-run, and decision 2 makes it the only recovery needed.
- A nested capability is named by its full path (architect-review on a scratch project, 1.13.0,
  placeholder in `openspec/specs/grp/sub/spec.md`: `validate grp/sub --type spec --strict` reports
  `Specification 'grp/sub' has issues`, rc=1; `validate sub` fails with ENOENT, rc=1), so a
  top-level name or a Windows path would refuse with a misleading Purpose hint.
- Rollback: revert the script and the `SKILL.md` line; nothing migrates. No ADR: the decision
  is local to one script.
