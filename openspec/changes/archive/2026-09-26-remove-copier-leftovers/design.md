## Context

See proposal.md — Why. The answers file is the only declared record of this repository's
identity (`github_repository`, `repo_name`) that any test reads.

## Goals / Non-Goals

**Goals:** remove the answers file and the dead Copier-era guards, and put every ADR under
the catalogue its test checks.

**Non-Goals:** the `tests/publisher` / `tests/agent_process` split and `_PROCESS_PATHS` of
`ci_check.py` stay; they are the layout the quality command runs today.

## Decisions

**D1. `TestTelemetryAttribution` checks the pairs against each other.** ADR 0026 fixes the
shape: `vcs.repository.name=<owner>/<repository>` and
`vcs.repository.url.full=https://github.com/<owner>/<repository>`. The tests assert that the
name is non-empty and `owner/repository`-shaped, and that `url.full` equals
`https://github.com/<name>` with at least two pairs. The blank-`github_repository` branch
goes: it served an adopter render with no URL, and this file is never rendered.
*Alternatives:* read `git remote get-url origin` (depends on the checkout's remote, which a
fork or a mirror changes) or `GITHUB_REPOSITORY` (absent locally). *Dropped guard and its
catcher:* no test any longer ties the name to a declared identity. A wrong literal in
`.claude/settings.json` mislabels telemetry, and telemetry is out of the v2 migration
(ADR 0029). Its catcher is the person reading the dashboard, which is the same as today,
because the answers file is itself a hand-kept literal next to the one it checks.

**D2. ADR 0012 and ADR 0017 stay unedited.** ADR 0027 lists the records it supersedes and says
"The other ADRs stay as history without edits". Adding a superseding record for two
historical mechanisms adds prose without changing behaviour. The person chose this in the
propose run.

**D3. `_has_product_scope` of `ci_check.py` is deferred.** Its "bare consumer render" branch
is also a Copier remnant, but removing it changes what the quality command runs. That is a
behaviour change for its own issue, not part of this chore (the person's choice in the
propose run).

**D4. The dead `skipif` guards are removed, not reworded.** `.claude/settings.json` is tracked
in this repository, and the installer does not copy `tests/agent_process/` to a consumer.
Without the file the tests should fail rather than skip (§IV).

## Risks / Trade-offs

- Moving the two ADRs brings them under `test_adr_records.py` for the first time. Their
  front matter and h2 sections were read during planning and match `_REQUIRED_SECTIONS` and
  the status set. The Verify group confirms this.

## Migration Plan

None: no consumer reads the removed file or the moved paths. Rollback is a revert of the PR.
