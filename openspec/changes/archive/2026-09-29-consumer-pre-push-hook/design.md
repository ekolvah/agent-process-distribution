## Context

The observations this design rests on are in proposal.md **Why**. The quality command of a
repository is its declaration `.github/agent-process-quality.json` (#249), parsed by
`skills/agent-process/scripts/quality.py`'s `read`, which CI (`quality.yml`), `check_red` and
`init` already share. CI runs `setup`, then `test` (per check with `checks`) through `eval` in
bash. `init` owns the Dependabot entry by a marker block (`_dependabot_text`): a file without the
block is a `conflict`.

## Decisions

**D1. A pre-commit hook repository, not a bespoke hook.** pre-commit is the standard for
distributing git hooks: a hook repository declares hooks in `.pre-commit-hooks.yaml`, and a
consumer references one by URL and `rev`. The publisher declares
`quality` there with `language: python`, `entry: agent-process-quality`, `pass_filenames: false`,
`always_run: true`, `stages: [pre-push]`; the consumer block pins `rev: v<version>`, like the
review and quality callers, and Install moves it (*Dependabot leaves process refs to Install*).
Alternatives:
- `repo: local` with the command baked in (#188's plan): at install time a repository without
  tests declares nothing (*Init asks for no quality command*), and a later declaration would not
  reach the baked copy.
- `repo: local` calling the `agent-process` launcher: it is on `PATH` only in Claude's Bash tool,
  so a push from a terminal would fail.
- `language: unsupported_script` with a `python3` shebang: `python3` resolves to the Windows
  Store stub (Why). `language: python` runs on the interpreter pre-commit itself runs on.
- Copying the publisher's bash hook: the footprint forbids publisher files in the consumer, and
  that hook runs this repository's `ci_check.py`.

**D2. The entry is a mode of `quality.py`.** `hook()` (console script `agent-process-quality`,
and `quality.py --hook` for this repository) calls `read(Path.cwd())`; pre-commit runs entries
from the repository root (Why). A declaration → `bash -c <test>`, exit code passed through,
output not captured. Absent → one stderr line, exit 0, as CI's warning does. Malformed →
the `read` error on stderr, exit 1, as CI fails. Only `test` runs once: `setup` installs
dependencies CI needs on a fresh runner, and `checks` only splits CI jobs. No new script: the one
parser of the declaration stays the one reader.

**D3. `bash`, as CI.** The declared command is written for CI's bash `eval`; running it through
`cmd.exe` on Windows would change its meaning. `shutil.which("bash")` inside a git hook finds
Git's `/usr/bin/bash` first (Why). Not found → exit 2 naming it.

**D4. The repository-local git environment and the hook environment are removed.** From a
linked worktree git hands the hook `GIT_DIR`, and pre-commit forwards it (Why); a test that
creates git repositories would act on the pushed one. The entry removes every name
`git rev-parse --local-env-vars` prints, and exits 2 when that command fails or prints nothing,
as `pre-push:6-16` does today. pre-commit's `language: python` puts the hook env first on `PATH`
and sets `VIRTUAL_ENV` (Why), so a declared `python …` would run an interpreter holding only
this package. The console script `agent-process-quality` is reached only from that env, so
only it drops from the child's `PATH` the directory of its own `sys.executable` and drops
`VIRTUAL_ENV` when it equals `sys.prefix`. `quality.py --hook` (this repository,
`language: unsupported`) keeps them: pre-commit applies no env patch there, so they are the
pusher's own interpreter and venv. A `VIRTUAL_ENV` the pusher had set is overwritten by
pre-commit on the console-script route and not restored; the pusher's own venv stays on `PATH`.

**D5. Packaging for pre-commit.** `language: python` installs the hook repository with
`pip install .`. `pyproject.toml` gains `[build-system]` (setuptools), `[project]` (name
`agent-process-hooks`, `version`, no dependencies) with `[project.scripts]
agent-process-quality = "quality:hook"`, and `[tool.setuptools]` `py-modules = ["quality"]` with
`package-dir = {"" = "skills/agent-process/scripts"}`: `quality.py` imports only the standard
library. `release-please-config.json` bumps `$.project.version` as a `toml` extra file, so the
version matches the tag; `test_version_drift` reads that version, so a release PR whose `toml`
updater missed it fails visibly. `[tool.ruff]` already pins `target-version`, so
`requires-python` changes no lint.

**D6. Init owns a marker block, as for Dependabot.** The template
`skills/agent-process/templates/pre-commit-config.yaml` is
`default_install_hook_types: [pre-push]` and `repos:` holding the marker block with the remote
entry, `rev: v{version}`. `_dependabot_text` becomes one helper for both files, taking the
rendered text: a fresh file gets the whole template; a file with the block gets the block
replaced; a file without it is a `conflict`, which the person resolves by adding the markers
around nothing. `default_install_hook_types` outside the block stays the consumer's, so the
manual row names `--hook-type pre-push` explicitly. Whole-file ownership was rejected: a
consumer's own hooks are common in that file.

**D7. This repository runs the entry from its own commit.** Its `.pre-commit-config.yaml` has a
`repo: local` hook `quality`, `language: unsupported`,
`entry: python skills/agent-process/scripts/quality.py --hook`, same flags and stage, and
`default_install_hook_types: [pre-push]`, as the publisher quality caller runs `./`. The
consumer route (manifest + packaging + pre-commit) is proven by a test that runs
`pre-commit try-repo <this repository> quality --hook-stage pre-push` in a temporary consumer
whose declared `test` prints `python`'s `sys.prefix`; `pre-commit` joins the dev requirements for
it. This repository's wiring is proven by a test that parses its `.pre-commit-config.yaml`.

## Dropped guards

The bash hook and its tests go. What each proved, and the catcher now:

- *Runs `ci_check` alone*: this repository's declared `test` is `ci_check`
  (`.github/agent-process-quality.json`); D2's test runs a declared command once and no `setup`;
  the D7 parse test proves this repository's pre-push runs the entry.
- *Clears the local git environment*, *discovery failure exits 2*: D4, tested on the entry.
- *Exit code propagated*, *stderr not swallowed*: D2, tested on the entry.
- *Interpreter discovery (`.venv/Scripts/python`, `.venv/bin/python`, `py -3.12`)*: gone. The
  declared `test` names `python`, as CI does, and D4 leaves it the pusher's (try-repo test); a
  `python` without the dev tools makes `ci_check` exit 2 and the push is refused visibly. Failure mode: a developer whose venv is not active sees
  the refusal and activates it.
- *LF-only hook file* (`.agent-process/.gitattributes`): no bash file remains.

## Risks / Trade-offs

- A clone that never runs the per-clone step runs no hook, silently, as today. The `manual
  pre-push` row is the signal; a session-start check of the installed shim is not in scope.
- **This repository's clones after merge** (BREAKING in proposal.md): `core.hooksPath` still names
  `.agent-process/.githooks`, now absent, so git runs no pre-push hook, and `pre-commit install`
  refuses until it is unset (Why). The step changes shared git config of every worktree, so the
  person runs it after merge; the PR report names it. Until then, the Verify group on the
  implementer's head and `agent-process / quality` on every PR head remain the catchers.
- A branch without `.pre-commit-config.yaml` pushed from a clone with the pre-commit shim fails
  with pre-commit's `No .pre-commit-config.yaml file was found`: visible; merging main fixes it.
- The consumer's first push after `pre-commit install` builds the hook environment from GitHub
  (network, some seconds); pre-commit caches it per `rev`.
- The try-repo test needs network for pip's build isolation; CI has it.
- pre-commit on an interpreter older than 3.12 fails to install the hook env
  (`requires-python`): visible at the first push, with pip's error.

## Migration / Rollback

Consumers get the block with the next release through Install; `init --dry-run` shows the
`pre-commit` step and the `manual pre-push` row before any write. Rollback: revert the PR; a
consumer's block then references a released `rev`, which keeps working, and the person removes
the block by hand if wanted. This repository's clones: `git config --unset-all core.hooksPath`,
then `pre-commit install --hook-type pre-push`.
