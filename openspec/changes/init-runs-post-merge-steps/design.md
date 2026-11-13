## Context

Today `init` only reports the post-merge state, as the `manual protection`,
`manual agent-identity` and `manual auto-merge` rows (`manual.py:153-166`).

## Standard approach

- The writes are the platform's own APIs, through `gh`: rulesets
  (https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset), `allow_auto_merge`
  (https://docs.github.com/en/rest/repos/repos#update-a-repository), collaborators and
  invitations (https://docs.github.com/en/rest/collaborators/collaborators#add-a-repository-collaborator,
  https://docs.github.com/en/rest/collaborators/invitations#accept-a-repository-invitation —
  the invitee lists `GET /user/repository_invitations` and accepts by `PATCH`), Project roles,
  and `gh auth token --user <login>` (https://cli.github.com/manual/gh_auth_token).
- Observed (gh 2.87.3, 2026-11-13): GraphQL introspection shows `updateProjectV2Collaborators`
  taking `projectId` and `collaborators: [{userId, teamId, role}]` with `ProjectV2Roles`
  `NONE | READER | WRITER | ADMIN`, and `ProjectV2.viewerCanUpdate`;
  `gh auth status --json hosts` lists each github.com account with `login` and `active`;
  this repository's bot, given the Project's Writer role in the Project's settings (a Project
  role has no invitation to accept,
  https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects),
  reads with its token `viewerCanUpdate` true and `viewerPermission` `WRITE` in one GraphQL read;
  `gh repo view --json autoMergeAllowed` fails with `Unknown JSON field`, so `allow_auto_merge`
  stays the `repos/<repo>` read of `manual._repository`.
- Settings-as-code tools apply such writes from a merged file: the repository-settings app
  (https://github.com/repository-settings/app) and the Terraform GitHub provider
  (https://registry.terraform.io/providers/integrations/github/latest/docs). Rejected: the app
  is a third-party GitHub App the person installs with admin on each repository, Terraform is a
  new toolchain with a state backend (§VII), and neither accepts the invitation as the bot or
  writes the clone's local token.

## Decisions

- **D1 — a step module of `init`, not prose.** The problem is two questions and three
  person-only actions after the merge. `init` already reads each of these states for its rows
  and classifies, prints and retries transitions; a module `post_merge.steps` over
  `manual.Target` holds them, as `project_areas` and `readings_setup` do, with no new entry
  point. Alternative: standard commands in SKILL step 5 run by the agent, as agent-identity-standard-commands left them —
  rejected: the ruleset `POST` is not idempotent (agent-identity-standard-commands D4), the invitation id must be looked
  up, and the token must reach JSON without passing through output; prose cannot make these
  retry-safe.
- **D2 — the merge is the consent.** Install asks no question: a dry-run that exits 0 is
  confirmed unasked, and the installation PR's body lists every `after-merge` transition, so
  merging it authorizes them; a person who disagrees does not merge. Dropped: the yes before
  `--confirm` and the yes after the merge. What the first guarded — writes outside the PR
  (the Project copy and link, the local pre-push hook, task readings) — the person asked for by
  starting install; each is reversible and printed by the run. What the second proved — that the
  person saw the post-merge writes — the PR body now proves at the merge. The body stays
  current: `post_merge` is classified before the onboarding steps, `onboarding._pr_step` writes
  its `after-merge` lines into the new PR's body, and a confirmed run that meets the PR open
  with another list rewrites the body (`gh pr edit --body`). Writes that appear only after the
  merge, as when the person adds the bot later, follow the person's own act of following the
  `manual agent-identity` row's fix. `gh pr merge --auto` is run only when both
  `approval-ruleset` and `auto-merge` read `unchanged`, since auto-merge alone merges on checks
  (ADR 0040 D7); what is
  written is held by the post-merge run's own classification (`conflict` exits before any
  write) and by its rerun, which prints each `unchanged`. Step 5 runs after every merge: after
  an unasked upgrade its transitions are all `unchanged`, which costs one run and removes a
  branch from the procedure.
- **D3 — `init` finds the agent account.** `gh auth status --json hosts` without `GH_TOKEN`
  and `GITHUB_TOKEN` names the person as its active account; the one other github.com account
  is the agent. `--agent` only chooses among several. Alternative: the agent passes `--agent`
  from its own read — rejected: a deterministic step in prose, repeated on every run, whose
  omission silently drops four transitions. New input's failure modes: a second personal
  account and no bot is taken as the agent — the dry-run's `after-merge agent-collaborator`
  line names it before the person's yes; a bot with admin reads `ADMIN`, so
  `agent-collaborator` stays planned and the post-merge rerun shows it.
- **D4 — reads are shared.** `gh auth token --user` runs once per run. One GraphQL read with
  that token answers `viewerPermission` and the Project's `viewerCanUpdate`;
  `manual._identity_pending` takes the token it reads with, so `agent-collaborator`,
  `agent-token` and the identity row use one read. `protection` is done when
  `manual._protected` holds; only then is it not planned, so `activate_protection.preflight`
  runs only for a planned `protection`. `protection` and `approval-ruleset` go through
  `activate_protection.plan` and `write`, whose rulesets list is read once per run; after the
  write, `protection` is read back by `activate_protection.read_back`, which checks the process
  ruleset's shape, and `approval-ruleset` by `plan` again with the shipped body, which must
  read `unchanged`. The merged PR is read by `post_merge` itself, `gh pr list --head
  agent-process/install-<version> --state merged`: onboarding reads PRs only on the
  installation branch, and step 4 leaves it for the default branch.
- **D5 — order and gating.** `protection` needs no bot. `auto-merge` follows
  `approval-ruleset` and exists only with an agent account: a repository without that ruleset
  merges on checks alone (ADR 0040 D7), so auto-merge before it would merge the agent's PRs
  unapproved. `approval-ruleset` precedes `agent-token`, so no clone holds the bot's token
  while auto-merge could merge an unapproved PR. `approval-ruleset` exists only with an agent account: without a bot it would
  block every PR the person authors (agent-identity-standard-commands D4); `plan` classifies it, which closes that D4's
  unobserved second `POST`. The `activate_protection` command stays: deleting it rewrites its
  requirements and tests, a change of its own.
- **D6 — calls and identities.** Person-side calls drop `GH_TOKEN` and `GITHUB_TOKEN`, as
  `activate_protection` does (ADR 0040 D6), through `manual.Target.gh(..., env=)`. The agent's
  token goes only into `GH_TOKEN` of its acceptance and reads, and into
  `.claude/settings.local.json` through `init`'s file-step helpers (`_json_object`,
  `manual.json_text`), whose line names the path only; the file keeps its other keys and is
  rewritten in `json_text` form, since it is local and untracked; a file that is not a JSON
  object, or one `git check-ignore -q` does not report ignored, is a `conflict`, so the token is never
  committed or stashed.
- **D7 — `gh auth setup-git` stays prose.** It writes the user's global git config, and `init`
  writes nothing in the user profile.

## Risks / Trade-offs

- [An organisation Project or repository refuses an outside collaborator] → the write fails;
  `init` names the failed command's output and exits non-zero (*Init names a failed command's
  output*).
- [The person merged the installation PR over a red check] → `conflict protection` names it;
  the fix is a green PR, as `activate_protection` required before.

## Migration Plan

A repository installed earlier reads its done states as `unchanged`, so an upgrade adds no
question unless a state is outstanding. Rollback: revert the PR; the removed rows return.
