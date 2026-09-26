## Context

See proposal.md — Why. The skill's release is `init.VERSION` (asserted equal to the plugin
manifest's `version` by `test_init.py`). The config block is written by the `config` step from
`templates/config.yaml`; `_recorded_pin` already reads one line of that block through `_span`.
This repository installs nothing into itself: its `openspec/config.yaml` has no marker block.

## Decisions

### One module owns the line: `init.py`

`init.py` gains `RELEASE = "# agent-process release: "` and renders it into the block from
`VERSION`, as `render_config_block` already renders `OPENSPEC` (its signature is unchanged):
`VERSION` is the installed release in every run that writes — a hand-off child whose `VERSION`
differs from `--version` exits 1 first. It exposes
`release_drift(root: Path, script_dir: Path) -> str | None`: `None` when the comparison passes or is
exempt, otherwise the message. It reads the line inside the block the way `_recorded_pin` does;
any `Conflict` — from `_read` (symlink, non-UTF-8, mixed line endings) or from `_span` — counts
as absent, so it ends in the exit-2 message, never a traceback. `start_change.py` and `create_tracking_issue.py`
import it (`from init import release_drift`); `init.py` has no import-time side effects.

Rejected: reading `.claude-plugin/plugin.json` — it is outside the skill directory, so a Codex
link to the skill alone would not reach it; a separate module — a second owner of the constant
the installer writes.

### Comparison and messages

The value must fully match `\d+\.\d+\.\d+`; versions compare as integer tuples, and any
difference is drift (a patch release may change the templates). Messages, on stderr, exit 2:

- absent / unparsable / older: `release drift: project records <x|none>, skill is <V> — re-run
  Install with this skill (<skill dir>/SKILL.md#install)`
- newer: `release drift: project records <x>, skill is <V> — update the skill to <x>: Claude
  `/plugin marketplace update agent-process-marketplace`, Codex Install with `--version <x>`;
  then restart the session`

The scripts only name the fix (decided with the person): a plugin or link update is
machine-wide and the running session needs a restart anyway.

### Placement: first step

Both scripts call it as the first statement of `start_change()` / `create_tracking_issue()`,
before the review is validated — the check is local and a drifted skill's validator or schema
is itself suspect. Nothing reaches `gh`.

### Exemption by path

Exempt iff `os.path.normcase(script_dir.resolve()) == os.path.normcase((root / "skills" /
"agent-process" / "scripts").resolve())` — the publisher's source checkout, where the scripts
are the release. A copy of the scripts elsewhere under the root (a scratch clone, #187) is
compared. `script_dir` is a parameter so the exempt case is tested without copying files; the
scripts pass their own `SCRIPT_DIR`.

### Tests

`_change` in `test_delivery_scripts.py` also writes `openspec/config.yaml` holding
`init.render_config_block("t")`, so every existing delivery test runs as a
consumer on the same release (the scripts run from the publisher path while `root` is
`tmp_path`, so they are compared).

## Risks / Trade-offs

- [Every 2.0.0 consumer is refused once] → the message names Install, which writes the line;
  this is the intended migration.
- [Two consumers on one machine at different releases share the Codex link] → one of them is
  always refused; that is the drift made visible, not a false positive.
- [Other delivery scripts (`archive_change`, `wait_for_pr`, …) stay unchecked] → both entry
  points of a change are checked; a release switch between Group 0 and delivery (another
  repository moving the user-wide Codex link) is an accepted gap.

## Migration and rollback

Consumers get the line on their next `init --confirm`. Rollback: revert; a recorded line is an
inert comment in the block.
