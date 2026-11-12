## Context

The project label of every telemetry series comes from `env.OTEL_RESOURCE_ATTRIBUTES` of the
consumer's `.claude/settings.json`
([ADR 0026](../../../.agent-process/docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md));
the task-readings recording filters on it. `init`'s `settings` step owns two keys of that file
(`extraKnownMarketplaces` entry, `SessionStart` group) and copies every other key; `manual.rows()`
prints what `init` cannot do, with the reason. Neither covers the attribution today
(proposal, **Why**).

## Standard approach

- OpenTelemetry, *Resource SDK — Specifying resource information via an environment
  variable* (https://opentelemetry.io/docs/specs/otel/resource/sdk/#specifying-resource-information-via-an-environment-variable):
  "The `OTEL_RESOURCE_ATTRIBUTES` environment variable will contain of a list of key value
  pairs, and these are expected to be represented in a format matching to the W3C Baggage,
  except that additional semi-colon delimited metadata is not supported, i.e.:
  `key1=value1,key2=value2`." `/` and `:` are baggage octets, so the name and URL need no
  percent-encoding.
- Claude Code settings, *Settings precedence* (https://code.claude.com/docs/en/settings):
  "When the same key appears in more than one place, Claude Code uses the value from the
  highest level that sets it." Shared project settings (`.claude/settings.json`) rank above
  user settings (`~/.claude/settings.json`), and "An `env` block inside a settings file is an
  ordinary key and follows the levels above." Over the process environment, the settings value
  wins outright — observed (`telemetry-measurement-setup.md`, "Precedence is observed").
- The set-up-or-print pattern is this repository's own:
  [ADR 0048](../../../.agent-process/docs/adr/0048-init-sets-up-task-readings-from-the-grafana-mcp-config.md)
  (task readings) and the pre-push step (`manual.pre_push`, `_pre_push_row`).

## Goals / Non-Goals

**Goals:** a consumer gets the attribution from its installation PR when that loses nothing;
otherwise `init`'s output names the step and why it was left.

**Non-Goals:** recovering readings of tasks merged before the value was set; a session-start
marker for the missing label; a clearer gap text of `task_readings.py` for unlabelled series.
Each is a separate issue if an adopter hits it after this change.

## Decisions

**D1 — Write when nothing is lost, else print.** The issue asked for a row; the person chose
the write (planning conversation, 2026-11-12). By the precedence above, the project value
replaces the same variable of the user settings and of the process environment for every
session in the repository. The only loss is a value the person set there, so `init` writes
only when it sees none. A row alone was rejected: it leads the person to the same replacement
by hand, one more step later, while sessions run unlabelled.

**D2 — Done means the pair `vcs.repository.name=<owner/repo>` is present.** The value splits
on `,`, each item on its first `=`, keys and values stripped of whitespace; other pairs do not
matter, since the recording filters on the name only.

**D3 — The machine's value.** `OTEL_RESOURCE_ATTRIBUTES` of `init`'s environment or of `env`
in `~/.claude/settings.json` (`t.home`), whatever it carries. A Claude Code session's settings
`env` does not reach the processes it starts (observed 2026-11-12: in a session of this
repository, whose project settings set the value, Bash prints it unset), so a value seen there
is the person's own, not a carrier, and is never replaced silently.

**D4 — One state, read in `manual.py`.** `attribution(t)` returns the target value, whether it
is done, and `blocked`, read in this order: the file is done → nothing else is read and
nothing is blocked, whatever the file's form; the file's own value (another repository's or
the person's); the machine's value and where it is set; `.claude/settings.json is not in the
form init writes`. The first lines of `_identity_pending` become `_settings_env(path) -> dict |
None` (the `env` object through `_plugin_file`, `None` when absent, `{}` when `env` is
missing, `Unreadable` for a non-object document or `env`), which both call; a non-string
value is `Unreadable`, as is a malformed `~/.claude/settings.json`. `init._json_text` moves to
`manual.json_text` so the form test and the write share one definition. The form matters: a
hand-formatted file that needs nothing else is `unchanged` today; adding the key would turn it
into a `settings` conflict, so it is `blocked` instead.

**D5 — The write.** `init` reads the consumer repository (`_repository`) before the consumer
steps, today right after them, and passes `<owner>/<name>` to the `settings` render, which
reads `attribution` through `_target(ctx, repo)`. `_settings_text` adds
`env.OTEL_RESOURCE_ATTRIBUTES` when the attribution is neither done nor blocked, keeping
every other `env` key; a `manual.Unreadable` leaves it, as the row prints the reason, so it
never escapes `_file_step`, which catches only `Conflict`. Its no-op return then also
requires the attribution done or left. A dry-run prints the step `planned`; a re-run after
the write is `unchanged`.

**D6 — Row text, printed only while blocked or unreadable.** `manual telemetry-attribution:
.claude/settings.json of this repository -- set env.OTEL_RESOURCE_ATTRIBUTES to
vcs.repository.name=<repo>,vcs.repository.url.full=https://github.com/<repo> and commit it;
the settings value replaces this machine's value of that variable in this repository's
sessions; sessions before it carry no project label and record no task readings (<blocked>)`.
Placed directly before `manual task-readings`, the row it feeds.

**D7 — No new ADR.** The decision applies ADR 0048's pattern to ADR 0026's carrier; ADR 0026's
consequence "a settings-level value replaces the adopter's own value" is the guard of D3.
`telemetry-measurement-setup.md` replaces "An adopter sets the pairs by hand" with the write
and its condition.

**Tests.** An autouse fixture clears `OTEL_RESOURCE_ATTRIBUTES`: a developer's shell may
export it, and every `init` run would then see a machine value.

## Risks / Trade-offs

- The environment of later sessions may differ from `init`'s (a shell profile, a Windows user
  variable set afterwards); pairs set only there are replaced silently. Accepted: the doc's
  precedence section names it, and the readings show the label either way.
- A value in a clone's `.claude/settings.local.json` outranks the project value in that clone;
  `init` does not read it for this. Accepted: local settings are that person's choice.
- A consumer without a canonical GitHub URL gets the URL pair; the doc says to omit it then.
  Accepted: `init` targets GitHub repositories only.

## Migration Plan

An adopted repository gets the value in the PR of its next `init` run (an upgrade included),
or the row. Rollback is reverting the PR; a written value stays the consumer's to keep.
