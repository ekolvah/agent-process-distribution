## Context

See proposal.md — Why for the reproduction and the observations each decision rests on.
`_manual(url, repo, root)` renders the rows from no reads; `_run` prints them after the plan
and before `_perform`. `Context` already carries the process boundary (`runner`, `which`,
`home`), and `FakeGitHub` in `tests/publisher/init_harness.py` answers every `gh` command a
test issues.

## Goals / Non-Goals

**Goals:** each `manual` row is outstanding work or says why its state is unknown.

**Non-Goals:** writing any of these states (issue #269, out of scope); checking the
workflows' target statuses or the Auto-add repository filter, which the GraphQL
`ProjectV2Workflow` does not expose (only `name`, `enabled` and ids); checking other clones.

## Decisions

**D1 — Read after the writes, print last.** `_run` classifies the manual rows after
`_perform` on `--confirm` (after the plan on `--dry-run` and on a conflict) and prints them
last. The linked Project is found by a fresh guarded `gh repo view` read (D2), so a copy the run just made
and linked is read like one that existed. *Alternative:* keep the rows before the writes —
a fresh install, the reproduction's case, would then read no Project and print every workflow.

**D2 — One read per state, none writes, none fails the run.** Each read uses `check=False` /
guarded parsing; a failure becomes the row's `(cannot read: <reason>)` with the command's
stderr or the parse error (§IV):
- `review-secret`: `gh secret list --repo <owner/name> --json name` (gh 2.87.3 requests
  the Actions secrets endpoint with `per_page=100`, `GH_DEBUG=api`; the command has no limit
  flag). Omitted
  when the names include `CLAUDE_CODE_OAUTH_TOKEN`.
- `project-*`: one GraphQL query with two aliased `repositoryOwner(...){... on
  ProjectV2Owner{projectV2(number:)}}` reads — the one linked Project (`public`,
  `workflows(first:50){nodes{name enabled}}`, `field(name:"Area"){... on
  ProjectV2SingleSelectField{options{name}}}`) and the template `ekolvah#4` (its `Area`
  options). `repositoryOwner` covers user and organization owners (observed on a user).
  Without exactly one linked Project the three rows print as today with `(cannot read: <n>
  Projects linked to <repo>)`. The post-write `gh repo view` and the GraphQL read go through
  `ctx.call(..., check=False)` with guarded JSON parsing, not `_gh_json` (whose
  `check=True` raises `InstallError`, which after `_perform` would turn a finished install into
  exit 1); their failure gives the three rows `(cannot read: <stderr or parse error>)`. A
  Project without an `Area` field makes gh exit 1 yet print `data` with `"field":null` beside a
  `NOT_FOUND` error (observed 2026-09-30), so the read is classified from the printed `data`
  whatever the exit code, and only a missing Project node is unreadable.
- `plugin-channel`: `ctx.home/.claude/plugins/known_marketplaces.json` (entry
  `agent-process-marketplace`: `source.repo` = `GITHUB_REPO`, `source.ref` = `stable`,
  `autoUpdate` true) and `installed_plugins.json` (`plugins[PLUGIN]` has an entry with
  `scope` `user`). A missing file, entry or plugin is outstanding (a machine that never
  installed a plugin has no such file); a file that is not the observed JSON shape is
  unreadable.
- `pre-push`: `git config --get core.hooksPath` exits 1 (unset) and the file
  `git rev-parse --git-path hooks/pre-push` names contains pre-commit's
  `# ID: 138fd403232d2ddd5efb44317e38bf03`.

*Alternative for the plugin:* `claude plugin marketplace list --json` / `claude plugin list
--json`, the standard readers `skill_check.py` uses — rejected because the first prints no
`autoUpdate` (observed), so a file read remains, and a `claude` subprocess would break the
spec's "no `claude` command" and run the real CLI inside the test Runner. The files are
Claude Code internals: a changed shape degrades to `(cannot read: …)`, never to a silent omit.

**D3 — Row conditions.** `project-visibility` while `public` is false (a copy starts private,
the template is public; keeping it private is the person's choice, so that row can persist).
`project-workflows` while any of `Auto-add to project`, `Item added to project`,
`Item reopened`, `Item closed`, `Pull request merged` is absent or disabled, naming only those
with the target text `WORKFLOWS` carries today. `project-areas` while the set of the copy's
`Area` option names equals the template's, or the copy has no `Area` field. Workflows the copy
has enabled are taken as done: their target statuses come with the copy and cannot be read
(#269's table lists them as done) — see Non-Goals.

**D4 — Omit, not `unchanged`.** An observed-done row is not printed. `unchanged` belongs to
steps `init` performs; printing done manual rows is the noise the issue removes (#269).

**D5 — Test fake mirrors the observed shapes.** `FakeGitHub` gains a secret-name set with a
`403` fault, answers the Project query from `Project` fields (`public`, `workflows`, `areas`),
and `project copy` yields a private copy with the template's `Area` options and every
workflow but `Auto-add to project` — the shapes in proposal.md — Why. The plugin files are
written under `Sandbox.home`; the hook file under the consumer's `.git/hooks`.

## Risks / Trade-offs

- [Claude Code changes its plugin files] → the row prints with `(cannot read: …)`; the
  session-start check keeps catching a missing user-scope install.
- [More than 100 secrets and gh does not page past the first] → `CLAUDE_CODE_OAUTH_TOKEN`
  may be missed: a false outstanding row, never a false omission.
- [pre-commit changes its hook ID] → the row is printed although installed: a false
  outstanding row, never a false omission.
- [`pre-push` done in this clone but not another] → the row is omitted here; SKILL.md Install
  step 4 keeps "in each clone".
- [A private copy the person wants private] → the visibility row repeats on every run.

## Migration Plan

Output-only change of `init`; no consumer file or state changes. Rollback is reverting the PR.
