## Context

Umbrella design: `v2-0-decision-record/design.md`.

## Decisions

- **Reviews are advisory.** Neither app's verdict is parsed; a blocking finding is a thread
  the person leaves unresolved. Alternative: v1 classification — duplicated what
  `required_conversation_resolution` does.
- **A fix after the run ended is a new `/implement <change>` run** that reads open threads.
  No fixer role, no re-review trigger comment.
- **Project status is resolved by name at run time** from the Project number in a repository
  variable; nothing is generated per project.

## Risks / Trade-offs

- If `claude-code-action` threads do not count for conversation resolution without write
  permission, the review job posts through the app token instead — confirmed on a real PR
  in this change.
