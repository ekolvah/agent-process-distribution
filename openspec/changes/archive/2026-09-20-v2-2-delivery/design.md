## Context

See proposal.md — Why and the four delta specs. The current repository has a metadata-only
Claude plugin plus the `architect-reviewer` agent, six OpenSpec skills for each carrier,
two workflow callers, two reusable workflows, a Python control plane under
`.agent-process/`, and classic protection that requires `quality / quality` and
`agent-review / agent-review`. There is no consumer installation path.

The preceding changes settle most platform choices. ADR 0027 records that the template
Project can be copied with its fields, views, and enabled workflows but is initially
private and unlinked; its workflow settings have no write API. It also records that the
PR→issue link is available synchronously enough for the quality job, `check_red` owns its
pytest invocation/report, and `wait_for_pr` owns check settling.

Platform observations used by this design:

- On 2026-09-20,
  `npx -y @fission-ai/openspec@1.13.0 init --tools 'claude,codex' --no-animation`
  in a fresh Git repository created `openspec/config.yaml`, six Claude commands/skills,
  and six Codex skills, and created no hook, workflow, settings, or project file.
- The current OpenAI skill documentation states that a skill directory may contain an
  optional `scripts/` directory, user skills live under `~/.agents/skills`, and Codex
  follows symlinked skill directories:
  https://developers.openai.com/codex/skills ("Where Codex loads local skills", read
  2026-09-20). This supersedes issue 112's older
  `$CODEX_HOME/skills` premise; local `codex-cli 0.153.4` is the observed installed CLI.
- GitHub's event reference says `pull_request_target` runs at the last commit on the
  default branch, while a `pull_request` workflow can address
  `github.event.pull_request.head.sha`:
  https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows.
  The caller therefore stays on `pull_request`; no credential-bearing job moves to
  `pull_request_target`.
- GitHub's ruleset troubleshooting reference says required status checks do not account
  for workflow, matrix, or event trigger type:
  https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/troubleshooting-rules.
  Required workflows are an organization/enterprise ruleset facility, not a portable
  repository rule for the personal-account consumer:
  https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets.
- GitHub's repository-ruleset REST reference defines `active` enforcement, the
  `~DEFAULT_BRANCH` condition, pull-request, deletion, non-fast-forward and required
  status-check rules, including the context, integration id and strict-latest-code fields:
  https://docs.github.com/en/rest/repos/rules ("Create a repository ruleset", read
  2026-09-20). It also provides the list/create/update/read endpoints used by the
  unique-name upsert and read-back.
- Live reads on 2026-09-20 show this repository has no ruleset and classic protection has
  strict checks `quality / quality` and `agent-review / agent-review`, both under GitHub
  Actions app id `15368`, with admin enforcement, force pushes and deletions blocked.
- The issue-112 pull request's Actions run `35523639249` ended in `startup_failure` with zero jobs because the
  new caller passed `setup` and `test` to `reusable-quality.yml@main` while the unmerged
  default-branch callee still exposed the old no-input interface.

## Goals / Non-Goals

**Goals:**

- Keep one procedure and one script implementation for both carriers.
- Make the consumer repository footprint small, inspectable, and repeatably installable.
- Use GitHub/OpenSpec/agent-native update paths rather than a new synchronization system.
- Make every conflict or unavailable prerequisite visible without ingesting a secret.

**Non-Goals:**

- Authenticating a consumer-editable caller on personal-account repositories; the owner
  selected name-bound quality plus human inspection where required-workflow rules are not
  available.
- Replacing a target repository's own quality policy, package manager, or editor feedback.
- Migrating an existing consumer, deleting all v1 source, or adding coverage enforcement.

## Decisions

### D1. One plugin skill is the portable procedure

The repository root remains the marketplace plugin source. Add
`skills/agent-process/SKILL.md` with `proposal`, `tasks`, architect-review, and `install`
sections. Move the seven standalone scripts used by those sections under
`skills/agent-process/scripts/`; none imports another process module today, so the skill
is self-contained. `commands/init.md` is the thin Claude command; the existing
`agents/architect-reviewer.md` remains the fresh-context Claude reviewer. The plugin ships
no hook file.

`openspec/config.yaml` keeps the repository-specific `context`, while each artifact rule
becomes a short pointer to the matching section of `agent-process`. The installed
`config.yaml` owns only a marker-delimited pointer block; consumer context outside the
markers survives an update. An unmarked conflicting `rules:` key is reported instead of
rewritten.

Alternative: retain full rules in every consumer. Rejected because every rule change
would again be a copied-file merge. Alternative: keep scripts under `.agent-process` and
walk out of a linked skill. Rejected because the linked directory is the portable unit;
the optional `scripts/` directory is the documented skill layout.

### D2. Codex gets an updateable checkout and a user-scope link

The Codex install step keeps a checkout of this repository at the process tag under a
user-owned process directory and makes `~/.agents/skills/agent-process` point to its
`skills/agent-process` directory (a symlink on Unix, a directory junction on Windows).
On update it refuses a dirty checkout or a link with another target, fetches the requested
tag, and changes the checkout only after those checks. When the requested version differs
from the running installer's version, the bootstrap hands the same literal arguments to
that tag's `init.py` and returns; a private guard makes a version mismatch fail instead of
recursing. This gives `SKILL.md`, `scripts/`, templates, and installer logic one shared
version and follows the current OpenAI path rather than the stale `~/.codex/skills`
assumption.

The bootstrap remains agent-native: Claude installs the marketplace plugin; Codex uses
its skill installation/bootstrap path to obtain the init skill once. `init` owns all
subsequent repository and linked-checkout updates.

Alternative: copy only `SKILL.md`. Rejected because its scripts would drift. Alternative:
link into the Claude plugin cache. Rejected because plugin cache paths and replacement are
host-owned and are not a stable Codex update target.

### D3. `init` is a deterministic, dry-runnable composition

`skills/agent-process/scripts/init.py` is stdlib-only and exposes a test seam around
subprocesses and the user home. The Claude command and Codex skill collect required
`--test` and optional `--setup` strings, run `--dry-run`, show the complete plan, then ask
once before rerunning with `--confirm-remote`. Every subprocess capture uses UTF-8 and
preserves `None` rather than converting it to an empty string.

Local steps, in order:

1. Run pinned OpenSpec `init --tools claude,codex`.
2. Insert or update the marker-owned pointer block in `openspec/config.yaml`.
3. Write the owned `.github/workflows/agent-process.yml` from the template, substituting
   the plugin version and the literal setup/test commands.
4. Create the process Dependabot entry when the file is absent or already marker-owned;
   otherwise print the entry and report a conflict.
5. Merge only `extraKnownMarketplaces.agent-process-marketplace` and
   `enabledPlugins["agent-process@agent-process-marketplace"]` into
   `.claude/settings.json`, preserving every other key.
6. Update the Codex checkout and user skill link.

Confirmed remote steps, in order:

7. Upsert the repository ruleset by its unique process name (zero matches → POST, one →
   PUT, several → error) from `ruleset.json` after substituting the default branch.
8. Read linked Projects. With none, run
   `gh project copy 4 --source-owner ekolvah --target-owner @me --format json` with a
   repository-specific title and `gh project link`. Before copying, reuse an unlinked
   exact-title Project left by a failed link; several matches are a conflict. With exactly
   one linked Project, reuse it; with several, report them and stop rather than choose. Do
   not verify or mutate fields/workflows.
9. Print `gh secret set CLAUDE_CODE_OAUTH_TOKEN`, the Codex automatic-review setting
   instruction, and the Project visibility/workflow checklist. Secret contents and UI
   choices never enter the script.

Each step prints `written`, `unchanged`, `planned`, or `conflict`; the process exits
non-zero on any conflict or command failure. A second same-version run has no local diff
and discovers the existing remote objects.

Alternative: prose instructs the agent through each native command. Rejected because
ordering, conflict rules, and partial-run recovery are deterministic and need unit tests.

### D4. The exact installed file set is closed

Templates are limited to `agent-process.yml`, `dependabot.yml`, `config.yaml`,
`settings.json`, and `ruleset.json`. OpenSpec owns its generated `.claude/`, `.agents/`,
and `openspec/` files. There is no hook payload, `AGENTS.md` fragment, report path, copied
review contract, process root, or process test. Publisher tests enumerate both the
templates and a temporary initialized repository against this allow-list.

The publisher may retain repository-only keys in `.claude/settings.json` and v1 files
until their scheduled cleanup; the template test proves none leaks into `settings.json`.

### D5. One caller contains quality and the direct Claude action

`.github/workflows/agent-process.yml` runs on `pull_request` and contains:

- `quality`, a call to
  `ekolvah/agent-process-distribution/.github/workflows/reusable-quality.yml@v<version>`
  with the literal `setup` and `test` inputs;
- `review`, a normal job using `anthropics/claude-code-action@v1` directly with
  `CLAUDE_CODE_OAUTH_TOKEN`, a small review prompt, and no process parser or outcome gate.

The reusable quality workflow owns the PR-link read, checks out the PR head, runs setup
when non-empty, runs test, and runs pinned strict OpenSpec validation when `openspec/`
exists. In consumers, its file and steps come from the immutable release ref the caller
pins. The publisher's own caller uses the repository-local reusable workflow and passes
its current dependency install plus `ci_check.py` as setup/test: before the first release
tag exists, that is the only stable merged configuration that both compiles and exercises
the changed callee. The publisher-only loss of an immutable callee is caught by terminal
inspection of every current-head workflow diff before the person merges.

Codex review is not requested by the workflow or delivery procedure. The person enables
the app's automatic review setting from `init`'s printed instruction. Both reviews are
advisory; only quality is required.

The inherited thread resolver keeps its settled-current-head precondition, resolves the
exact addressed older-head P0/P1 thread, and replies without re-running the combined
workflow. Re-running would start another advisory Claude review on an unchanged head
after the prescribed wait even though required quality does not depend on thread state.

Alternative: keep `reusable-agent-review.yml`. Rejected by the owner review: the official
action can be called directly, and the wait/parser/fallback/enforcement code is bespoke
review control. Alternative: `pull_request_target` for a trusted caller. Rejected by the
observed base-SHA binding and the credential risk. Alternative: keep the publisher on
`@main` until tagging. Rejected by run `35523639249`: GitHub validates the caller inputs
against the old default-branch interface and creates no job. A temporary tag or branch is
also rejected because the merged caller would depend on a mutable or disposable ref.

### D6. The ruleset requires quality by name and protects the ref

`ruleset.json` uses GitHub's repository-ruleset API body: active, branch target, default
branch condition, no bypass actors, `pull_request`, strict `required_status_checks` for
`quality / quality` with integration id `15368`, `non_fast_forward`, and `deletion`.
Required-workflow rules are not emitted conditionally because there must be one portable
JSON for personal and organization repositories.

This deliberately proves only that a GitHub Actions check with that name succeeded on the
head. It does not authenticate the caller file. The terminal delivery handoff therefore
includes `gh pr diff <PR> --name-only` and inspection of every
`.github/workflows/**` change on the current head before the person merges. An
organization may layer a required-workflow rule on top without changing the installed
repository ruleset.

### D7. Replacing the trusted driver and dropping hooks has explicit proof loss

The caller's setup/test strings replace selection by the trusted default-branch
`ci_check` registry for consumers.

- A typo, missing executable, bad quoting, or failing setup/test command is caught by the
  `quality / quality` run on that PR head; the shell output and non-zero exit are the
  visible result.
- A command that succeeds while omitting a repository gate is not detected by the
  reusable workflow. The exact terminal step is inspection of the current-head workflow
  diff before the person merges. There is no stronger portable machine proof on a
  personal repository; this is the explicit owner-selected trust boundary, not a claim
  that quality authenticated its caller.
- A PR that rewrites the caller can change the input or attempt to emit the same context.
  The pinned callee is still immutable to that PR, but the name-bound ruleset cannot prove
  which caller selected it. The same current-head workflow-diff inspection is the only
  catcher unless an organization required-workflow rule is added.

The plugin also drops the portable PreToolUse/PostToolUse/Stop guard set.

- Direct/force/delete updates of the default branch are caught by the active ruleset on
  the attempted ref update.
- Lint and tests are caught only if the consumer's declared test command runs them; there
  is no replacement for immediate post-edit feedback.
- Navigation denial, force pushes away from the default branch, and local denial of
  `gh pr merge` stop being process proofs. The person-only merge boundary and scoped
  repository instructions remain, but the design does not mislabel them as a hook.

Finally, removal of the required review workflow loses proof that one process-classified
review exists and that P0/P1 threads are closed. The direct Claude job's failure remains a
visible check and both apps' comments remain on the PR, but quality does not catch their
absence or outcome; current-head review inspection at the person merge step is the
accepted boundary.

### D8. Release identity is one version

Set the plugin and marketplace versions to `2.0.0`; templates derive `v2.0.0`. A publisher
test compares both manifests and every pinned template. The person creates the tag after
the merge; Dependabot's `github-actions` entry proposes future reference bumps. A tag is
never reused during rollback.

### D9. The publisher transitions without losing its current PR gate

The implementation PR cannot delete the old review caller while classic protection still
requires `agent-review / agent-review`. Before the final archived head is pushed, and only
after the person confirms the live plan, the implementer:

1. installs and reads back the active ruleset requiring quality;
2. removes only `agent-review / agent-review` from classic protection, leaving its strict
   quality context and other protections in place;
3. verifies the read-back shows the active ruleset plus classic `quality / quality`;
4. then archives, pushes, and opens the PR with the new one-caller workflow.

The duplication of the quality rule is safe and remains until issue 114 removes the
classic mechanism. Rollback restores the old required context before reverting the caller
deletion, then deletes the new ruleset; the release tag is not created.

## Risks / Trade-offs

- [The initial Codex bootstrap installs a copied skill rather than the final link] → the
  first `init` normalizes it only after showing the link/checkout plan; a foreign target
  is a conflict, never removed automatically.
- [A partial `init` leaves some local or remote steps complete] → every step is idempotent
  and reports its state, so rerunning continues; multiple matching rulesets or Projects
  stop rather than guess.
- [The template Project is private or has workflows that need UI changes] → `init` prints
  the visibility and exact built-in-workflow checklist; it does not claim to verify or
  mutate API-read-only workflow settings.
- [Fork PRs do not receive the Claude secret] → the review job fails visibly or is skipped
  under platform policy, but it is advisory; quality remains the ruleset gate.
- [A required context can be spoofed by another GitHub Actions workflow] → D6/D7 state the
  name-bound limit and terminal current-head workflow-diff inspection; organization users
  may add a required-workflow rule.
- [Removing immediate hooks reduces feedback] → this is the explicit owner decision; the
  caller's declared quality command is the portable deterministic feedback.

## Migration Plan

1. Add RED publisher tests for the skill/plugin layout, closed install footprint, init
   idempotency/conflicts, one-caller workflow, ruleset, Project composition, version
   coupling, and moved script paths.
2. Move the standalone scripts, add the shared skill and pointer rules, and keep the
   publisher's canonical procedure documentation executable at the new paths.
3. Add `init`, templates, plugin metadata/settings, and their temporary-repository tests.
4. Replace workflow callers/review callee, update reusable quality, and add Dependabot.
5. Update ADR 0027 and installation/runtime docs, then run strict OpenSpec validation and
   the full CI command.
6. Perform D9's confirmed protection transition, archive the change, open the PR, and use
   the new caller/review behavior on its final head.
7. After human merge, the person creates `v2.0.0`; issue 117 is the first consumer
   installation. A defect found there is a new change, not an untracked edit here.

There are no open design questions: later consumer observations may reveal a defect, but
the install footprint, trust boundary, and review mode are owner decisions recorded by
issue 112.
