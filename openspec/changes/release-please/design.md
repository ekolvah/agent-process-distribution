## Context

The observations this design rests on are in the proposal's **Why**: the dry run that parsed
none of the six commits on `main`, the repository's workflow permissions, the ruleset's two
required contexts, and the release-please-action README sentence on `GITHUB_TOKEN`. The
installer tests fix the current release at `2.0.0` in 35 places across seven files, and their
fixture tags this tree as `v2.0.0` and a recording stub as `v2.1.0`, so the first release PR
would fail its own `quality` check unless those tests follow `init.VERSION`.

## Goals / Non-Goals

**Goals:** one standard tool cuts every release; the three version places cannot disagree
on any head; no PR merges into `main` without a Conventional Commit type in its title; the
first release is `2.1.0` and carries the fixes merged since `v2.0.0`.

**Non-Goals:** delivery of a release to consumers (#199); a release workflow in consumer
repositories; a title check in consumer repositories.

## Decisions

**D1. release-please-action in manifest mode, release type `simple`.** Files:
`release-please-config.json` (`release-type: simple`, `include-component-in-tag: false`,
`extra-files`: `{type: json, path: .claude-plugin/plugin.json, jsonpath: $.version}`,
`{type: json, path: .claude-plugin/marketplace.json, jsonpath: $.plugins[0].version}`,
`{type: generic, path: skills/agent-process/scripts/init.py}`) and
`.release-please-manifest.json` `{".": "2.0.0"}`. `init.py` gets
`VERSION = "2.0.0"  # x-release-please-version`. The workflow
`.github/workflows/release-please.yml` runs on `push` to `main` with `contents: write`,
`issues: write`, `pull-requests: write`, pinned to `googleapis/release-please-action@v4`
like the other actions of the repository. The config and file names are the README
defaults, so the action takes no path inputs. Observed in the tool's documentation and
source (`docs/customizing.md`, `src/strategies/simple.ts`, `src/bin/release-please.ts` on
`main` of googleapis/release-please):
- `extra-files` takes `{"type": "json", "path": …, "jsonpath": "$.json.path.to.field"}`, and
  for the `x-release-please-version` annotation "we will try to replace the value on that
  line only";
- `simple` pushes `version.txt` with `createIfMissing: false` and `CHANGELOG.md` with
  `createIfMissing: true`, so the release PR adds `CHANGELOG.md` and no `version.txt`;
- `release-pr` without `--release-type` calls `Manifest.fromManifest(…, targetBranch,
  configFile, manifestFile)`, so the dry run of task 3.2 reads this branch's config.
That dry run is the observation of the three bumps before delivery.
*Alternatives:* a bespoke bump script or check — rejected by the issue and by
[Native first](../../specs/maintenance/spec.md); semantic-release — needs a Node release
config and publishes on every merge with no PR for the person to approve.

**D2. A fine-grained PAT, secret `RELEASE_PLEASE_TOKEN`.** Scope: this repository only,
Contents and Pull requests read/write. The release PR and its pushes are then the person's
events, so `agent-process / quality` and `agent-review / agent-review` run on them. The
workflow token stays read-only and the repository keeps
`can_approve_pull_request_reviews: false`.
This replaces the default `GITHUB_TOKEN` input with one the person supplies. Its failure
modes: missing, expired, or lacking a permission. What stops proving: nothing a test proves;
the release PR is simply not opened or updated. Catcher: the `release-please` run on the
push to `main` fails on authentication, a red run on the `main` commit in the Actions tab.
*Alternatives:* a GitHub App token — no expiry, but an App and two secrets for one
repository; `GITHUB_TOKEN` plus the person closing and reopening each release PR — a manual
step every release and a new Actions permission.

**D3. The PR title carries the type, and the squash title is the PR title.** SKILL.md Tasks
tells the planner to write `gh pr create --title "<type>: <change>"` in the Deliver task,
and Delivery shows that command. The repository setting `squash_merge_commit_title` moves
from `COMMIT_OR_PR_TITLE` to `PR_TITLE`; the REST reference reads "PR_TITLE - default to the
pull request's title. COMMIT_OR_PR_TITLE - default to the commit's title (if only one commit)
or the pull request's title (when more than one commit)". The repository reads
`squash_merge_commit_title: COMMIT_OR_PR_TITLE`, `allow_merge_commit: true`,
`allow_rebase_merge: true`; a merge commit or a rebase bypasses the PR title, so both are
turned off and squash stays the only method.
Without a check, a missing type would be silent: release-please leaves the commit out
(`commit could not be parsed: <sha> <title>` in a `--debug` run, as observed in the
proposal) and its run stays green. D7 makes it blocking.
A wrong but valid type (`docs` on a behaviour change) passes every check; the catcher is the
release PR's `CHANGELOG.md`, which lists no entry for that commit before the person merges it.
*Alternatives:* rebase merges, which keep the branch's conventional commits but put RED,
GREEN and archive commits on `main`; parsing the squash body, which release-please does not do.

**D4. The release PR links its issue by hand.** The `quality` step already fails a PR with
no linked issue and prints how to link one; the person links the release's issue in the PR's
Development panel (#197 for the first), requests `@codex review`, and merges. No spec and no
workflow change.
*Alternative:* exempting release PRs from the link step, which changes a requirement of
`review-and-merge` and both quality workflows.

**D7. The title is checked by `amannn/action-semantic-pull-request`, required by a ruleset of
its own.** `.github/workflows/pr-title.yml`: one job `pr-title` (the required context),
`permissions: pull-requests: read`, step `amannn/action-semantic-pull-request@v6` with
`GITHUB_TOKEN` and `types` `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. The action
README reads that the `types` input is "Configure which types are allowed
(newline-delimited)", and "If the workflow is required for merging, you need to ensure that
the you add a trigger type for `synchronize`". Trigger: `pull_request` with `opened`,
`edited`, `synchronize`, `reopened`; the README notes that `pull_request` "uses the current
branch's configuration but only functions for repository-based branches" — the same limit
as the repository's other `pull_request` workflows, and it lets this PR check its own title
before the workflow exists on `main` (`pull_request_target` would read `main` and never run
here). The release PR title `chore(main): release <version>` passes.
The requirement lives in a second ruleset `pr-title` (target `~DEFAULT_BRANCH`, one
`required_status_checks` rule, context `pr-title`, integration 15368), because
`activate_protection` converges the context set of `agent-process default branch`
([Activation converges one ruleset](../../specs/distribution/spec.md)) and would drop a
foreign context on its next run. GitHub's rulesets page: "if multiple rulesets target the
same branch or tag in a repository, the rules in each of these rulesets are aggregated."
A required context that no run reports stays pending and blocks the merge; the ruleset's
two present contexts read `integration_id: 15368` (`gh api
repos/ekolvah/agent-process-distribution/rules/branches/main`), the GitHub Actions app that
also reports `pr-title`, and a wrong id leaves the same never-satisfied context. So the person
creates the ruleset once the `pr-title` check has reported on this PR and reads the rule
back from the same endpoint.
A test in `test_reusable_workflows.py` fixes the job key, triggers and types, so a rename of
the job cannot silently orphan the required context.
*Alternatives:* commitlint on commits — checks branch commits, not the squash title that
lands on `main`; adding the context to the process ruleset — reverted by
`activate_protection`; a bespoke title check in `ci_check` — a standard action exists.

**D5. Installer tests follow `init.VERSION`.** The harness exposes `CURRENT = init.VERSION`
and `OTHER`, the next minor of it; the fixture tags `v{CURRENT}` with this tree and
`v{OTHER}` with the stub, and the stub prints `stub-release v{OTHER}`. Every literal
`2.0.0`/`2.1.0` in `conftest.py`, `init_harness.py`, `test_init.py`, `test_init_config.py`
and `test_init_remote.py` uses these. `test_skill_check.py` keeps its literals: they name
cache directories, not the release. Proof of the class: task 2.2 bumps the three places to
`2.1.0` in the worktree, runs `tests/publisher`, and reverts.

**D6. The first release is `2.1.0`.** This PR merges as `feat: release-please`, the first
commit since `v2.0.0` that release-please parses; with the manifest at `2.0.0` it proposes
`2.1.0`. The earlier six commits are in the released tree but not in the generated changelog;
the person may add them to the GitHub Release notes. No `release-as` pin is needed.

## Risks / Trade-offs

- The generated `CHANGELOG.md` could fail the document guard of `ci_check` → the release PR's
  own `quality` run shows it; fix through `changelog-sections` or a guard exclusion in a
  change of its own.
- The PAT expires → D2 catcher; the expiry date is the person's to track.
- A PR stays open while its title fails `pr-title` → the check's message names the allowed
  types; `gh pr edit --title` re-runs it through the `edited` event.

## Migration Plan

The PR report lists the person's one-time actions — the PAT and its secret, the three merge
settings, the `pr-title` ruleset — to take before this PR merges; no delivery task performs or asks for them. If the
secret is missing at merge, the D2 catcher shows it and a re-run after adding it recovers; the release PR appears on the next push to `main`, which
is this PR's merge. Rollback: delete the `pr-title` ruleset first — while it stands,
removing the workflow blocks every PR into `main` — then the workflow and config files, and
restore the settings; the tag `v2.0.0` and the version places stay valid.

## Open Questions

None.
