# Code review contract

This is the authoritative contract for the owner-requested Codex primary and
Claude fallback PR-review carriers.
`AGENTS.md` points here; do not copy these rules into workflow YAML.

- Read `AGENTS.md` and the repository documents it links to first: repository
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
- The PR author starts the Codex primary with `@codex review`; GitHub Actions
  never writes that command. Codex posts a standard GitHub review whose inline
  comments are the evidence for the current head SHA. If that evidence is absent
  or invalid, the workflow calls Claude as the fallback carrier.
- The trusted gate translates Codex priorities: P0/P1 are `blocking`; P2 is
  `should-fix`; P3 is `nice-to-have`. Its published result contains `outcome` and
  `findings`: `clean` carries `findings: []`; `rework` carries non-blocking
  findings; `blocking` carries at least one blocking finding. Every translated
  finding has `severity`, `confidence`, and a non-empty human-readable `summary`.
- Do not append an `agent-review-evidence` JSON block. Codex's normal GitHub
  review format is authoritative input; the trusted gate creates its own
  structured publication from that format. Claude's fallback result is instead
  required to satisfy the workflow's structured-output schema.
- Request changes only for blocking findings; comment for lower findings;
  approve only when there are no findings. Never merge.
