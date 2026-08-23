# Code review contract

This is the authoritative contract for both automated PR-review carriers.
`AGENTS.md` points here; do not copy these rules into workflow YAML.

- Read `CLAUDE.md` and the repository docs it links to first: repository
  conventions take precedence over your defaults.
- Look for bugs, logic errors, security issues, convention violations, and
  missing matching tests or an explicitly recorded coverage decision.
- For changed documentation, use the repository file map. It describes current
  implemented state, not history or ideas; issue and PR references are pointers.
- Report every finding. Each has `severity` (blocking / should-fix /
  nice-to-have) and `confidence` (high / medium / low).
- `blocking` means wrong behaviour, a failing or missing behavioural test, a
  misleading result, a leaked secret, or a convention violation.
- `should-fix` changes behaviour, contract, or what an operator reads. Wording,
  naming, ordering, and style are nice-to-have.
- Do not re-raise a finding already answered by a correct recorded rationale.
  On a re-run review only the increment, not accepted trade-offs again.
- A deterministic-gate duplicate is `nice-to-have, duplicate of ci_check`.
- In the review body group findings by severity and state `Reviewed head SHA:`.
  If there are no findings, say so exactly in one line.
- A merge-affecting structured result contains `outcome` and `findings`. `clean`
  carries `findings: []`; `rework` and `blocking` each carry at least one finding
  with `severity`, `confidence` (`high` / `medium` / `low`), and a non-empty
  human-readable `summary`. The check publishes only validated evidence with its
  reviewed head SHA.
- A GitHub review carrier appends that JSON inside an exact
  `<!-- agent-review-evidence` block. Its `outcome` must match its GitHub review
  state: approved is `clean`, commented is `rework`, and changes requested is
  `blocking`.
- Request changes only for blocking findings; comment for lower findings;
  approve only when there are no findings. Never merge.
