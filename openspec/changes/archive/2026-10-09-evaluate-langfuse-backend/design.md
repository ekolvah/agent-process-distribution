## Context

See proposal.md — Why. Observed on 2026-10-07 in the plugin source at tag `v1.2.1`
(commit `b5b7cc364996467e856dc17575b5674f4799ad87`, the repository head), read with
`gh api repos/langfuse/Claude-Observability-Plugin/contents/<path>?ref=v1.2.1`:

- `hooks/hooks.json` registers `hooks/langfuse_hook.py` on `Stop` and `SessionEnd`, run by
  `uv run --quiet --script` when `uv` is on `PATH`, else `python3`.
- The script's inline metadata declares `"langfuse>=4.7,<5"`: a range, resolved at run time.
- `_opt(name)` reads `os.environ` first, then `CLAUDE_PLUGIN_OPTION_<name>`. Variables read:
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`, `LANGFUSE_USER_ID`,
  `CC_LANGFUSE_TRACE_TAGS` (JSON array or comma list, at most 20), `CC_LANGFUSE_TRACE_SEED`,
  `CC_LANGFUSE_TRACEPARENT`, `CC_LANGFUSE_MAX_CHARS` (default 20000),
  `CC_LANGFUSE_CAPTURE_IMAGES` (default true), `CC_LANGFUSE_SKILL_TAGS`, `CC_LANGFUSE_DEBUG`.
- `.claude-plugin/plugin.json` declares the keys, base URL, user id, seed and the
  `CC_LANGFUSE_*` switches except `TRACE_TAGS` and `TRACEPARENT` (environment only) as
  `userConfig`; `LANGFUSE_SECRET_KEY` is `"sensitive": true`. For keys and base URL,
  `_core_opt` prefers a `LANGFUSE_*` variable in the environment over the `userConfig` value.
- No `TRACE_TO_LANGFUSE` gate exists in this version (the integration page still documents
  one): with keys configured, every session the plugin is enabled for is traced.
- `main()` returns 0 on every failure (missing config, lock timeout, any exception), logging
  only to the hook's state directory.

The integration page and this source disagree on tags and the gate; the source decides.

## Goals / Non-Goals

**Goals:** answer the fixed criterion of issue 103 (AC5) on real tasks of this repository,
with an egress and key-handling record the owner signed off before the first trace.

**Non-Goals:** the Codex route (AC6 of issue 103; no Codex carrier,
[ADR 0033](../../../../.agent-process/docs/adr/0033-claude-code-is-the-only-carrier.md)); a task
launcher (#101); edits to the Grafana stack or its setup doc; the community plugin
`pdhoolia/langfuse-claude-code-plugin` unless D5 fails on fidelity.

## Decisions

**D1 — Pin by commit, not by marketplace name.** Clone the plugin repository into
`evidence/langfuse-plugin/` of the main checkout (not the change worktree, which is deleted
after merge), check out `v1.2.1`, verify `git rev-parse HEAD` equals `b5b7cc36…`, and install
from that clone as a local marketplace, from the main checkout root where measured sessions
start. A git commit id is the published integrity digest for a git-distributed plugin; the
marketplace name alone resolves to whatever the default branch carries. A plugin from a local
marketplace is "loaded in place" and not pinned by its `version` field (plugins reference,
`version`), so the clone's head and clean state are re-checked before each measured task.
*Alternative:* `claude plugin install langfuse-observability@langfuse-observability` —
rejected, unpinned.

**D2 — Freeze the SDK resolution.** The script's `langfuse>=4.7,<5` range moves under the
hook. At vetting, resolve it once with `uv` and record the version and its PyPI sha256; set
`UV_EXCLUDE_NEWER` to the vetting date so `uv run --script` cannot resolve past the vetted
release (uv environment reference: "If set, uv will exclude distributions published after the
specified date"). It goes in the `env` block of the main checkout's `.claude/settings.local.json`
(untracked: `git check-ignore` matches it on this host), which Claude Code applies to every
session and the hooks it starts, so no launch can omit it. If `uv` is absent, the `python3`
fallback runs an unvetted interpreter environment: vetting confirms `uv` is on the hook's
`PATH` first.
*Alternative:* a lockfile beside the script (`uv lock --script`) — it lives in the plugin
cache and is lost on reinstall; rejected for a spike.

**D3 — Keys through the plugin's `userConfig`, never env or files in the tree.** Plugins
reference, "Where values are stored": "Non-sensitive values are saved under `pluginConfigs` in
the user's `settings.json`. Sensitive values go to the platform's secure credential store
instead." The spike observes where the secret actually lands on this Windows host (Credential
Manager or `~/.claude/.credentials.json`) and records it; a plain file is a finding for the
owner before the first trace (AC1/AC2), not a reason for a bespoke loader. Because an
environment `LANGFUSE_*` overrides `userConfig` (Context), no such variable may be set in the
launching shell.

**D4 — Egress decided against the vetted payload.** After D1–D3, the implementer writes the
payload record (fields sent, truncation at 20000 chars, images on by default, skill content
off by default, destination host) to `evidence/`, and stops. The owner chooses Cloud (region)
or self-hosted and the `CC_LANGFUSE_CAPTURE_IMAGES` value; the choice and reason go into the
ADR. Nothing is sent before that. Because there is no gate (Context), scope is enforced by
installing the plugin at `local` scope in this repository only and uninstalling it when the
readings are taken.

**D5 — Identity by operator tags.** Each measured session is launched with
`CC_LANGFUSE_TRACE_TAGS=task:<change>,attempt:<n>` set by the owner — the comma form, which
needs no JSON quoting (`parse_operator_tags` reads a value not starting with `[` as a comma
list, so a JSON value that keeps shell quotes silently becomes wrong tags); the change name is
the task identifier this process already has. A task spanning several sessions (propose,
apply) shares the tag. If the tags do not reach the trace, that is the AC3 finding; no second
scheme is introduced. `CC_LANGFUSE_TRACEPARENT` (nesting sessions under one task trace) is
noted for #101, not exercised.

Owner-typed tags replace a launcher-minted id, so their failure modes are listed here: a
missing tag (session untagged, invisible to the readings), a mistyped tag (session under a
phantom task), and a stale tag left in the shell from the previous task (an unrelated session
inflates a task's readings). Catcher: the owner records the change → session id list at each
launch (task 4.1), and task 4.3 checks that the sessions under each `task:<change>` tag in
Langfuse are exactly that list before any metric is read; a mismatch is corrected in the list
of readings, not by retagging.

**D6 — Cross-check before belief.** For at least three tagged tasks, compare per-session
input, output, cache-creation and cache-read totals in Langfuse with
`npx -y ccusage@20.0.26 session --id <session-id> --offline --json` (`--help` of that version:
`-i, --id` "Filter to specific session ID"; `--offline` only selects cached pricing). A
divergence is explained (truncation,
deduplication, a dropped turn from the fail-open path) and recorded; a session present in
`ccusage` and absent in Langfuse is a fail-open drop and counts against AC4.

**D7 — Readings without code.** M1, M3, M4, M5, M6 are read per task from Langfuse UI
filters, dashboards or its public API query, with no script beyond the plugin and its
configuration. A metric that needs code is a failed criterion, recorded as such.

**D8 — One ADR carries the outcome.** `0036-per-task-token-analysis-backend.md` holds the
criterion, the pinned versions and digests, the egress choice, the readings table, the
verdict, and the reconsider condition (own orchestration on the Agent SDK → Langfuse SDK
instrumentation and Datasets/Experiments; repeat the comparison). It contains no transcript
text, repository content from transcripts, credentials or account metadata.

**D9 — Early exit.** Three gates end the spike before the measured tasks: the vetting (task
2.1–2.2) finds a destination or field the owner did not expect and cannot switch off; the owner
declines every egress option (2.3); the smoke run (3.2) shows the task tags do not reach the
trace, the hook log shows the cause is in the plugin or the platform rather than the launch,
and the Langfuse UI shows that M1–M6 cannot be filtered to a set of session ids without code.
A tag failure short of that is the AC3 finding, and the spike continues with session-id
filters over the 4.1 list. Each gate fails AC5 already. The spike
then goes straight to the ADR with verdict "Grafana stays", naming the gate and the observation,
and runs the rollback for whatever was installed. Running three tasks after a failed gate would
spend owner time on readings that cannot change the verdict.
*Alternative:* always run the full protocol for a complete readings table — rejected; the
table cannot overturn a failed criterion.

## Risks / Trade-offs

- [Every session in this repository is traced while the plugin is enabled, including
  unmeasured ones] → `local` scope; untagged traces are ignored by the readings.
- [Fail-open hook drops turns silently] → D6 compares against `ccusage`; the debug log is on
  during the spike.
- [The hook is POSIX shell under Git Bash on Windows; `uv` may be missing] → vetting runs one
  Stop event with debug on and reads the log before any measured task.
- [Fewer than three tasks land in the window] → the apply pauses; no verdict on two.
- [The source changes after v1.2.1] → the ADR names the version; #101 re-vets on upgrade.

## Migration Plan

Nothing in the tree changes but the ADR. Rollback, run on an early exit (D9):
`claude plugin uninstall` at local scope, remove the local marketplace, the plugin's
`pluginConfigs` entry in `~/.claude/settings.json`, the secret in the credential store, and
`UV_EXCLUDE_NEWER` and `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` from
`.claude/settings.local.json`. After a full run the owner keeps Langfuse in use beside
Grafana (plugin, keys, traces, the `langfuse` skill and MCP server), so the end of the spike
removes only its path-logging hooks. Grafana stays in place throughout.
