# Review and merge

**Question this document answers:** what reviews a PR, what blocks a merge, and how the
process protects the default branch from agent mistakes.

Status: draft

## Requirements

- **REVW-1** (MUST) PR review is **advisory**: the Codex GitHub app reviews every PR by
  its own configuration, and a short `claude-code-action` workflow reviews the diff.
  Neither verdict is classified by a script or turned into a required check.
- **REVW-2** (MUST) The reviewer reads the **diff** of the PR, not whole files, and the PR
  body lists tracked deferrals as issue links so a reviewer does not re-report them.
- **REVW-3** (MUST) The implementer's own run applies review findings before the person
  looks (`40-implementation.md`, IMPL-5); a later fix is the person launching
  `/implement #N` again, which reads the open threads.
- **REVW-4** (MUST) The only automated merge gates are GitHub-native: required checks
  from the reusable workflow, `required_conversation_resolution`, PR required, no direct
  push. They are applied as a ruleset JSON kept in this repository and installed once by
  `init`.
- **REVW-5** (MUST) The person merges. No agent has merge authority.
- **REVW-6** (MUST) Local safety is a deny-list in the plugin's `settings.json`
  (force-push, push to the default branch); the ruleset is the authoritative barrier.
- **REVW-7** (SHOULD) Reviewer instructions name two simplicity triggers (reinvented
  functionality, unnecessary complexity) as findings to raise.
- **REVW-8** (MUST NOT) No outcome classification, evidence publishing or review
  credentials preflight; no carrier failover between reviewers; no drift check for branch
  protection.
