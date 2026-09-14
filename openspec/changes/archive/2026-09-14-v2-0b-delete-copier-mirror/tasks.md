## 0. Branch

- [x] 0.1 `gh issue develop -c 119 --name v2-0b-delete-copier-mirror` from fresh `origin/main`;
  `python .agent-process/scripts/set_issue_status.py 119 in-progress`; verify
  `git branch --show-current` prints the change name.

## 1. Delete the mechanism

- [x] 1.1 `git rm -r template/ copier.yml template-drift-allowlist.yml
  .agent-process/scripts/template_drift.py .agent-process/scripts/adopt_agent_process.py
  .agent-process/scripts/check_consumer_test_collision.py
  .agent-process/scripts/bootstrap_github_project.py`; verify
  `git grep -l -i -E "copier|template_drift|template/" -- . ':!openspec' ':!*/adr/*' ':!.agent-process/copier-answers.yml'`
  lists only the files tasks 1.2–2.3 edit.
- [x] 1.2 `git rm tests/publisher/conftest.py tests/publisher/test_template_drift.py
  tests/publisher/test_project_bootstrap_template.py tests/publisher/test_self_installed_process.py
  tests/publisher/test_payload_layout.py tests/publisher/test_bare_consumer_quality.py
  tests/publisher/test_existing_project_installation.py tests/publisher/test_existing_project_update.py
  tests/publisher/test_workflow_references.py tests/publisher/test_test_suite_ownership.py`;
  verify `python -m pytest tests/publisher --collect-only -q` reports no collection error.
- [x] 1.3 `tests/publisher/test_reusable_workflows.py`: drop the `template/` reads in
  `test_pr_link_grants_issues_read`, `test_review_contract_is_a_file_not_an_agents_section_parser`
  (keep `contract.is_file()`), `test_installation_documents_the_caller_workflow_trust_boundary`
  (root document only); verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` green.
- [x] 1.4 Remove the `template/` exclusions and the `ci.yml.jinja` root probe:
  `tests/agent_process/test_doc_links.py` (`_EXCLUDED_PREFIXES` and its comment),
  `tests/agent_process/test_doc_narrative.py` (same), `tests/agent_process/test_branch_protection.py`
  (`_REPO_ROOT = _PAYLOAD_ROOT`), the `template/` clause of the comment in
  `ci_check.py::check_pytest`; verify `python -m pytest tests/agent_process -q` green.
- [x] 1.5 `.github/workflows/reusable-quality.yml`: delete the `pip install copier==9.17.2`
  step; verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` green and
  `git grep copier .github` is empty.

## 2. Docs and ADR

- [x] 2.1 `.agent-process/docs/architecture/agent-process.md`: in §Test suite ownership keep
  the ownership rule and the run commands, delete the render/allowlist/drift-gate paragraph
  and the `check_consumer_test_collision` paragraph; delete §Maintaining this distribution;
  verify `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py -q` green.
- [x] 2.2 `.agent-process/docs/architecture/agent-process-installation.md`: one-line notice
  under the title — the v1 Copier installation path is retired by this change (#119), `init` returns in v2-2
  (#112), the text below is history; verify the four phrases of
  `test_installation_documents_the_caller_workflow_trust_boundary` are still present.
- [x] 2.3 ADR 0027 §More Information: add "Observations from v2-0b" — the mirror had one
  consumer (this repository); the three surviving `distribution` requirements have no
  observable render until v2-2; verify `python -m pytest tests/agent_process/test_adr_records.py -q` green.

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@latest validate v2-0b-delete-copier-mirror --strict` green.
- [x] 3.2 `python .agent-process/scripts/ci_check.py` green (pytest both suites, lint, secrets,
  pip-audit).

## 4. Deliver (v1 path; `finish_change` arrives with v2-1)

- [x] 4.1 Push the branch; `gh pr create` with `Closes #119`, the deleted-file list and the
  kept-file list from `proposal.md`; `python .agent-process/scripts/request_codex_review.py --request`;
  address review threads; verify every check on the head is green.
- [x] 4.2 Last commit: `npx -y @fission-ai/openspec@latest archive v2-0b-delete-copier-mirror -y`
  (delete a leftover `openspec/changes/archive/.openspec-archive.lock` before committing), then
  3.1–3.2 again; push; wait for the checks on that head; the person merges. Verify
  `openspec/specs/distribution/spec.md` no longer has `Layered delivery through Copier`.
