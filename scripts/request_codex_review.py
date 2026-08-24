"""Read the automatic Codex verdict for the reviewed head and publish it.

Carrier 1 is the Codex code review that runs on GitHub through the ChatGPT
subscription: Automatic reviews triggers it without a workflow-authored comment.
It posts its own review. Unlike Claude it does not execute inside this
runner, so this module polls for a review the
declared reviewer left on *this* head, and translates the review state into the
outcome vocabulary the enforcement step already understands.

Two rules carry the design. A review left on an earlier head is not a verdict on
this one: the diff it read is not the diff being merged. And a carrier that never
answered must leave nothing behind — the enforcement step reds the check on an
empty payload, which is exactly what «no review happened» has to look like (§IV).

The mapping below is not divination: `REVIEW_CONTRACT.md`, linked from
`AGENTS.md`, tells the reviewer to request changes only for a blocking finding
and to comment otherwise, so the review state is the severity the reviewer was
asked to express.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence

from scripts.check_agent_review_outcome import VALID_OUTCOMES, validated_evidence
from scripts.gh_io import flatten_pages, publish_step_output, slurp_records

# Verified against the live API (`gh api apps/chatgpt-codex-connector` → owner
# `openai`), not inferred from the product name: a wrong login here would read
# every Codex review as absent and time the carrier out on every run.
CODEX_REVIEWER = "chatgpt-codex-connector[bot]"
_EVIDENCE_BLOCK = re.compile(
    r"<!--\s*agent-review-evidence\s*\n(?P<payload>\{.*?\})\s*-->", re.DOTALL
)
STATE_OUTCOMES = {
    "APPROVED": "clean",
    "COMMENTED": "rework",
    "CHANGES_REQUESTED": "blocking",
}
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_POLL_SECONDS = 20


def _evidence_from_review(record: Mapping[str, object], outcome: str) -> dict[str, object] | None:
    """Read the explicitly-delimited evidence block without inventing findings."""
    body = record.get("body")
    match = _EVIDENCE_BLOCK.search(body) if isinstance(body, str) else None
    if match is None:
        return None
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return None
    evidence = validated_evidence(payload)
    if evidence is None or evidence[0] != outcome:
        return None
    return {"outcome": evidence[0], "findings": evidence[1]}


def find_verdict(reviews: object, head_sha: str, reviewer: str) -> dict[str, object] | None:
    """Return structured evidence from `reviewer`'s review of `head_sha`, if any.

    The last matching review wins: Codex re-reviews on request, and its latest
    word on this head is the one the maintainer sees.
    """
    verdict: dict[str, object] | None = None
    for record in flatten_pages(reviews):
        user = record.get("user")
        login = user.get("login") if isinstance(user, Mapping) else None
        if login != reviewer or record.get("commit_id") != head_sha:
            continue
        outcome = STATE_OUTCOMES.get(str(record.get("state")))
        if outcome is not None:
            verdict = _evidence_from_review(record, outcome)
    return verdict


def _fetch_reviews(repository: str, pr_number: str) -> object:
    return slurp_records(f"repos/{repository}/pulls/{pr_number}/reviews?per_page=100")


def _has_current_review(reviews: object, head_sha: str, reviewer: str) -> bool:
    return any(
        isinstance(record.get("user"), Mapping)
        and record["user"].get("login") == reviewer
        and record.get("commit_id") == head_sha
        and str(record.get("state")) in STATE_OUTCOMES
        for record in flatten_pages(reviews)
    )


def poll_for_verdict(
    repository: str,
    pr_number: str,
    head_sha: str,
    *,
    reviewer: str = CODEX_REVIEWER,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    sleep: Callable[[float], None] | None = None,
    monotonic: Callable[[], float] | None = None,
) -> dict[str, object] | None:
    """Wait for automatic review evidence until `timeout_seconds` elapses.

    The first read handles automatic review that completed before this job.
    An invalid current-head review permits Claude fallback; an absent review is
    polled until the bounded timeout.
    """
    wait = sleep or time.sleep
    clock = monotonic or time.monotonic

    reviews = _fetch_reviews(repository, pr_number)
    verdict = find_verdict(reviews, head_sha, reviewer)
    if verdict is not None:
        return verdict
    if _has_current_review(reviews, head_sha, reviewer):
        return None

    deadline = clock() + timeout_seconds
    while clock() < deadline:
        wait(poll_seconds)
        verdict = find_verdict(_fetch_reviews(repository, pr_number), head_sha, reviewer)
        if verdict is not None:
            return verdict
    return None


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", dest="repository", required=True, metavar="OWNER/REPO")
    parser.add_argument("--pr", dest="pr_number", required=True, metavar="NUMBER")
    parser.add_argument("--head-sha", dest="head_sha", required=True)
    parser.add_argument("--reviewer", default=CODEX_REVIEWER)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Publish Codex's verdict as the payload the enforcement step reads.

    Exit code 0 either way, on purpose: the enforcement step is the single place
    that turns an outcome into a check result, and an empty payload already means
    «no verdict» there. Failing here as well would split one verdict across two
    steps and leave the log unable to answer who reviewed this head.
    """
    options = _parse_options(argv)
    verdict = poll_for_verdict(
        options.repository,
        options.pr_number,
        options.head_sha,
        reviewer=options.reviewer,
        timeout_seconds=options.timeout_seconds,
        poll_seconds=options.poll_seconds,
    )
    if verdict is None:
        print(
            f"::warning::{options.reviewer} left no review of {options.head_sha} within "
            f"{options.timeout_seconds}s. Codex produced no verdict, so the enforcement "
            "step below has no outcome to enforce. Check that Automatic reviews are enabled "
            "with the On every push trigger, and that its subscription "
            "quota is not exhausted."
        )
        publish_step_output("payload=")
        return
    outcome = verdict.get("outcome")
    if outcome not in VALID_OUTCOMES:  # pragma: no cover - guarded by the mapping test
        raise RuntimeError(f"Codex produced an outcome the gate does not know: {outcome!r}")
    publish_step_output(f"payload={json.dumps(verdict, separators=(',', ':'))}")


if __name__ == "__main__":
    main()
