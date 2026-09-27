## Context

Two carriers deliver the repository to a consumer (proposal, Why): the plugin marketplace
clone with its cache, and the installer's user-scope checkout. The observation of the
platform's `sparsePaths` is recorded in the proposal.

## Decisions

**D1 — The marketplace source carries `sparsePaths`.** The rendered source becomes
`{"source": "github", "repo": …, "ref": "v<version>", "sparsePaths": [".claude-plugin",
"agents", "commands", "skills/agent-process"]}`. The plugin entry keeps `"source": "."`: with a
sparse marketplace clone, `"."` is the sparse tree (observed, proposal). No file moves, so
every `skills/agent-process/…` path in this repository, the plugin agents'
`${CLAUDE_PLUGIN_ROOT}` fallback and the skill check (`skills/agent-process/SKILL.md` in the
install) stay valid. The key stays one of the two owned settings keys, so an installed
consumer's entry without `sparsePaths` is replaced by the owned render, as a `ref` change is
today. This repository's `.claude/settings.json` names the same list (dogfood).
Alternatives: move the package into a `plugin/` subdirectory and point `source` there —
rejected: it rewrites every `skills/agent-process/` path of the repository and still leaves the
marketplace clone whole; a separate release ref holding only distributed paths — rejected: a
new build step in the release pipeline, for what a platform field does.
Residue: cone mode keeps the root files (proposal, Why); they are small and the plugin loads
none of them.

**D2 — No user-scope checkout.** `init --confirm` of another version clones the tag
(`--depth 1`) into a temporary directory and hands off from there, the path `--dry-run` takes
today; the directory is removed after the child exits. The `checkout` step, `Context.checkout`
and the helper only it uses (`_same_path`) are removed; the same-version run starts at
`openspec`. Nothing reads the checkout since remove-codex (remove-codex D5 named this
alternative). An existing `~/.agent-process/distribution` is left in place: the installer
never deletes a path it no longer uses. `Host.home`/`Context.home` stay as the injected
user-profile boundary with no current reader, and no `Path.home()` appears outside `main()`:
a future profile write then goes through the injected home, where the sandbox test of
`Confirmed install of the running release` sees it.
Dropped guard: the checkout conflicts (dirty, other origin, not a Git checkout, non-directory
parent). They protected only the persistent checkout, which no longer exists; a temporary
clone has no prior state to conflict with. A failing clone still raises `InstallError`
(exit 1) before any consumer write — the same path as `--dry-run`'s clone, covered by the
existing dry-run tests.
Retry (`Init reconciles from observable state`): with no persistent write of its own, the
upgrade run's retry is the requested release's; the retry test keeps the same-version
scenarios, whose labels lose `checkout`.

## Risks / Trade-offs

- A machine that already knows the marketplace keeps its full clone until the marketplace
  is removed and added again (#184 class) → the consumer gets the sparse tree on the next
  fresh add; nothing breaks meanwhile.
- A future plugin component root outside the four paths would be missing from installs →
  the publisher test of D1 derives its expectation: every plugin component root the
  repository has at its top level under the platform's default layout (`commands`, `agents`,
  each `skills/<name>`, `hooks`, `output-styles`, `.mcp.json`, `.lsp.json`) plus
  `.claude-plugin` is covered by a `sparsePaths` entry, in the rendered source and in this
  repository's settings, and every entry exists.

## Migration / Rollback

Rollback is a revert of the PR: the next release renders the source without `sparsePaths`
and the installer recreates the checkout on its next confirm.
