## 1. ADR "v2"

- [x] 1.1 Create `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`
  from `template.md` (0025 and 0026 are taken in `docs/adr/`): frontmatter `status: "accepted"`,
  `date: 2026-09-14`, `decision-makers: ekolvah`; h2 sections the guard requires — `Context and
  Problem Statement`, `Considered Options`, `Decision Outcome` — plus `Native alternatives
  considered` and `Deletion condition` (the two requirements this change adds to `maintenance`).
- [x] 1.2 `Context and Problem Statement`: from `design.md` §Context and `proposal.md` §Why — the
  v1 size (9 100 / 11 400 lines), code guarding the two human decisions, the Copier mirror and its
  drift tests; issue references as pointers in parentheses (`(#107)`), never narrative.
- [x] 1.3 `Decision Drivers`: the goal function in strict order (future support, tokens,
  predictability) and the constraints (GitHub Actions + Projects only, mixed stacks, two
  subscriptions, both agents carry every role).
- [x] 1.4 `Considered Options` as a Kepner-Tregoe trade study for the spec/plan carrier:
  options OpenSpec, GitHub Spec Kit, bespoke `plan-issue` runbook. MUSTs: a living system spec
  that shows implemented vs pending; works identically from Claude Code and Codex; no third paid
  service. WANTs weighted by the goal function: maintained by a team other than us, tokens per
  change, fits the existing issue/PR flow, archive step keeps `specs/` current. Fill the scores
  from the facts already in `design.md` (Spec Kit fails the living-spec MUST; bespoke is the same
  loop iterated by one team); one table, no prose repetition.
- [x] 1.5 `Decision Outcome`: the eight decisions of `design.md` §Decisions as one bullet each,
  with `Consequences` (good: deletions by v2-1 … v2-6; bad: Node in consumers, ~17k-token
  OpenSpec skills, Codex self-review weaker than a subagent) and `Confirmation` (the acceptance
  criteria of `proposal.md`: size budget, ≤ 10-minute install, no three-way merge, telemetry no
  worse than v1).
- [x] 1.6 `Native alternatives considered`: for every script v2 keeps or adds (`check_red`,
  `set_status`, `wait_for_pr`, `finish_change`, `check_coverage`, `init`) name the GitHub / `gh` /
  OpenSpec / Claude Code / Codex feature that was tried or ruled out and why it falls short.
- [x] 1.7 `Deletion condition`: what is removed if v2 stops paying for itself — per decision, one
  line (e.g. "if OpenSpec is abandoned upstream, `openspec/` becomes plain Markdown specs and
  `/opsx:*` is replaced by the `plan-issue` runbook kept in git history").
- [x] 1.8 `More Information`: superseded records listed with one line each on what replaces them;
  the v1 lessons the specs no longer repeat (from the v2 Q&A of 2026-09-12 when the owner
  supplies it; otherwise from `design.md` §Risks and `proposal.md` §Why).

## 2. Superseded records

- [x] 2.1 Set `status: "superseded by ADR-0027"` in 0011, 0015, 0019, 0021, 0022, 0023 under
  `.agent-process/docs/adr/` and in 0013 under `docs/adr/`; change nothing else in them.
  (The v1 Copier mirror still ships the ADR catalogue: the six records and 0027 are copied to
  `template/.agent-process/docs/adr/` so `test_template_drift` holds until `v2-2` deletes it.)

## 3. Change artifacts

- [x] 3.1 `proposal.md` §Capabilities: `maintenance` is now a **Modified** capability
  (`openspec/specs/maintenance/spec.md` exists since #109); keep the delta as two ADDED
  requirements.

## 4. Verify

- [x] 4.1 `python -m pytest tests/agent_process/test_adr_records.py tests/agent_process/test_doc_links.py -q` green
  (record name, unique number, known status, `superseded by` resolves, required sections; links).
- [x] 4.2 `npx -y @fission-ai/openspec@latest validate v2-0-decision-record --strict` green (delta well-formed against the
  baseline spec).
- [x] 4.3 `python .agent-process/scripts/ci_check.py` green.

## 5. Deliver (v1 path; `finish_change` arrives with v2-1)

- [x] 5.1 Push the branch `v2-0-decision-record`; open the PR (`Closes #110`); address review threads.
- [ ] 5.2 Last commit: `openspec archive v2-0-decision-record -y`, then 4.1–4.3 again; push; wait
  for the checks on that head; the person merges.
