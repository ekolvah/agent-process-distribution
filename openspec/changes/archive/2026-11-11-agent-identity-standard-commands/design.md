## Standard approach

- Git credentials: `gh auth setup-git` (https://cli.github.com/manual/gh_auth_setup-git),
  observed writing the reset-and-route into the global config (proposal, **Why**).
- Collaborator: `PUT /repos/{owner}/{repo}/collaborators/{username}` invites; the invitee accepts
  from the invitation link (https://docs.github.com/en/rest/collaborators/collaborators#add-a-repository-collaborator).
- Project writer: the Project's settings, "Manage access"
  (https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-access-to-your-projects);
  `gh project` has no access command.
- Ruleset: `POST /repos/{owner}/{repo}/rulesets` with the shipped template
  (https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset); `gh api` fills
  `{owner}/{repo}` from the current repository.

## Decisions

- **D1 — the checks live in `init`'s identity row.** `manual._identity_set` already reads the
  settings token and runs on every Install and upgrade, so a bot promoted to admin later shows
  up; a separate script would add an entry point, its arguments and tests. With a token set,
  the row reads `repository{viewerPermission}` in one GraphQL call carrying that token as
  `GH_TOKEN`, whatever the session's environment, and is outstanding unless it is `WRITE` or
  `MAINTAIN`; a failed read is the row's existing `(cannot read: …)`. This one read covers both
  observed failures: the person's token is `ADMIN` wherever Install ran, since step 5 writes a
  ruleset, which needs admin; a non-collaborator reads `READ` on a public repository. No
  standard checks "this token has write but not admin on this repository". The session-start
  check stays offline: it gains no network read.
- **D2 — lost proofs and their catchers.** The re-plan of the old script verified every
  transition; now:
  - git route: without it the agent pushes as the person, which nothing needs to catch — its
    PR and merge still go through `gh` as the bot and the ruleset;
  - collaborator: the row's read answers `READ` or fails, so the row stays outstanding;
  - Project role: the agent's first `set_status` call fails;
  - ruleset: no catcher in a consumer — a PR whose repository skipped the `POST` auto-merges
    on green checks and `wait_for_pr` exits 4 with `MERGED`; accepted, as a presence check
    answers no observed failure. ADR 0040's live confirmation covers this repository.
  - person-side calls: the script ran its admin calls without `GH_TOKEN`. The per-repository
    lines of step 6 run as the person because step 6 runs before the restart that gives the
    session the bot's token; run later with the bot's token, they fail with 403, since the bot
    is not an admin, and the agent shows that failure.
  "Not git-ignored" goes: Claude Code configures git to ignore `.claude/settings.local.json`
  when it creates it (https://code.claude.com/docs/en/settings, "Settings files"; observed in
  `~/.config/git/ignore`, proposal **Why**), and a committed token is caught by the secrets
  scan of the quality `test`.
- **D3 — git route per machine.** `gh auth setup-git` writes the global config; outside a
  session `gh auth git-credential` answers with `gh`'s active account, the person. Clones set
  up by the old script keep an equivalent local route.
- **D4 — the ruleset by one `gh api` call.** `activate_protection` planning it too is rejected:
  an unasked upgrade runs `activate_protection` on repositories without a bot, where the
  approval rule would block every PR the person authors. The `POST` is not idempotent, and what a
  second `POST` of the same name returns was not observed; step 6 runs it once per repository. Step 6 names the template under the skill's base directory,
  which Claude Code prints when it loads the skill.

## Migration Plan

No consumer state changes. Rollback: revert the PR; the old script converges the same state.
