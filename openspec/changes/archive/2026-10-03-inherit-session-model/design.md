## Context

`agents/` holds one plugin agent, `architect-reviewer.md`, pinned as proposal.md records.
Claude Code resolves a subagent's model in this order (sub-agents docs, read 2026-10-03):
the per-invocation `model` parameter, the frontmatter `model` (`inherit` selects the main
conversation's model), `CLAUDE_CODE_SUBAGENT_MODEL`, the main conversation's model. `effort`:
"Overrides the session effort level. Default: inherits from session."

## Decisions

**D1 — `model: inherit`, not an omitted key.** Omitting `model` lets
`CLAUDE_CODE_SUBAGENT_MODEL` (step 3) choose a model the chat did not select; `inherit` stops
at step 2 on the chat's model. Alternative: a floating alias (`opus`) — it does not go stale,
but it still ignores the chat's choice.

**D2 — `effort` absent.** The docs give no `inherit` value for `effort`; the session level
applies only when the key is absent.

**D3 — A test, not a shipped check.** One assertion in `tests/publisher/test_plugin.py` over
every `agents/*.md` keeps a pin from coming back; nothing ships to consumers (proposal.md,
declined ask).

## Risks / Trade-offs

- [Dropped guard: the pin guaranteed review on a strong model at `high` effort] → What stops
  proving: a review in a session on a weaker model or lower effort runs weaker. Catcher: none
  automated; the person chose that session's model and effort and sees them in the chat. The
  PR's `agent-review` job is unaffected — its model is the workflow's, not this frontmatter's.
- [A per-invocation `model` argument (step 1) still overrides `inherit`] → accepted: it is the
  main session's own choice.

## Migration Plan

Ships with the next plugin release; rollback restores the two frontmatter lines.
