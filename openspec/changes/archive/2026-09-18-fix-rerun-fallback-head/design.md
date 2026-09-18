## Context

See proposal.md — Why. The callee runs one path for every event: wait (`request_codex_review.py
--wait`, exit 0 present / 3 absent / else fail), the Claude action on `absent`, the verify
read on `github-actions`, the enforcement. `reviewed()` is head-exact for one login: a native
review whose `commit.oid` is the head, or a clean comment by that login naming the head
(Codex's `**Reviewed commit:**`, the fallback's `Reviewed head SHA:`). `gh run rerun`
re-executes every step of a run on the same payload (ADR 0027, `38debbd`). The caller pins
the callee `@main`, so a callee edit is first exercised by the PR after its merge.

## Goals / Non-Goals

**Goals:**
- A second attempt of a run whose first attempt fell back is enforcement alone: no second
  wait for Codex, no second Claude review of an unchanged head.
- The operator can finish the resolve step by hand when the rerun or the reply fails after
  the resolve.

**Non-Goals:**
- An attempt that only enforces: an attempt indistinguishable from a first run still reviews a
  head nobody reviewed (the enforcement-only hole, `b6858f8`).
- An idempotent `--thread` that re-enters after a partial run: the recovery is two `gh` calls
  the error names; a resumable step is more surface than the failure it serves.
- Any change of what is read: presence of a review on this head, never its content.

## Decisions

- **D1 — one presence read over a set of trusted logins, in the wait step.**
  `--reviewer` becomes repeatable (`action="append"`, default `None` resolved to the Codex
  login after parsing — an `append` onto a non-empty default would make `--reviewer
  github-actions` alone read both logins); `reviewed()` takes the logins and is true when
  any of them reviewed the head; the wait step names the Codex app and `github-actions`. Alternatives: a second step before the wait (`--reviewer
  github-actions --timeout-seconds 0`, its output combined into the Claude step's `if`) —
  one more step, one more output, the same read twice; a marker the fallback leaves (a label,
  a check annotation) — a new artefact to read, where the fallback's own review already is
  the marker. The verify step keeps `--reviewer github-actions` alone: it asks whether the
  fallback published, not whether anyone did.
- **D2 — no observation before the fix; the fix is confirmed after the merge.** Issue 138
  asks that a platform fact a design rests on be observed first. The one here — `gh run
  rerun` re-executes every step — is observed (attempts 2 and 3 of `35267976560` ran the
  wait again). The second Claude review on a fallback head is what the callee's own two
  lines do next (the wait's one login, the Claude step's `if` on `absent`); a test proves
  those, and running them on the platform first would cost two Codex timeouts and two Claude
  reviews to confirm an `if`. The callee is exercised by the PR after the merge (the caller
  pins `@main`): the first fallback head re-run then is the confirmation, and its carrier is
  a placeholder this change leaves in ADR 0027 in the form of the one it fills (run id, wait
  duration, second review yes/no) — a deferral in a PR body alone has no reader after the
  merge. Alternative considered: the observation on this PR's own
  first head, or on a throwaway PR — rejected by the owner (2026-09-18) as cost without a
  question. What is unobserved and stays so here: the fallback and the verify step have not
  run live under the merged callee (every `pull_request` run of PR 137 skipped both, Codex
  being requested every time); that is a fact about the fallback's publication, not about
  this change, and is noted in the ADR entry for the record.
- **D3 — a failure after the resolve names what is still undone.** `close_round` wraps the
  rerun and the reply: an exception after a successful resolve is re-raised with the commands
  the operator runs by hand, ids filled in — `gh run rerun <run-id>` and `gh api -X POST
  repos/<repo>/pulls/<pr>/comments/<comment-id>/replies -f body=…` when the rerun failed,
  the reply alone when the rerun went through and the reply failed (a second rerun of a run
  in progress is refused, and would be a wrong instruction). The thread is resolved and gone
  from `--list` by then; the message is where the operator learns it (§IV, visible
  degradation). Alternative: skip the resolve when the thread is
  already resolved and retry the rest — needs the resolved threads in the read, a second
  guard on whose resolve it was, and a test matrix for a case seen zero times.

## Risks / Trade-offs

- [A `github-actions` review of an older head counts as presence] → the read is head-exact
  on both forms (`commit.oid`, `Reviewed head SHA: <sha>`); the stale-review scenario stays
  and its test covers the second login.
- [Another workflow under the same login names a head] → only the review job writes
  `Reviewed head SHA:`; the quality workflow posts no comment.
- [The callee fix is not exercised by this PR] → the first fallback head after the merge
  is the confirmation; recorded in ADR 0027 then, as for the same-path run today.
