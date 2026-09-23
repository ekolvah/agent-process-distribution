## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py refactor-init-install --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 162; verify it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any code change

## 1. RED first

- [x] 1.1 no RED: `skip_specs` behaviour-preserving refactor; the safety net is the unchanged `tests/publisher/test_init.py`. Record its baseline instead: `python -m pytest tests/publisher/test_init.py -q` is green and `python -m pytest tests/publisher/test_init.py --collect-only -q` lists the node ids that 3.2 compares against

## 2. Refactor

- [x] 2.1 Add `Host` and change `install` to `install(argv, host)` (design D1); update `main` and the call in `tests/publisher/init_harness.install`, whose `noqa` reason becomes "mirrors the fields of init.Host"; verify `python -m pytest tests/publisher/test_init.py -q` is green
- [x] 2.2 Extract `_run` and `_perform` (design D2) and remove the `noqa` of `install`; verify `python -m ruff check --ignore-noqa --select C901,PLR0911,PLR0912,PLR0913,PLR0915 skills/agent-process/scripts/init.py` reports only `_checkout`, and `python -m pytest tests/publisher/test_init.py -q` is green; commit Group 2 as `refactor(init): fit install under the complexity limits`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify it passes; verify `git diff origin/main -- tests/publisher/test_init.py` is empty, the `--collect-only` node ids equal those of 1.1, and `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [x] 4.1 With a clean worktree run `python skills/agent-process/scripts/archive_change.py refactor-init-install`; verify it commits the archive (no spec delta: `skip_specs`) and pushes the branch
- [ ] 4.2 Run `gh pr create --title "refactor-init-install" --body-file <report>`; the report references issue 162 without `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`; after each corrective push run both again; resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`, answer P2/P3 without resolving, run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- n/a: `skip_specs` — the change has no delta scenario; behaviour is held by the unchanged `tests/publisher/test_init.py`.
