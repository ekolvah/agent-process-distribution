## Context

See proposal.md — Why. `init` classifies every transition `planned` / `unchanged` / `conflict` from
observed state, exits 2 on any conflict before writing, and `_perform` applies the planned steps in
order (`init.py` `_run`, `_perform`). The `link` step reads `closingIssuesReferences`, which a
closing keyword in the PR body fills.

## Goals / Non-Goals

**Goals:** the installation PR passes `link` on its first run with no step left to the person;
every new transition obeys *Init reconciles from observable state*.

**Non-Goals:** adding the issue to the Project (`link` does not read it); changing `link`;
opening a PR for Project-only changes (they write no file).

## Decisions

**D1 — The installer opens the PR (onboarding PR).** Renovate (`renovate/configure`),
pre-commit.ci and Dependabot all deliver their repository changes as a PR they open; the person
reviews and merges. Here that makes the link a property of code under test. Rejected: SKILL.md
prose with `gh issue create` / `gh issue develop` (the link depends on execution nobody checks);
`init` makes the issue and prints a `Closes #N` row (same, one step later); exempting the
installation PR from `link` (*A PR links its issue* exempts only release PRs).

**D2 — `Closes #<N>` in the body `init` writes, not a `gh issue develop` branch.** The body is
composed by `init`, so the link is exact and testable in the fake. A linked branch would be named
by GitHub from the issue (`CreateLinkedBranchInput.name` defaults to "issue number and title",
schema read 2026-09-29), so a dry-run could not name the branch before the issue exists, and a
retry could not find it without another read.

**D3 — Branch `agent-process/install-<version>`.** Reconciling needs a name known before any
write. A tool-namespaced onboarding branch is the Renovate precedent; the version keeps a merged
branch of an earlier release from blocking an upgrade.

**D4 — Five steps, in this order around the existing ones.** `onboarding-branch` first (so the
files land on it), then the file steps, the Project steps, `onboarding-commit`, `onboarding-issue`,
`onboarding-push`, `onboarding-pr`. Each is classified from reads and re-read in `apply`:

| step | `unchanged` when | `planned` when | apply |
|---|---|---|---|
| branch | current branch is B | on the default branch, clean worktree, B absent locally and on `origin` | `git switch -c B` |
| commit | on B, clean worktree, B ahead of the default branch | a file step is planned or the worktree has changes | `git add -A`, `git commit -m "chore: install agent-process <v>"` |
| issue | exactly one open issue titled `Install agent-process <v>` | none | `gh issue create --title … --body …` |
| push | `git ls-remote --heads origin B` equals `HEAD` | otherwise | `git push -u origin B` |
| pr | `gh pr list --head B --state open` has one | none | `gh pr create --base <default> --head B --title "chore: install agent-process <v>" --body "Closes #<N>…"` |

The steps exist only when a file step is planned or the current branch is B; otherwise the run
prints none of them (*Nothing to install*). On B, `gh pr list --head B --state all --json
number,state,url` is read first: a `MERGED` PR makes all five `unchanged` naming it (*Rerun after
the merge* — `init` leaves the checkout on B, so this is the person's likely next run), or a
`conflict` if a file step is still planned ("switch to <default> and pull"); a `CLOSED` PR with no
open one is a `conflict` ("reopen it or remove B"). Every other starting point is `conflict` naming
its cause and the command that resolves it (`git stash`, `git switch <default>`, `git switch B`).
More than one open issue with the title is a `conflict` listing them. The issue is found through
`gh issue list --state open --json number,title` (the list API, not search, so no index lag) and
matched on the exact title; a lost `gh issue create` output is therefore found on retry, not
duplicated.

Nothing depends on what the creates print: after `gh issue create` the number is re-read with the
same `issue list`, and after `gh pr create` the URL with `gh pr list --head B --state open --json
number,url`. Every `gh issue` / `gh pr` command pins `--repo <owner>/<name>` from `_repository`, so
a fork's parent is never targeted, and `--head` keeps `gh pr create` from pushing or forking
(`gh pr create --help`). The default branch comes from `gh repo view --json defaultBranchRef`,
added to `_repository`'s read.

Observed read shapes (2026-09-29, `ekolvah/agent-process-sandbox-2`): `gh repo view --json
defaultBranchRef` → `{"defaultBranchRef":{"name":"main"}}`; `gh issue list --state open --json
number,title` → `[]` (issue 2 is closed); `gh pr list --head install-agent-process --state all
--json number,state,url` → `[{"number":1,"state":"MERGED","url":"https://github.com/ekolvah/agent-process-sandbox-2/pull/1"}]`,
and with `--state open` → `[]`. The fake answers in these shapes.

**D5 — The confirmation stays the person's.** The dry-run plan lists the branch, issue, push and
PR before `--confirm`; the person still reviews and merges the PR, and `init` never touches the
default branch.

## Risks / Trade-offs

- [The consumer's commit hooks reject the commit, or git has no identity] → `git commit` fails
  visibly with its stderr; the files stay on B and the retry resumes at `onboarding-commit`.
- [The first head is pushed before `CLAUDE_CODE_OAUTH_TOKEN` exists] → `agent-review` would be red
  on it (archive `2026-09-25-v2-5-delete-control-plane`, design.md) and need a rerun, one manual
  action more than 3.0.0, where the person pushed after setting it. The dry-run already prints the
  `review-secret` row and a repository secret can exist before its workflow, so SKILL.md step 3 has
  the person set it before the yes; on an upgrade it is already set.
- [The first `link` run starts before GitHub records the keyword link] → `link` fails naming the
  missing link and `gh run rerun`; the next installation run observes whether it happens (#117).
- [Tests need a consumer that is a git repository with an `origin`] → the `sandbox` fixture gets a
  bare `origin` and an initial commit on `main`; `snapshot` skips `.git`, and git state is asserted
  explicitly.

## Migration Plan

Consumers get it with the next release; a consumer already carrying the installation merges
nothing new (no file step planned, no onboarding step). Rollback reverts the release.
