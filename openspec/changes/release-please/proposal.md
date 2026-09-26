## Why

The release version lives in three places — `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json` and `VERSION` in `skills/agent-process/scripts/init.py` —
and no procedure moves them. The tag `v2.0.0` (`75c5309`) was set by hand, and `main` still
says `2.0.0` after four more merges (#189, #191, #192, #200), so one version string names two contents
and release drift compares equal strings (#190). A consumer cannot tell which process it runs,
and the fixes after the tag reach no one (#197).

Observed, not inferred:

- A read-only run of the standard tool on this repository,
  `npx -y release-please@17 release-pr --repo-url=ekolvah/agent-process-distribution
  --release-type=simple --dry-run --debug`, found the release `v2.0.0` at `75c5309` and
  then `commit could not be parsed: c109c29… install-activation-order (#200)` for all six
  commits after it, ending `Would open 0 pull requests`. The squash merge takes the PR title,
  and the procedure titles a PR with the bare change name
  ([SKILL.md Delivery](../../../skills/agent-process/SKILL.md#delivery)), so the issue's
  premise that Conventional Commits are already used holds for branch commits only, not for
  the commits on `main` that release-please reads.
- The repository's workflow permissions read
  `{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}`, and its
  ruleset requires `agent-process / quality` and `agent-review / agent-review` on every PR.
  The release-please-action README states: "When you use the repository's `GITHUB_TOKEN` to
  perform tasks, events triggered by the `GITHUB_TOKEN` will not create a new workflow run."
  A release PR opened on the workflow token would never receive its required contexts.

## What Changes

- A `release-please` workflow on push to `main` runs `googleapis/release-please-action` in
  manifest mode with a fine-grained PAT (`RELEASE_PLEASE_TOKEN`), so its release PR runs the
  required checks. Merging the release PR creates the tag `v<x.y.z>` and the GitHub Release.
- `release-please-config.json` bumps the two JSON files through `extra-files` with
  `jsonpath`, and `init.py` through an `x-release-please-version` marker;
  `.release-please-manifest.json` starts at `2.0.0`, the release the tool already found.
- The Deliver task titles the PR `<type>: <change>` with a Conventional Commit type the
  planner writes into `tasks.md`, and the repository's squash commit title is set to the PR
  title, so the commit on `main` carries the type. A required `pr-title` check
  (`amannn/action-semantic-pull-request`) in a ruleset of its own fails a PR whose title has
  no allowed type.
- `test_version_drift` stops pinning `"2.0.0"`: every version place equals the manifest.
  The installer tests stop assuming the current release is `2.0.0`.
- The release PR links its issue by hand, as the `quality` step already asks (the first one
  links #197). This PR is `feat: release-please`, so the first release PR ships `2.1.0`.
- ADR 0030 records the decision. Delivery to consumers is out of scope (#199).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: adds how a release is cut and where its version lives.
- `implementation`: adds the Conventional Commit type in the PR title.

## Impact

Added:
- `.github/workflows/release-please.yml`
- `release-please-config.json`
- `.release-please-manifest.json`
- `.github/workflows/pr-title.yml`
- `.agent-process/docs/adr/0030-releases-go-through-release-please.md`

Edited:
- `skills/agent-process/scripts/init.py` — the marker on `VERSION`
- `skills/agent-process/SKILL.md` — PR title in Tasks and Delivery
- `tests/publisher/test_plugin.py` — `test_version_drift`
- `tests/publisher/conftest.py`, `init_harness.py`, `test_init.py`, `test_init_config.py`,
  `test_init_remote.py` — current and other release derived from `init.VERSION`

Removed: none.

Outside the repository: the secret `RELEASE_PLEASE_TOKEN` (created by the person) and the
settings `squash_merge_commit_title=PR_TITLE`, `allow_merge_commit=false`,
`allow_rebase_merge=false`, and a second ruleset `pr-title` requiring the `pr-title` check. The first release PR adds `CHANGELOG.md` and
changes the three version places; that PR is release-please's, not this change's.
