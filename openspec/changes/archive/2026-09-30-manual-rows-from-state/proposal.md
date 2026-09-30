## Why

`init` classifies every step from observed state except its closing `manual` rows: `_manual()`
(`skills/agent-process/scripts/init.py`) returns fixed strings, only `quality-command` being
conditional, and a confirmed run prints them before its writes, so a copy it creates is never
read. The person gets a to-do list half of which is done and has to check each row by hand
(#269).

**Reproduction (#269, 3.2.0 `--confirm` into the fresh `ekolvah/ekolvah-agent-process-sandbox-3`):**
the run printed all six rows although the secret, the plugin channel and all workflows but one
were already in place; the issue's table records each row's observed state.

**Observations (2026-09-30, gh 2.87.3, Windows 11), each a read that writes nothing:**
- `gh secret list --repo ekolvah/ekolvah-agent-process-sandbox-3 --json name` →
  `[{"name":"CLAUDE_CODE_OAUTH_TOKEN"}]`, exit 0. On `cli/cli` it printed `failed to get
  secrets: HTTP 403: You must have repository read permissions or have the repository secrets
  fine-grained permission.`, exit 1.
- GraphQL `repositoryOwner(login:"ekolvah"){... on ProjectV2Owner{projectV2(number:9){public
  workflows(first:50){nodes{name enabled}} field(name:"Area"){... on
  ProjectV2SingleSelectField{options{name}}}}}}` on the copy (#9): `public:false`; seven
  workflows, all enabled — `Auto-add sub-issues to project`, `Auto-close issue`, `Item added to
  project`, `Item closed`, `Item reopened`, `Pull request linked to issue`, `Pull request
  merged`; Area options `Observability, Distribution, Token efficiency, Process quality,
  Refactoring`. The template (#4): `public:true`, the same seven plus `Auto-add to project`,
  the same Area options. `gh project copy` leaves `Auto-add to project` out entirely (it is
  absent, not disabled).
- `~/.claude/plugins/known_marketplaces.json` entry `agent-process-marketplace`:
  `source {source: github, repo: ekolvah/agent-process-distribution, ref: stable}`,
  `autoUpdate: true`. `~/.claude/plugins/installed_plugins.json` `plugins
  ["agent-process@agent-process-marketplace"]` holds an entry with `scope: "user"`.
  `claude plugin marketplace list --json` prints `repo` and `ref` but no `autoUpdate`.
- pre-commit 4.6.0's hook template (`pre_commit/resources/hook-tmpl`) carries
  `# ID: 138fd403232d2ddd5efb44317e38bf03`; `git rev-parse --git-path hooks/pre-push` names
  the hook file git runs (`.agent-process/.githooks/pre-push` in this clone, whose
  `core.hooksPath` is set). `pre-commit install` refuses while `core.hooksPath` is set
  (observation on record in the archived change `consumer-pre-push-hook`, proposal — Why).

**Root cause:** the rows are rendered without reading the state they name, and before the
writes that create the Project copy.

## What Changes

- The `manual` rows are classified at the end of the run — after the writes of a confirmed
  run — from reads that write nothing, and a row whose target state is observed is omitted:
  `review-secret` from the repository's secret names, `project-visibility`,
  `project-workflows` and `project-areas` from the linked Project and the template,
  `plugin-channel` from the machine's plugin files, `pre-push` from this clone's git config and
  hook file. `quality-command` stays as it is.
- `project-workflows` names only the required workflows the copy lacks or has disabled;
  `project-areas` is printed only while the copy's Area options equal the template's;
  `project-visibility` only while the copy is private.
- A state `init` cannot read (no linked Project yet, a `gh` read that fails, a malformed
  plugin file) keeps its row and appends `(cannot read: <reason>)`; such a read never
  fails the run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: new *Manual rows follow observed state*; *Project UI actions are printed, not
  performed*, *The review secret is printed, not set*, *The marketplace follows the stable
  channel* and *Init renders the pre-push hook* print their row only while it is outstanding.

## Impact

Edited: `skills/agent-process/scripts/init.py` (`_manual`, the order of the output, the
module docstring); added `skills/agent-process/scripts/manual.py`, the rows' reads as a sibling
module like `onboarding.py`, since in `init.py` they exceed the 1000-line module gate
(`test_plugin.py` and `test_start_change.py` list it among the package scripts);
`skills/agent-process/SKILL.md` (Install steps 3–4: the rows
are the ones the run prints), `tests/publisher/init_harness.py` (`FakeGitHub` answers the
secret and Project reads; a copy is private and lacks `Auto-add to project`),
`tests/publisher/test_init_remote.py`.

Reviewed and still true: `.agent-process/docs/adr/0032-the-review-gate-is-installed-in-every-consumer.md`
(the `manual review-secret:` row exists while the secret is unset); the *quality-command*
requirement. No ADR: design.md records the decisions. No new dependency.
