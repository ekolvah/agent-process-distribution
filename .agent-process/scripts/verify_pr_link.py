#!/usr/bin/env python3
"""CI gate: a PR from an `issue-N-slug` branch MUST close its issue.

Run in CI as a module so `from scripts.open_pr import …` resolves:

    python .agent-process/scripts/verify_pr_link.py --branch "$HEAD_REF" --pr "$PR_NUMBER"

(`python .agent-process/scripts/verify_pr_link.py` would break the cross-script import — repo
root is not on `sys.path` then, same trap `issue_branch.py` documents.)

`open_pr.py` makes the right path cheap at PR-creation time, but it is invoked by
implementer prose — an agent can forget it and `gh pr create` by hand,
re-opening (issue stayed open after merge). This gate makes the
invariant NON-bypassable: as a required check it fails the PR — and blocks the
merge — whenever an `issue-N` branch's PR closes no issue, regardless of HOW the
PR was created. It reuses `open_pr`'s pure `issue_number_from_branch` +
`has_closing_reference` (no duplicated parsing).

Polls `closingIssuesReferences` (reusing `open_pr`'s attempt/delay budget) rather
than reading once: GitHub computes the linkage asynchronously after PR creation,
and on the `opened` event this required check can race ahead of that computation
on a warm runner — a single read would then false-red a correctly-linked PR and
block its merge. Betting "CI startup latency covers the window" is a hope, not a
guarantee; the same poll `open_pr` needs at creation time, the gate needs too.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time

try:
    from scripts import check_orphan_scope, open_pr
    from scripts.open_pr import (
        DEFERRED_SCOPE_BEGIN,
        DEFERRED_SCOPE_END,
        LINKAGE_ATTEMPTS,
        LINKAGE_DELAY_S,
        has_closing_reference,
        issue_number_from_branch,
    )
except ModuleNotFoundError:  # Direct execution from the relocated payload.
    import check_orphan_scope
    import open_pr
    from open_pr import (
        DEFERRED_SCOPE_BEGIN,
        DEFERRED_SCOPE_END,
        LINKAGE_ATTEMPTS,
        LINKAGE_DELAY_S,
        has_closing_reference,
        issue_number_from_branch,
    )

# Feature-detection marker for the reusable `pr-link` workflow: the trusted
# default-branch checkout is what actually runs (bootstrap fallback shape),
# so on the PR that introduces this check, and for any consumer whose default
# branch predates issue #64, this constant is absent and the workflow emits a
# visible notice instead of assuming support (§IV — mirrors
# `PUBLISH_PR_COMMENT_SUPPORTED` / `DIAGNOSE_EXECUTION_FILE_SUPPORTED` in
# check_agent_review_outcome.py).
DEFERRED_SCOPE_CHECK_SUPPORTED = True

# Anchored at the end of a top-level bullet: the exact suffix
# `render_deferred_scope_section` renders. A bullet lacking this shape is
# rejected outright (issue #64 BLOCKING on PR #66), not silently skipped —
# the earlier `findall`-over-the-whole-block scan let an arbitrary entry sit
# unnoticed next to one legitimate tracked entry inside a block the contract
# calls gate-verified.
_TRACKER_SUFFIX_RE = re.compile(r"\(tracked in #(\d+): .+\)$")


def link_required_but_missing(branch: str, refs_json: str) -> bool:
    """True iff `branch` is an `issue-N` branch but its PR closes no issue.

    A non-issue branch (fork PR, dependabot, manual branch) is not required to
    close anything, so the gate is N/A there — returns False."""
    if issue_number_from_branch(branch) is None:
        return False
    return not has_closing_reference(refs_json)


def _refs_json(pr: str) -> str:
    """Fetch `closingIssuesReferences` JSON for the PR, or exit 2 on a `gh` failure.

    Distinct exit 2 (infra/tool failure), NOT the empty `"{}"` fallback: as a
    required merge-blocking check, a transient `gh` error (auth/rate-limit/network)
    must not be misattributed as a real missing-linkage (exit 1) — that would fail
    the PR with a false diagnosis (§IV)."""
    result = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "closingIssuesReferences"],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.stdout is None or result.stderr is None:
        # Capture failed: this is infrastructure failure, the same class as the
        # nonzero rc below, and must return code 2 rather than become empty `"{}"`
        # (a false “no linkage” verdict).
        print(
            f"error: capture failed for `gh pr view {pr}` (rc={result.returncode}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}",
            file=sys.stderr,
        )
        sys.exit(2)
    if result.returncode != 0:
        print(
            f"error: `gh pr view {pr}` failed (rc={result.returncode}): "
            f"{result.stderr.strip()} — cannot verify PR→issue link.",
            file=sys.stderr,
        )
        sys.exit(2)
    return result.stdout


def _link_missing_after_poll(branch: str, pr: str) -> bool:
    """True iff `branch` is an issue-N branch whose PR still shows no link after
    polling. A non-issue branch is N/A → no `gh` call, no poll. Wraps the pure
    `link_required_but_missing` with re-fetch/backoff to tolerate GitHub's async
    linkage computation; a `gh` failure inside `_refs_json` still exits 2."""
    if issue_number_from_branch(branch) is None:
        return False
    for attempt in range(LINKAGE_ATTEMPTS):
        if not link_required_but_missing(branch, _refs_json(pr)):
            return False
        if attempt < LINKAGE_ATTEMPTS - 1:
            time.sleep(LINKAGE_DELAY_S)
    return True


def _block_bullets(pr_body: str) -> list[str] | None:
    """Top-level bullets inside the PR body's Deferred-scope sentinels.

    `None` ONLY when BOTH sentinels are absent — there is no block, nothing to
    check. A partial pair (one sentinel kept, or the two inverted) is `[]`
    instead: that is a corrupted generated block, not a PR that exports
    nothing, and conflating the two let issue #68's short-circuit turn such a
    body over a closed source issue from a visible exit 2 into a pass, with its
    unverified entries still readable as gate-verified downstream (Codex
    BLOCKING on PR #74 — the same empty-vs-absent shape as the finding below).
    `[]` also when the sentinels ARE present but no top-level bullet parses
    out of the enclosed content (wrong/missing heading, or prose instead of a
    `- ` list) — itself a malformed condition, not "nothing to check":
    `render_deferred_scope_section` never renders sentinels around an empty
    block (it omits them entirely when there is nothing to export), so this
    shape can only arise from hand-editing/corruption after generation
    (Claude finding on PR #66's fresh review — the two results used to be
    conflated, so a corrupted block was silently waved through as sound).
    Parsed structurally via `top_level_bullets`, not a regex scan over the
    raw block text — a nested (Acceptance-criteria) bullet must not be
    mistaken for a top-level entry."""
    begin = pr_body.find(DEFERRED_SCOPE_BEGIN)
    end = pr_body.find(DEFERRED_SCOPE_END)
    if begin == -1 and end == -1:
        return None
    if begin == -1 or end == -1 or end < begin:
        return []
    return check_orphan_scope.top_level_bullets(pr_body[begin:end], heading="deferred scope")


def deferred_scope_mismatch(branch: str, pr_body: str, source_issue_body: str) -> list[int]:
    """Tracker numbers the PR body's Deferred-scope block claims but the
    linked issue's *current* Out of scope section no longer backs with an
    open `deferred:` bullet — plus a `0` entry for each top-level bullet that
    does not even carry the rendered `(tracked in #N: title)` suffix (no real
    issue is ever numbered 0, so it is an unambiguous "malformed" marker).

    Soundness, not equality (issue #64 finding S2): only tracker NUMBERS are
    compared, never the rendered wording, so a benign retitle/reword of the
    issue does not red a merge-ready PR. Empty for a non-issue branch,
    mirroring `link_required_but_missing`'s short-circuit — the check is N/A
    there."""
    if issue_number_from_branch(branch) is None:
        return []
    bullets = _block_bullets(pr_body)
    if bullets is None:
        return []
    if not bullets:
        return [0]
    valid: set[int] = set()
    for bullet in check_orphan_scope.deferred_scope_bullets(source_issue_body):
        valid.update(check_orphan_scope.deferred_scope_trackers(bullet))
    mismatched: list[int] = []
    for bullet in bullets:
        match = _TRACKER_SUFFIX_RE.search(bullet)
        if match is None:
            mismatched.append(0)
            continue
        n = int(match.group(1))
        if n not in valid:
            mismatched.append(n)
    return mismatched


def _unsound_with_liveness(branch: str, pr_body: str, source_issue_body: str) -> list[int]:
    """`deferred_scope_mismatch` plus a liveness check: a tracker textually
    backed by a `deferred:` bullet but since closed must not keep downgrading
    a finding either (issue #64 should-fix on PR #66) — closed is stale
    evidence, the same reason `render_deferred_scope_section` omits a closed
    tracker at render time rather than including it."""
    mismatched = deferred_scope_mismatch(branch, pr_body, source_issue_body)
    if issue_number_from_branch(branch) is None:
        return mismatched
    unsound = list(mismatched)
    for bullet in _block_bullets(pr_body) or []:
        match = _TRACKER_SUFFIX_RE.search(bullet)
        if match is None:
            continue  # already flagged as malformed above
        n = int(match.group(1))
        if n in mismatched:
            continue  # already flagged as unbacked above
        tracker = open_pr._fetch_issue(n)
        if tracker is None or tracker.get("state") != "OPEN":
            unsound.append(n)
    return unsound


def _pr_body(pr: str) -> str:
    """Fetch the PR body, or exit 2 on a `gh` failure (same infra-vs-verdict
    split as `_refs_json`)."""
    result = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "body"],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )
    if result.stdout is None or result.stderr is None:
        print(
            f"error: capture failed for `gh pr view {pr} --json body` (rc={result.returncode}): "
            f"stdout={result.stdout!r} stderr={result.stderr!r}",
            file=sys.stderr,
        )
        sys.exit(2)
    if result.returncode != 0:
        print(
            f"error: `gh pr view {pr} --json body` failed (rc={result.returncode}): "
            f"{result.stderr.strip()} — cannot verify deferred-scope soundness.",
            file=sys.stderr,
        )
        sys.exit(2)
    return json.loads(result.stdout).get("body") or ""


def _unsound_deferred_trackers(branch: str, pr: str) -> list[int]:
    """`_unsound_with_liveness` with its two bodies fetched through `gh`.

    Statement order is the contract here, not an implementation detail
    (issue #68):

    1. The non-issue branch guard stays first, so a fork/dependabot/manual
       branch still makes no `gh` call at all — the fetches are skipped, not
       just their result discarded.
    2. The PR body is read next. `fetch_issue_body` hard-raises on a source
       issue that is not OPEN, so reading the issue first turned "this PR
       carries nothing for this check to verify" into a merge-blocking exit 2
       whenever the linked issue had been closed out from under the PR.
    3. `_block_bullets(...) is None` — sentinels absent, nothing this check can
       verify — returns before any issue read; the source issue's state is then
       not this gate's business. Keyed on `is None`, never on falsiness:
       sentinels present but unparseable is `[]`, a malformed condition that
       must still be fetched and still red (PR #66).
    4. Only then the issue read, and `_unsound_with_liveness` with the PR body
       already in hand — one `gh` round trip fewer than before in the no-block
       case, not one more.

    That reorder also changes diagnostic precedence deliberately: when both the
    PR-body read and the issue read would fail, the operator now sees
    `_pr_body`'s message rather than the issue-read one. Both still exit 2."""
    n = issue_number_from_branch(branch)
    if n is None:
        return []
    pr_body = _pr_body(pr)
    if _block_bullets(pr_body) is None:
        return []
    try:
        source_issue_body = check_orphan_scope.fetch_issue_body(n)
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(
            f"error: could not read issue #{n} to verify deferred-scope soundness: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    return _unsound_with_liveness(branch, pr_body, source_issue_body)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CI gate: PR from issue-N branch must close it.")
    parser.add_argument("--branch", required=True, help="PR head branch (github.head_ref)")
    parser.add_argument("--pr", required=True, help="PR number")
    ns = parser.parse_args(argv)

    if _link_missing_after_poll(ns.branch, ns.pr):
        n = issue_number_from_branch(ns.branch)
        print(
            f"error: PR #{ns.pr} from branch {ns.branch!r} does NOT close issue #{n} "
            f"(closingIssuesReferences empty) — it will stay open after merge. "
            f"Add `Closes #{n}` to the PR body (or use `python .agent-process/scripts/open_pr.py`).",
            file=sys.stderr,
        )
        sys.exit(1)

    unsound = _unsound_deferred_trackers(ns.branch, ns.pr)
    if unsound:
        detail = ", ".join(
            f"#{n}" if n else "a malformed entry (missing the `(tracked in #N: ...)` suffix)"
            for n in unsound
        )
        print(
            f"error: PR #{ns.pr} Deferred scope block is not gate-verified sound ({detail}) — "
            f"a listed tracker must be OPEN and backed by a `deferred:` bullet in the linked "
            f"issue's Out of scope section, and every entry must match the rendered shape. "
            f"Regenerate the section with `python .agent-process/scripts/open_pr.py` "
            f"or `update_pr_body.py`.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"ok: PR link check passed for branch {ns.branch!r}")


if __name__ == "__main__":
    main()
