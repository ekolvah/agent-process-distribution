## Context

The review job checks out the PR head and the trusted process source at `trusted/`. The
contract says the policy is `CLAUDE.md`, `.claude/rules/` and the documents they link to "at
the reviewed repository's default branch", and the prompt calls every worktree `CLAUDE.md` and
`.claude/rules/` file untrusted. The evidence (the observation in the proposal's Why) is run
38132196665, the action's own log, and the closing comments of PRs 372–390.

## Decisions

### D1. The policy is the root files the session loads from the base

The contract's Policy source bullet and the prompt name the policy as the contract and the root
`CLAUDE.md` and root `.claude/rules/` of the PR worktree, restored from the PR's base. Every
other file of the PR worktree is untrusted review data, named explicitly for the instruction
files the session may also load: any other `CLAUDE.md` or `.claude/rules/` file,
the PR's own copies in `.claude-pr/`, and `trusted/CLAUDE.md`. The bullet drops "the documents
they link to" and "the default branch".

- Only a delivered source is named, and only the part of it that comes from the base.
  `anthropics/claude-code-action@v1` `src/github/operations/restore-config.ts`,
  `restoreConfigFromBase`, restores root-level paths, among them `CLAUDE.md` and `.claude`,
  with `git checkout origin/${baseBranch} -- <path>` before the session. The session loads
  them: the run log shows `settingSources [user, project, local]`, and the Agent SDK page
  "Modifying system prompts" says "`'project'` loads `CLAUDE.md` or `.claude/CLAUDE.md` from
  the working directory" and "CLAUDE.md loading is controlled by setting sources, not by the
  `claude_code` preset". The Claude Code memory page says "Rules without `paths` frontmatter
  are loaded at launch" and "A path-scoped rule loads when Claude uses the Read, Write, or Edit
  tool on a matching file". A path-scoped root rule (this repository's `testing.md`, scoped to
  `tests/**`) is still restored from the base; it loads only when a matching file is read.
- Other instruction files are loaded too, but not from the base. The memory page says files
  in subdirectories "load on demand" once Claude reads a file there. A nested `CLAUDE.md` or
  `.claude/rules/` file is therefore the PR head's, and
  `trusted/CLAUDE.md` is this repository's conventions, not a consumer's. Hence the prompt keeps
  calling them untrusted.
- The contract is read through `trusted/`, and the nine closing comments show it read every
  time. Nothing delivers the linked documents (`principles.md`, `SKILL.md`): the closing
  comments show them rarely opened, and an opened copy is the PR head's.
- Dropping the linked documents loses no enforced rule. The rules the review grades at
  `P0`/`P1` are in the contract, including the two §VII triggers verbatim.
- The PR's base, not the default branch, because that is what the action restores. The
  ruleset requires the check on the default branch only, where the two are the same.

Alternatives rejected:

- Telling the model to read the linked documents with `git show origin/<base>:<path>`. It is
  an instruction with no guarantee of being followed, and it adds reads for rules the
  contract already states.
- Appending the contract and linked documents through `--append-system-prompt-file`. It
  guarantees presence, not compliance, costs about 9k cached tokens per review, and is
  unverified inside the action. No observed review skipped the contract.

### D2. No tool grant is added

`--allowed-tools` stays as it is: the inline comment, `gh pr diff` and `gh pr view`. The
contract-required reads are file reads, `Grep`/`Glob`, `git diff` and `git show`. Claude Code
allows these as read-only, and the nine closing comments show them running with no denial.
The four denials were compound commands, and none of them was a contract-required read.

- Granting `Bash(git show:*)` explicitly was rejected. The read-only classification already
  allows `git show`, and a prefix grant would also allow `git show --output=<file>`, which
  writes files.
- Granting `Bash(*)` or the compound forms was rejected. It would open arbitrary shell in a
  job that holds a token with `pull-requests: write`, to save the model a retry it already
  makes.
- Catcher if a later Claude Code release stops classifying a read as read-only: the closing
  comment lists each denial with its command (the existing requirement "Claude reviews every
  head", scenario "Denied tool"), on the PR the person reads.

### D3. A denial does not fail the check

This is unchanged. It is the existing requirement, and the data does not support changing it.
Failing on any denial would have turned 4 of the 9 reviews red over convenience commands the
model had worked around. Failing only on a "contract-required" denial would need a parser that
classifies tool inputs. ADR 0027 removed that kind of bespoke review parsing. The issue's
second question is answered "keep" and needs no code.

## Risks / Trade-offs

- Accepted gap: the base origin of the policy depends on the action's restore, and `@v1` is a
  floating tag. If a release drops the restore, the session loads the PR's root `CLAUDE.md`,
  and the prompt now calls that file policy, where today it disowns it. Nothing in delivery
  reads the action's restore log line, so no check catches this. Pinning the action to a SHA,
  or restoring the root files in a workflow step of our own, is a separate decision; the PR
  body names this gap for the person.
- Accepted gap, unchanged by this change: instruction files the session loads that the
  restore does not cover (a nested `CLAUDE.md`, an `AGENTS.md` in a repository with no root
  `CLAUDE.md`, which the memory page says is read "only when you have no `CLAUDE.md` in your
  working directory or above it", a file a root `CLAUDE.md` imports with `@path`) come from
  the PR head. The prompt calls the first two untrusted, which is a request, not a gate. This repository's root
  `CLAUDE.md` has no `@path` import.
- No mechanism makes the model apply the policy. The review is evidence, not a gate
  (ADR 0027); the deterministic gates enforce what a script can check.

## Migration / Rollback

No migration is needed: a consumer picks up the prompt at its caller's pin. To roll back,
revert the PR. The previous prompt is still valid against the same tools.
