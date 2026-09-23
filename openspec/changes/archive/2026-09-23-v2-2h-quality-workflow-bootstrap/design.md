## Context

See `proposal.md` (Why). On `main` (`e73fa5b`), `ci.yml` job `quality` calls
`reusable-quality.yml@main` (no inputs, job `quality`, trusted default-branch driver). Its
context `quality / quality` is the one required by ruleset `23732345` (GitHub Actions
integration `15368`, strict), which issue 112 records as live state to preserve.
`agent-review.yml` is unchanged here. The v1 guard `check_branch_protection.py` names every
`pull_request` job by its caller key (job `name:` or key). It rejects two jobs with one key and
any PR job that is neither required nor in `NOT_REQUIRED` with a reason.
`tests/agent_process/test_branch_protection.py` runs it on the real workflows. The consumer
template already renders `setup`/`test` (archived `v2-2g-b-local-installer-lifecycle`, D4–D5).

## Observations

- https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows (read
  2026-09-23): "Each workflow run will use the version of the workflow that is present in the
  associated commit SHA or Git ref of the event." and "Some events also require the workflow
  file to be present on the default branch of the repository in order to run."
- https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows (read
  2026-09-23): "When you reference a reusable workflow in the same repository using `$/` or
  `./` (without `{owner}/{repo}` and `@{ref}`), the called workflow is from the same commit as
  the caller workflow."
- PR 151, run `35523639249`: a caller that passed new inputs to `reusable-quality.yml@main`,
  whose `main` version declared none, created zero jobs.
- Disposable public repository `ekolvah/agent-process-bootstrap-probe` (2026-09-23):
  - `main` `ea81bf6` had `ci.yml` job `quality` calling local `reusable-quality.yml` (job
    `quality`). Ruleset `23897425` required pull requests, deletion and non-fast-forward
    protection, and strict `quality / quality` from integration `15368`, with no bypass.
  - PR 1 (head `6ecd7a5`) added callee `quality.yml` (inputs `setup`/`test`, job
    `agent-process`) and caller `agent-process.yml` (job `quality`, `uses:
    ./.github/workflows/quality.yml`). On `opened` it got `quality / quality` (run
    `35909173919`) and `quality / agent-process` (run `35909173945`), both `SUCCESS`, with
    `mergeStateStatus` `CLEAN`. The person merged it through the ruleset without bypass:
    merge commit `cccc48a`, 2026-09-23T19:27:07Z.
  - PR 2 (head `79274e8`, a README edit) got both contexts on `opened` without close/reopen:
    `quality / quality` run `35909442544` and `quality / agent-process` run `35909442456`.
  - A reusable job's check name is `<caller job> / <callee job>`, as both runs show.
- PR 151 reported no check until a `reopened` event. The probe does not reproduce that for a
  caller present when the PR opens. This design asserts no cause for it.

## Goals / Non-Goals

**Goals:** the callee and a caller exist on `main` and report on every later PR, while the
required set and every v1 workflow stay as they are.

**Non-Goals:** ruleset or classic-protection writes (issue 154), deletion of v1 workflows and
of the v1 guard (issue 115), the `v2.0.0` tag (the person's action), an OpenSpec validation
step in the callee (the consumer's `test` names its complete command, as the installer's
config pointer says).

## Decisions

### D1. A new callee file, not a second mode of `reusable-quality.yml`

`quality.yml` declares `setup` (optional, default `""`) and `test` (required). It has one job
`quality` with these steps: verify the PR links its issue (the v1 step, unchanged), then
`actions/checkout@v4` (default ref, which is the PR merge commit as in v1), then
`actions/setup-python@v5` with Python 3.12 (the v1 environment where `ci_check.py` passes), then
`setup` if it is not empty, then `test`. `run: ${{ inputs.test }}` interpolates only the
caller file's literal from the same commit, never event data.

Alternative: make `test` optional in `reusable-quality.yml` and fall back to the trusted
driver when it is empty. v1 `ci.yml` would keep working, but one file would carry two modes
until issue 115, and the required context's callee would change in this PR. Rejected because
the person chose the new file (2026-09-23).

### D2. Caller job `agent-process`, callee job `quality`

The context is `agent-process / quality`. It differs from the required `quality / quality`,
so a ruleset rule cannot be satisfied by the wrong workflow. Its caller key `agent-process`
does not collide with `ci.yml`'s `quality` in the v1 guard. The consumer template uses the
same job key, so issue 154 activates one name for the publisher and for consumers. The
alternative, caller `quality` with callee `agent-process` (the probe's shape), trips the
guard's duplicate-key rule on this repository. Consumers would then report a context that
the publisher cannot.

### D3. The publisher caller uses the same-commit path

`.github/workflows/agent-process.yml` runs on `pull_request` with default types and
read-only `contents`, `pull-requests`, and `issues`. Its job `agent-process` uses
`./.github/workflows/quality.yml` with `setup: python -m pip install -r
.agent-process/requirements.txt -r .agent-process/requirements-dev.txt` and `test: python
.agent-process/scripts/ci_check.py`.

`@main` is rejected. On this PR, `main` has no `quality.yml`, so the new check would fail on
the very PR that lands it. The `@main` pin also adds no trust: for `pull_request` the caller
comes from the event commit (Observations), and a PR can already rewrite the caller.
Consumers keep `@v<version>`.

**Trust boundary.** The new context runs the PR's own `ci_check.py`, while v1 runs the
default-branch driver. This change replaces nothing and drops no guard. The new context is
not required, and `quality / quality` still runs the trusted driver on every head.
A PR that weakens the checks `agent-process / quality` runs is caught by the required
`quality / quality` run on the same head (v1 `reusable-quality.yml`, driver from the
default branch). Whether this stays a proof once the new context becomes required is issue
154's decision, and its design must list the catcher.
The `distribution` delta states this as a modified requirement: the trusted driver binds a
required context, and a PR-owned driver stays non-required until its catcher is named.

### D4. The template follows

`skills/agent-process/templates/agent-process.yml` changes `uses:` to
`.../quality.yml@v${version}` and its job key to `agent-process`. `with:` stays `{setup,
test}`, which is the interface D5 of `v2-2g-b` pinned for this issue.

### D5. The v1 guard records the new job

`NOT_REQUIRED["agent-process"]` gets the reason "bootstrap: required only after issue 154
activates it". `REQUIRED_CONTEXTS` is unchanged. The real-workflow test in
`test_branch_protection.py` then proves offline that the declaration is complete.

## Risks / Trade-offs

- [Every PR runs the quality command twice until issue 115] → accepted. The runs are
  independent and not required.
- [A consumer cannot run the template before the `v2.0.0` tag exists] → unchanged from
  `v2-2g-b`. `test_caller_inputs` pins the rendered path and job, and the tag is the person's
  action after issue 154.
- [A red `agent-process / quality` does not block merge] → it is visible on the PR, and the
  required v1 context gates the same head.

## Migration Plan

Merge. Nothing else changes: no ruleset or protection write. The PR report records the
probe run ids above, this PR's run ids for both contexts, and a read-back of ruleset
`23732345` (rules and required contexts) before the merge. After the merge, the next PR's
`agent-process / quality` run is the observation issue 154 preflights on. Rollback: revert
the PR. No required context references the new files.
