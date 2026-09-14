## Context

See `proposal.md` — Why. Current state that shapes the deletion:

- `template/` mirrors the root payload as `.jinja` files; `template_drift.py` errors on any
  template file absent from the root and on any root file absent from the template unless
  `template-drift-allowlist.yml` names it. Every root-only file added since the OpenSpec adoption
  (#105) has an allowlist row.
- Render tests (`tests/publisher/conftest.py::rendered_default` and the tests listed in the
  proposal) run `copier copy` against this checkout; `reusable-quality.yml` installs
  `copier==9.17.2` for them. `pyproject.toml` `testpaths = ["tests/publisher"]` and
  `ci_check.py` collect `tests/publisher` and `tests/agent_process` — nothing under
  `template/tests/` is ever collected at the root.
- Three tests in `test_reusable_workflows.py` read `template/` files for equality or
  presence checks; `test_doc_links.py`, `test_doc_narrative.py` exclude `template/` from
  their scans; `test_branch_protection.py` locates the repository root by probing for
  `ci.yml.jinja` (a consumer-render heuristic that is always false here).
- `.agent-process/copier-answers.yml` is read by `test_delivery_gate_wiring.py` as the
  source of `vcs.repository.name` (ADR 0026); no other code reads it after this change.
- `agent-process-installation.md` describes the v1 install/update path (`copier copy`,
  `adopt_agent_process.py`, `check_consumer_test_collision.py`); `AGENTS.md` and
  `.claude/rules/workflow.md` link to it; `test_reusable_workflows.py::test_installation_documents_the_caller_workflow_trust_boundary`
  asserts four phrases in it (trust-boundary paragraphs, unrelated to Copier).

## Goals / Non-Goals

**Goals:** one PR that deletes the mechanism and everything that exists only for it; CI
green on the same checks as before minus the render tests; no v1 behaviour other than
distribution changes.

**Non-Goals:** any replacement (plugin packaging, `init`, ruleset) — v2-2; touching
`copier-answers.yml` or the tests that read it — v2-2; editing ADR text beyond ADR 0027's
observations; reorganising `tests/publisher` vs `tests/agent_process` — the split stays as a
directory convention, only its render-based enforcement goes.

## Decisions

- **Delete whole files where the file exists only for the render; edit where a test also
  proves something else.** `test_test_suite_ownership.py` is deleted entirely: all six tests
  compare the root against `template/tests/` or a render — with no template there is no
  "physical owner" to compare. `test_reusable_workflows.py` keeps its 40+ workflow assertions
  and loses only the `template/` reads: `test_pr_link_grants_issues_read` keeps the two root
  assertions; `test_review_contract_is_a_file_not_an_agents_section_parser` keeps the root
  contract-exists assertion and drops the template equality; `test_installation_documents_the_caller_workflow_trust_boundary`
  iterates the root document only. Alternative — rewrite the ownership test as a root-only
  layout rule — rejected: no observed problem asks for a guard (#106 decision).
- **`copier-answers.yml` stays.** Deleting it moves `test_delivery_gate_wiring.py`'s
  attribution source into this change; that test and the answers file die together in v2-2
  when `init` writes the Project attribution its own way. Kept files are listed in the
  proposal so the leftover is a decision, not an oversight.
- **`distribution` keeps three requirements with unobservable scenarios until v2-2.**
  `Rendered payload` and `Process change` speak of "rendered"; there is no render to
  observe between this step and v2-2. Alternative — MODIFY them now to a render-free
  wording — rejected: v2-2's delta rewrites them together with `init`, and rewording twice
  is the duplicated-work the goal function forbids. The gap is recorded in ADR 0027
  §More Information as an observation of this step.
- **`agent-process-installation.md` stays with a retirement notice** (one line under the
  title: the v1 path is retired by #119, `init` returns in v2-2). Alternative — delete it —
  rejected: `AGENTS.md`, `workflow.md` and `test_reusable_workflows.py` reference it, and
  its trust-boundary paragraphs are still the canon `reusable-quality.yml` is written
  against. Its Copier steps are left as history, not corrected: the notice says so.
- **`agent-process.md`:** §Test suite ownership keeps its first paragraph (the rule) and the
  run commands; loses the render/allowlist/drift-gate paragraph and the
  `check_consumer_test_collision` paragraph; §Maintaining this distribution is deleted.
  `test_doc_narrative` and `test_doc_links` decide whether the remaining text is consistent.
- **CI:** `reusable-quality.yml` drops the `pip install copier` step only; the pytest
  invocation is unchanged. Alternative — also drop Node/`npx` — not applicable, the quality
  workflow never installed it.
- **Deletion, not `git mv`:** history keeps the mirror; ADR 0027's deletion condition for
  OpenSpec already names "kept in git history" as the recovery route.

## Risks / Trade-offs

- [A root file that only the drift gate proved present — e.g. a consumer test under
  `tests/agent_process/` that mirrored a template twin] → no risk of loss: root files are
  untouched; only the proof that the mirror matched disappears, and the mirror goes too.
- [`test_doc_links` starts scanning paths it used to exclude] → the exclusion covered only
  `template/`, which no longer exists; an unexpected link failure elsewhere is a real broken
  link and is fixed in this PR.
- [The second consumer runs `copier update` against this source after merge] → fails
  visibly (no `copier.yml`); the migration issue (#117) already says it migrates through
  v2-2, never through an update.
- [A stale `copier` dependency somewhere] → none: `copier` is not in any
  `.agent-process/*.txt`; the only install was the CI step this change deletes.

## Migration Plan

One PR on branch `v2-0b-delete-copier-mirror` (v1 delivery path, as #110): `gh issue develop`,
`Closes #119`, archive as the last commit, the person merges. Rollback: revert the PR — the
mirror returns intact, the allowlist rows for this change's own artifacts would then be
missing and `test_template_drift` would say so.
