## Context

See `proposal.md` — Why, and the `distribution` delta. Current `main` has the shared skill
(`skills/agent-process/`, seven scripts, plugin `2.0.0`) and a test,
`tests/publisher/test_plugin.py::test_package_has_no_installer_state`, that rejects any
installer file in the package. ADR 0027 (v2-0b observations) leaves the `distribution`
requirements `The process footprint is one root…` and `This repository dogfoods its own
process` worded around the deleted Copier render, to be restated together with `init`; the
delta removes the first in favour of `The installed footprint is closed` and drops the second's
"before a consumer installation path is added". `reusable-quality.yml` on `main` takes no inputs; its
`setup`/`test` interface is delivered by issue 153. No `v2.0.0` tag exists; the person
creates it after the sequence of issue 112.

Observations this design rests on:

- `npx -y @fission-ai/openspec@1.13.0 init --tools claude,codex --no-animation` in a fresh
  Git repository (2026-09-23, Windows) exited 0 and created exactly: `.agents/skills/.openspec-target`,
  six `.agents/skills/openspec-*/SKILL.md`, six `.claude/commands/opsx/*.md`, six
  `.claude/skills/openspec-*/SKILL.md`, `openspec/changes/archive/.gitkeep`,
  `openspec/config.yaml`, `openspec/specs/.gitkeep`. Run again after a
  `# agent-process:begin … # agent-process:end` block was appended to
  `openspec/config.yaml`, it exited 0 and `git status --porcelain` was empty.
- A `git clone --no-checkout` printed one `D  <path>` line per tracked file from
  `git status --porcelain`; after `git checkout --detach <tag>` it printed none
  (2026-09-23).
- Claude Code plugin marketplaces reference
  (https://code.claude.com/docs/en/plugin-marketplaces, read 2026-09-23): a `github`
  marketplace source takes `repo` and optional `ref` — "Git-based marketplace sources
  support `ref` (branch/tag) but not `sha`." — and `ref` defaults to the default branch.
  `marketplace.json` lists the plugin with `"source": "."`, so the marketplace ref is the
  plugin ref.
- The Codex skill location (`~/.agents/skills`, symlinked directories followed) is on record
  in PR 151's archived `design.md` D2 (https://developers.openai.com/codex/skills, read
  2026-09-20).

## Goals / Non-Goals

**Goals:** one installer whose every transition — preview, release selection, write,
interruption, retry, conflict — is exercised by a test on both platforms.

**Non-Goals:** Project copy/link and its UI checklist (issue 156); the ruleset, secrets, and
required checks (issues 153, 154); an advisory review job in the caller (issue 114);
uninstall; committing or pushing the rendered files.

## Decisions

### D1. The requested release owns its run

`init.py` carries `VERSION` equal to the plugin version (a test compares them). With
`--version` equal to `VERSION` it runs itself. Otherwise:

- `--dry-run` clones `v<version>` with `--depth 1 --branch` into a
  `tempfile.TemporaryDirectory`, runs that tree's `init.py` with the same literal
  arguments plus a hidden `--selected-release`, forwards its stdout and stderr unchanged, and
  exits with its exit code. Nothing outside the temporary directory is written.
- `--confirm` reconciles the persistent checkout and link to `v<version>` (D3), then runs the
  checkout's `init.py` the same way and returns its exit code. The running installer writes
  no consumer file.
- `--selected-release` with a `VERSION` other than `--version` exits 1: a tag that does not
  carry its own version never recurses.

The repository URL is a constant; the environment variable `AGENT_PROCESS_REPOSITORY`
overrides it for tests, is inherited by the handed-off child, and when set the plan prints
it as its first line, so an override is never silent.

Alternative: switch the checkout and re-import the new module in-process. Rejected: the
old process's already-loaded code and templates would still decide part of the run — the
defect class PR 151's review found three times.

### D2. Preflight every transition, then write in a fixed order

A run first builds its transition list and classifies each one from observed state as
`planned`, `unchanged`, or `conflict`, then prints it. Any `conflict` exits 2 before the
first write; `--dry-run` stops after printing. Confirmed writes run in this order:

1. process checkout at `~/.agent-process/distribution` at the tag (D3);
2. link `~/.agents/skills/agent-process` (D3);
3. hand-off when the version differs (D1) — the child repeats the preflight, so steps 1–2
   report `unchanged` there;
4. pinned OpenSpec `init --tools claude,codex`;
5. marker block in `openspec/config.yaml`;
6. managed `.github/workflows/agent-process.yml`;
7. marker block in `.github/dependabot.yml`;
8. two keys in `.claude/settings.json`.

Steps 1–2 before 4–8 are what "confirmation selects the release first" means. Each step
prints `written` or `unchanged` when it completes. Step 4 is classified from owned state, not
by running the command: `unchanged` when every path of the pinned OpenSpec output (the observed
list in Context, a constant beside the pin) exists and the marker block of
`openspec/config.yaml` records that same pin in its `# openspec: <pin>` line; otherwise
`planned`, and only `planned` runs the command. Step 4 completes by writing that pin line (its
last write, creating the block with only that line when absent); step 5 renders the rest of the
block and keeps the line. The dry-run prints the same classification. A retry after step 4
therefore does not run OpenSpec again; a release whose pin differs from the recorded one
re-runs it; and `test_installed_footprint_is_closed` catches the path constant drifting from
the real pinned output. Whether a future pin refreshes files that already exist is that
release's to observe when it changes the pin; this change keeps `1.13.0`.

When the version differs, the running installer's list is steps 1–3 only: consumer targets
are the requested release's to judge. A consumer conflict is then found by the child after
steps 1–2 have completed; it exits 2 before any consumer write, the checkout stays at the
requested tag, and a rerun after the person resolves the conflict reports steps 1–2
`unchanged`. The entry points (D7) always run the dry-run first, which is the requested
release's own full preflight.

Alternative: check each target just before writing it. Rejected: a conflict in step 7 would
leave steps 4–6 written, and the operator must then untangle a half-install.

### D3. The checkout and link are reconciled, never repaired

Checkout states: absent → clone; a Git repository whose `origin` is the process repository,
clean, and whose `HEAD` equals `v<version>^{commit}` → `unchanged` without a fetch; the same
but on another commit → `git fetch --tags origin`, then `git checkout --detach v<version>`;
anything else (other origin, dirty, not a repository) → `conflict`.

A clone goes into a sibling `tempfile.mkdtemp(dir=~/.agent-process)` directory with
`--branch v<version>` and is moved into place with one `os.replace`; the checkout path
therefore exists only when complete. This fixes the observed `--no-checkout` defect
(Context): no intermediate state of the clone is visible to a retry.

Link states: absent → create; resolves to `<checkout>/skills/agent-process` → `unchanged`;
anything else, including a real directory → `conflict`. Unix creates it with
`ln -s <target> <link>`; Windows with `cmd /c mklink /J <link> <target>`; both through the
runner, so a row of the other platform emulates only that command — `os.symlink` needs a
privilege a Windows host may lack (`WinError 1314`, observed 2026-09-23). Every executable
(`git`, `npx`, `cmd`, `ln`) is resolved with `shutil.which` before it is run, so `npx.cmd` is found on Windows and
a missing tool is an `error:` line with exit 1.

The checkout and link exist once per user, because Codex reads user skills from one
`~/.agents/skills` directory: a confirmed run in one repository moves the Codex skill of every
repository on the machine, while each repository's Claude plugin stays pinned by its own
`ref` (D4). This is accepted, and made visible: the checkout transition prints
`<current tag or commit> → v<version>`, and the Install section says the Codex skill is
user-wide.

Alternative: move a foreign link aside. Rejected: it deletes or hides state the installer
does not own. Alternative: one checkout per tag. Rejected: the single user link still selects
one of them, so it adds directories without making Codex per-repository; a repository-scoped
`.agents/skills` link would leave the closed footprint.

### D4. Consumer file ownership

| Target | Owned when | Conflict when |
|---|---|---|
| `openspec/config.yaml` | the one `# agent-process:begin/end` block | several or unordered markers; an unmarked top-level `rules:` |
| `.github/workflows/agent-process.yml` | first line `# agent-process:managed` | the file exists without it |
| `.github/dependabot.yml` | the one marker block | the file exists, is non-empty, and has no block |
| `.claude/settings.json` | `extraKnownMarketplaces["agent-process-marketplace"]` whose `source.repo` is the process repository; `enabledPlugins["agent-process@agent-process-marketplace"]` absent or `true` | invalid JSON, a non-object, the key naming another repository, or the plugin set to `false` |

Rendering: `config.yaml` holds `rules:` with one pointer per artifact to the matching
`agent-process` skill section, and the tasks pointer names the `--test` command as the
repository's complete quality command. `agent-process.yml` calls
`ekolvah/agent-process-distribution/.github/workflows/reusable-quality.yml@v<version>` with
`setup` and `test` rendered through `json.dumps` (valid YAML scalars for any literal).
`settings.json` sets the marketplace source `ref` to `v<version>`, so the Claude plugin and
the Codex checkout are one release. Files are written through a sibling temporary file and
`os.replace`, UTF-8, `\n` line endings; "unchanged" compares decoded text, so a consumer's
CRLF checkout is not a diff.

An empty or whitespace `--test` exits 2 at argument parsing.

### D5. The caller replaces the trusted registry — for consumers, later

The rendered caller passes consumer-supplied `setup`/`test` where this repository's
`ci.yml` lets the default-branch `ci_check.py` registry choose the checks. Nothing runs it in
this change: `main`'s callee takes no inputs and the consumer has not committed the file.
Failure modes and their catchers:

- Quoting that breaks YAML → `test_init.py::test_literal_commands_are_yaml_safe` in this PR's
  `quality` run.
- Empty command → refused by `init` (D4), same test file.
- Typo or failing command → the consumer's first `quality / quality` run on its PR head,
  reachable once issue 153 lands the callee.
- A command that passes while skipping gates → not machine-caught; the person inspects the
  `.github/workflows/` diff of the consumer PR that commits the file (issue 112's accepted
  trust boundary).
- Callee interface drift → `test_init.py::test_caller_inputs` pins the template's `with:`
  keys to `{setup, test}`; issue 153 must declare exactly those inputs, and the PR report of
  this change names that contract under deferrals.

No guard of this repository is dropped.

### D6. Tests drive the transitions, not the steady state

`install()` takes `root`, `home`, `platform`, a subprocess `runner` (the process boundary),
and an `on_write(label)` callback invoked after each persistent write. Tests use real `git`
against a local bare fixture repository (via `AGENT_PROCESS_REPOSITORY`) whose tags carry
this tree's `init.py` and templates at `v2.0.0` and, at `v2.1.0`, a recording stub `init.py`
that prints its argv, `cwd`, and a marker, and exits with a chosen code — the hand-off
contract treats the selected release as opaque. Rows whose platform is the host's use the
real runner for the link; rows for the other platform emulate only its link command
(`mklink` or `ln`, creating a host-native link). The table emulates `npx` (writing the observed OpenSpec file set);
`test_installed_footprint_is_closed` runs the real pinned OpenSpec through `shutil.which`, as
`test_openspec_valid.py` already does. CI runs on `ubuntu-latest` only, so the real junction and
`npx.cmd` paths are proven by running `tests/publisher/test_init.py` on a Windows host during
implementation; its output goes into the PR report.

Because the upgrade stub composes nothing, installation over another release's rendering is
proven in-process by `test_rerender_replaces_only_owned_content`: the consumer is seeded with
owned content rendered for another tag — including a block that records another OpenSpec
pin — beside consumer content, and a same-version confirmed run must run OpenSpec once and
rewrite only the owned block, file, and keys.

The lifecycle table is one parametrized test over {fresh, same-version, upgrade} ×
{dry-run, confirm, retry} × {win32, linux}; its rows assert the printed transitions and a
snapshot of `root` and `home`. Fault injection is a separate test parametrized over the labels
an uninterrupted fresh and upgrade run reports: `on_write` raises at label *n*, the retry
completes, and the runner log shows each state-changing command once across both runs. A new
write therefore enters the fault set without editing the test.

Alternative: a fake runner for `git`. Rejected: PR 151's fakes passed while the real clone
left a state its retry refused.

### D7. Entry points

`commands/init.md` (Claude, `/agent-process:init`) and a `## Install` section in
`SKILL.md` (Codex, and the source the command follows) both: collect `--test` and optional
`--setup`, run `--dry-run`, show its whole output, ask once, run `--confirm`, and tell the
person to review and commit the changed files. The section also states that in a consumer,
`skills/agent-process/` in the commands of this skill means this skill's own directory, and
gives the Codex bootstrap: run `init.py` from a temporary clone of the tag, because the user
skill path must become the installer's link. `agent-process-installation.md`'s retired
note points to that section.

## Risks / Trade-offs

- [No `v2.0.0` tag exists, so no real end-to-end install is possible yet] → the fixture
  repository proves the tag-driven paths; issue 117 is the first real consumer.
- [A hard kill during a clone leaves a `tmp*` directory under `~/.agent-process/`] → it is never
  read; the checkout path appears only through `os.replace`.
- [`extraKnownMarketplaces` applies only after the teammate trusts the folder (settings
  reference, read 2026-09-23)] → the Install section says so; the Codex side does not depend on
  it.
- [A confirmed upgrade meets a consumer conflict after the checkout moved (D2)] → no consumer
  file is written, the Codex skill is already at the requested tag, and the rerun continues;
  running the dry-run first, as both entry points do, reports the conflict before any write.
- [One repository's upgrade moves every repository's Codex skill (D3)] → accepted and printed
  as `<old> → <new>`; the Claude plugin stays per-repository.
- [Retry after a hand-off crash re-runs the old installer] → D1–D3: the checkout is already
  at the tag, reports `unchanged`, and the hand-off runs the selected release again.

## Migration Plan

1. RED: `tests/publisher/test_init.py` and the package-boundary updates.
2. Templates and `init.py` (D1–D4, D6), then the entry points and docs (D7).
3. Strict OpenSpec validation and `python .agent-process/scripts/ci_check.py`; deliver under
   the unchanged v1 workflow and review gate.
4. Rollback: revert the PR. It creates no consumer, user-profile, or GitHub state.
