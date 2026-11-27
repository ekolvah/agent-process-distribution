## MODIFIED Requirements

### Requirement: `archive_change` archives the change before its PR
One script, `archive_change <change>`, SHALL archive a change on its branch before the PR
opens: it SHALL refuse to run while the worktree holds any change other than a modification
of `openspec/changes/<change>/tasks.md`, or while an archive lock already exists; otherwise it
SHALL mark its own task done, run `openspec archive <change> -y`, remove the lock a successful
archive leaves behind, run `openspec validate --strict` on each main spec the change has a
delta for, commit — the ticks left in `tasks.md` included — and push, leaving a clean
worktree. When that validation fails it SHALL exit 2 printing OpenSpec's findings, before
committing; a re-run while the change's archive is still uncommitted SHALL skip to the
validation, accepting uncommitted changes under `openspec/` only. It SHALL NOT request a
review or wait for the PR: those are the delivery tasks that follow it, recorded by the PR
itself.

#### Scenario: Archive commit
- **WHEN** `archive_change` runs on a clean worktree
- **THEN** the archive commit is pushed before any PR exists, and the run continues with the PR tasks

#### Scenario: Ticks left for the archive
- **WHEN** `archive_change` runs while the only uncommitted change is ticks in `openspec/changes/<change>/tasks.md`, again while another file is also changed, and again while that `tasks.md` is deleted
- **THEN** the first run's archive commit carries those ticks and leaves the worktree clean; the second and third exit 2 naming the other file or the deleted `tasks.md`, before archiving or committing

#### Scenario: Stale archive lock
- **WHEN** an archive lock exists before `archive_change` runs
- **THEN** it reports the lock and exits without archiving or committing

#### Scenario: Archive leaves a placeholder Purpose
- **WHEN** `archive_change` runs for a change whose delta creates a capability without `## Purpose`
- **THEN** it exits 2 naming that capability's spec from OpenSpec's findings, with no commit and nothing pushed

#### Scenario: Re-run after the Purpose is written
- **WHEN** the placeholder Purpose of that main spec is replaced by a direct edit and `archive_change` runs again
- **THEN** it validates without archiving again, and the archive commit carrying the written Purpose is pushed
