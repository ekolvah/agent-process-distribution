"""Read the standard GitHub review that a PR author requested from Codex.

Codex's supported GitHub flow is an owner comment, ``@codex review``. The
integration posts a normal GitHub review: its summary is generic and its actual
findings are inline comments, marked P0 through P3. This adapter never writes a
comment or invokes another model. It waits for a current-head Codex review and
translates those native records into the gate's evidence vocabulary.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence

from scripts.check_agent_review_outcome import VALID_OUTCOMES, validated_evidence
from scripts.gh_io import flatten_pages, publish_step_output, slurp_records

CODEX_REVIEWER = "chatgpt-codex-connector[bot]"
STANDARD_REVIEW_PARSER = True
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_POLL_SECONDS = 20
_PRIORITY = re.compile(r"\bP(?P<number>[0-3])\b", re.IGNORECASE)
_SEVERITIES = {
    "0": "blocking",
    "1": "blocking",
    "2": "should-fix",
    "3": "nice-to-have",
}
_REVIEW_STATES = frozenset({"APPROVED", "COMMENTED", "CHANGES_REQUESTED"})


def _finding(record: Mapping[str, object]) -> dict[str, str] | None:
    body = record.get("body")
    if not isinstance(body, str) or not (summary := body.strip()):
        return None
    priority = _PRIORITY.search(summary)
    severity = _SEVERITIES[priority.group("number")] if priority else "should-fix"
    return {"severity": severity, "confidence": "high", "summary": summary}


def _findings_for_review(comments: object, review_id: object) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for comment in flatten_pages(comments):
        if comment.get("pull_request_review_id") != review_id:
            continue
        finding = _finding(comment)
        if finding is not None:
            findings.append(finding)
    return findings


def _evidence_from_review(
    record: Mapping[str, object], comments: object
) -> dict[str, object] | None:
    state = str(record.get("state"))
    findings = _findings_for_review(comments, record.get("id"))
    if state == "APPROVED":
        return {"outcome": "clean", "findings": []} if not findings else None
    if state not in {"COMMENTED", "CHANGES_REQUESTED"} or not findings:
        return None
    outcome = (
        "blocking" if any(finding["severity"] == "blocking" for finding in findings) else "rework"
    )
    evidence = {"outcome": outcome, "findings": findings}
    return evidence if validated_evidence(evidence) is not None else None


def find_verdict(
    reviews: object,
    comments: object,
    head_sha: str,
    reviewer: str,
) -> dict[str, object] | None:
    """Return native Codex evidence for the current reviewed head, if present."""
    verdict: dict[str, object] | None = None
    for record in flatten_pages(reviews):
        user = record.get("user")
        login = user.get("login") if isinstance(user, Mapping) else None
        if login != reviewer or record.get("commit_id") != head_sha:
            continue
        evidence = _evidence_from_review(record, comments)
        if evidence is not None:
            verdict = evidence
    return verdict


def _has_current_review(reviews: object, head_sha: str, reviewer: str) -> bool:
    return any(
        isinstance(record.get("user"), Mapping)
        and record["user"].get("login") == reviewer
        and record.get("commit_id") == head_sha
        and str(record.get("state")) in _REVIEW_STATES
        for record in flatten_pages(reviews)
    )


def _fetch_reviews(repository: str, pr_number: str) -> object:
    return slurp_records(f"repos/{repository}/pulls/{pr_number}/reviews?per_page=100")


def _fetch_review_comments(repository: str, pr_number: str) -> object:
    return slurp_records(f"repos/{repository}/pulls/{pr_number}/comments?per_page=100")


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
    """Wait for a requested standard review, stopping on invalid evidence too."""
    wait = sleep or time.sleep
    clock = monotonic or time.monotonic
    deadline = clock() + timeout_seconds
    while True:
        reviews = _fetch_reviews(repository, pr_number)
        verdict = find_verdict(
            reviews,
            _fetch_review_comments(repository, pr_number),
            head_sha,
            reviewer,
        )
        if verdict is not None or _has_current_review(reviews, head_sha, reviewer):
            return verdict
        if clock() >= deadline:
            return None
        wait(poll_seconds)


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", dest="repository", required=True, metavar="OWNER/REPO")
    parser.add_argument("--pr", dest="pr_number", required=True, metavar="NUMBER")
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--reviewer", default=CODEX_REVIEWER)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Publish the requested review payload; enforcement owns the final result."""
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
            f"::warning::{options.reviewer} left no usable review of {options.head_sha} within "
            f"{options.timeout_seconds}s. The PR author must request `@codex review` "
            "and wait for its GitHub review before this gate can pass."
        )
        publish_step_output("payload=")
        return
    outcome = verdict.get("outcome")
    if outcome not in VALID_OUTCOMES:  # pragma: no cover - validated above
        raise RuntimeError(f"Codex produced an outcome the gate does not know: {outcome!r}")
    publish_step_output(f"payload={json.dumps(verdict, separators=(',', ':'))}")
