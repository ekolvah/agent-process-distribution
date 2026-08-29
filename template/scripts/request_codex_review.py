"""Request or read the standard GitHub review that a PR author requested from Codex.

Codex's supported GitHub flow is an owner comment, ``@codex review``. The
integration posts a normal GitHub review: its summary is generic and its actual
findings are inline comments, marked P0 through P3. The ``--request`` mode uses
the authenticated local PR-author session to post the exact trigger; the normal
mode runs in CI, waits for a current-head Codex review, and translates those
native records into the gate's evidence vocabulary.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence

from scripts.check_agent_review_outcome import VALID_OUTCOMES, validated_evidence
from scripts.gh_io import flatten_pages, publish_step_output, run_gh, slurp_records

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
REQUEST_BODY = "@codex review"
_CLEAN_COMMENT_MARKER = "Codex Review: Didn't find any major issues. :tada:"
_REVIEWED_COMMIT = re.compile(r"^\*\*Reviewed commit:\*\* `(?P<sha>[0-9a-f]{10})`$")


def request_review(pr_number: str) -> None:
    """Ask Codex to review ``pr_number`` through the authenticated local session."""
    run_gh(["pr", "comment", pr_number, "--body", REQUEST_BODY])


def _finding(record: Mapping[str, object]) -> dict[str, str] | None:
    body = record.get("body")
    if not isinstance(body, str) or not (summary := body.strip()):
        return None
    priority = _PRIORITY.search(summary)
    if priority is None:
        return None
    severity = _SEVERITIES[priority.group("number")]
    return {"severity": severity, "confidence": "high", "summary": summary}


def _findings_for_review(
    comments: object, review_id: object, reviewer: str
) -> list[dict[str, str]] | None:
    findings: list[dict[str, str]] = []
    for comment in flatten_pages(comments):
        if comment.get("pull_request_review_id") != review_id:
            continue
        author = comment.get("user")
        if (
            not isinstance(author, Mapping)
            or author.get("login") != reviewer
            or comment.get("in_reply_to_id") is not None
        ):
            continue
        finding = _finding(comment)
        if finding is None:
            return None
        findings.append(finding)
    return findings


def _evidence_from_review(
    record: Mapping[str, object], comments: object, reviewer: str
) -> dict[str, object] | None:
    state = str(record.get("state"))
    findings = _findings_for_review(comments, record.get("id"), reviewer)
    if findings is None:
        return None
    if state == "APPROVED":
        return {"outcome": "clean", "findings": []} if not findings else None
    if state not in {"COMMENTED", "CHANGES_REQUESTED"} or not findings:
        return None
    if state == "CHANGES_REQUESTED" and not any(
        finding["severity"] == "blocking" for finding in findings
    ):
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
    matching = [
        record
        for record in flatten_pages(reviews)
        if isinstance(record.get("user"), Mapping)
        and record["user"].get("login") == reviewer
        and record.get("commit_id") == head_sha
    ]
    if not matching:
        return None
    _, latest = max(
        enumerate(matching), key=lambda item: (str(item[1].get("submitted_at", "")), item[0])
    )
    return _evidence_from_review(latest, comments, reviewer)


def _has_current_review(reviews: object, head_sha: str, reviewer: str) -> bool:
    return any(
        isinstance(record.get("user"), Mapping)
        and record["user"].get("login") == reviewer
        and record.get("commit_id") == head_sha
        and str(record.get("state")) in _REVIEW_STATES
        for record in flatten_pages(reviews)
    )


def _latest_evidence(
    candidates: Sequence[tuple[str, dict[str, object] | None]],
) -> dict[str, object] | None:
    if not candidates:
        return None
    latest_timestamp = max(candidate[0] for candidate in candidates)
    latest = [candidate[1] for candidate in candidates if candidate[0] == latest_timestamp]
    if any(evidence is None for evidence in latest):
        return None
    return max(
        [evidence for evidence in latest if evidence is not None],
        key=lambda evidence: {"clean": 0, "rework": 1, "blocking": 2}.get(
            str(evidence.get("outcome")), -1
        ),
    )


def _native_evidence_candidates(
    reviews: object,
    comments: object,
    head_sha: str,
    reviewer: str,
) -> list[tuple[str, dict[str, object] | None]]:
    matching: list[tuple[str, int, Mapping[str, object]]] = []
    for index, record in enumerate(flatten_pages(reviews)):
        if (
            not isinstance(record.get("user"), Mapping)
            or record["user"].get("login") != reviewer
            or record.get("commit_id") != head_sha
        ):
            continue
        submitted_at = record.get("submitted_at")
        matching.append((submitted_at if isinstance(submitted_at, str) else "", index, record))
    if not matching:
        return []
    submitted_at, _, latest = max(matching, key=lambda candidate: (candidate[0], candidate[1]))
    evidence = _evidence_from_review(latest, comments, reviewer)
    return [(submitted_at, evidence)]


def _read_record(endpoint: str) -> Mapping[str, object]:
    try:
        payload = json.loads(run_gh(["api", endpoint]))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh api {endpoint} returned invalid JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RuntimeError(f"unexpected payload shape from {endpoint}: {type(payload).__name__}")
    return payload


def _clean_reaction_context(repository: str, pr_number: str, head_sha: str) -> str:
    pull = _read_record(f"repos/{repository}/pulls/{pr_number}")
    author = pull.get("user")
    author_login = author.get("login") if isinstance(author, Mapping) else None
    head = pull.get("head")
    if (
        not isinstance(author_login, str)
        or not isinstance(head, Mapping)
        or head.get("sha") != head_sha
    ):
        raise RuntimeError("live PR author or head SHA is unavailable")
    return author_login


def find_clean_reaction(
    requests: object,
    reactions_by_request: Mapping[object, object],
    *,
    author_login: str,
    head_observed_at: str,
    reviewer: str,
) -> dict[str, object] | None:
    """Accept only the native clean reaction tied to this author and head."""
    for request in reversed(flatten_pages(requests)):
        author = request.get("user")
        if (
            not isinstance(author, Mapping)
            or author.get("login") != author_login
            or request.get("body") != "@codex review"
            or not isinstance(request.get("created_at"), str)
            or request["created_at"] < head_observed_at
        ):
            continue
        reactions = reactions_by_request.get(request.get("id"), [])
        if any(
            reaction.get("content") == "+1"
            and isinstance(reaction.get("user"), Mapping)
            and reaction["user"].get("login") == reviewer
            for reaction in flatten_pages(reactions)
        ):
            return {"outcome": "clean", "findings": []}
    return None


def _eligible_requests(
    requests: object,
    *,
    author_login: str,
    head_observed_at: str,
) -> list[Mapping[str, object]]:
    return [
        request
        for request in flatten_pages(requests)
        if isinstance(request.get("user"), Mapping)
        and request["user"].get("login") == author_login
        and request.get("body") == REQUEST_BODY
        and isinstance(request.get("created_at"), str)
        and request["created_at"] >= head_observed_at
    ]


def _clean_reaction_candidates(
    requests: object,
    reactions_by_request: Mapping[object, object],
    *,
    author_login: str,
    head_observed_at: str,
    reviewer: str,
) -> list[tuple[str, dict[str, object]]]:
    candidates: list[tuple[str, dict[str, object]]] = []
    for request in _eligible_requests(
        requests, author_login=author_login, head_observed_at=head_observed_at
    ):
        for reaction in flatten_pages(reactions_by_request.get(request.get("id"), [])):
            if (
                reaction.get("content") != "+1"
                or not isinstance(reaction.get("user"), Mapping)
                or reaction["user"].get("login") != reviewer
            ):
                continue
            created_at = reaction.get("created_at")
            timestamp = created_at if isinstance(created_at, str) else request["created_at"]
            candidates.append((timestamp, {"outcome": "clean", "findings": []}))
    return candidates


def _clean_comment_candidates(
    records: object,
    *,
    author_login: str,
    head_sha: str,
    head_observed_at: str,
    reviewer: str,
) -> list[tuple[str, dict[str, object]]]:
    eligible_requests = _eligible_requests(
        records, author_login=author_login, head_observed_at=head_observed_at
    )
    request_times = [request["created_at"] for request in eligible_requests]
    candidates: list[tuple[str, dict[str, object]]] = []
    for record in flatten_pages(records):
        author = record.get("user")
        body = record.get("body")
        created_at = record.get("created_at")
        if (
            not isinstance(author, Mapping)
            or author.get("login") != reviewer
            or not isinstance(body, str)
            or not isinstance(created_at, str)
            or created_at <= head_observed_at
            or not request_times
            or not any(request_time < created_at for request_time in request_times)
        ):
            continue
        lines = body.splitlines()
        reviewed_lines = [line for line in lines if "Reviewed commit" in line]
        if not lines or lines[0] != _CLEAN_COMMENT_MARKER or len(reviewed_lines) != 1:
            continue
        reviewed_commit = _REVIEWED_COMMIT.fullmatch(reviewed_lines[0])
        if reviewed_commit is None or not head_sha.startswith(reviewed_commit["sha"]):
            continue
        candidates.append((created_at, {"outcome": "clean", "findings": []}))
    return candidates


def find_clean_comment(
    records: object,
    *,
    author_login: str,
    head_sha: str,
    head_observed_at: str,
    reviewer: str,
) -> dict[str, object] | None:
    """Accept only the observed SHA-bound clean Codex issue-comment transport."""
    return _latest_evidence(
        _clean_comment_candidates(
            records,
            author_login=author_login,
            head_sha=head_sha,
            head_observed_at=head_observed_at,
            reviewer=reviewer,
        )
    )


def _fetch_reviews(repository: str, pr_number: str) -> object:
    return slurp_records(f"repos/{repository}/pulls/{pr_number}/reviews?per_page=100")


def _fetch_review_comments(repository: str, pr_number: str) -> object:
    return slurp_records(f"repos/{repository}/pulls/{pr_number}/comments?per_page=100")


def _fetch_request_comments(repository: str, pr_number: str) -> object:
    return slurp_records(f"repos/{repository}/issues/{pr_number}/comments?per_page=100")


def _fetch_reactions(repository: str, comment_id: object) -> object:
    return slurp_records(f"repos/{repository}/issues/comments/{comment_id}/reactions?per_page=100")


def poll_for_verdict(
    repository: str,
    pr_number: str,
    head_sha: str,
    *,
    head_observed_at: str,
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
    author_login: str | None = None
    while True:
        reviews = _fetch_reviews(repository, pr_number)
        native_candidates = _native_evidence_candidates(
            reviews, _fetch_review_comments(repository, pr_number), head_sha, reviewer
        )
        if author_login is None:
            author_login = _clean_reaction_context(repository, pr_number, head_sha)
        requests = _fetch_request_comments(repository, pr_number)
        reactions = {
            request.get("id"): _fetch_reactions(repository, request.get("id"))
            for request in flatten_pages(requests)
            if request.get("body") == "@codex review"
        }
        candidates = [
            *native_candidates,
            *_clean_reaction_candidates(
                requests,
                reactions,
                author_login=author_login,
                head_observed_at=head_observed_at,
                reviewer=reviewer,
            ),
        ]
        candidates.extend(
            _clean_comment_candidates(
                requests,
                author_login=author_login,
                head_sha=head_sha,
                head_observed_at=head_observed_at,
                reviewer=reviewer,
            )
        )
        verdict = _latest_evidence(candidates)
        if verdict is not None:
            return verdict
        if clock() >= deadline:
            return None
        wait(poll_seconds)


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--request", metavar="PR", help="post the Codex trigger to this PR")
    parser.add_argument("--repo", dest="repository", metavar="OWNER/REPO")
    parser.add_argument("--pr", dest="pr_number", metavar="NUMBER")
    parser.add_argument("--head-sha")
    parser.add_argument(
        "--head-observed-at",
        help="GitHub event timestamp for the current PR head transition.",
    )
    parser.add_argument("--reviewer", default=CODEX_REVIEWER)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    options = parser.parse_args(argv)
    if options.request is not None:
        return options
    missing = [
        flag
        for flag, value in (
            ("--repo", options.repository),
            ("--pr", options.pr_number),
            ("--head-sha", options.head_sha),
            ("--head-observed-at", options.head_observed_at),
        )
        if value is None
    ]
    if missing:
        parser.error("the read mode requires " + ", ".join(missing))
    return options


def main(argv: Sequence[str] | None = None) -> None:
    """Publish the requested review payload; enforcement owns the final result."""
    options = _parse_options(argv)
    if options.request is not None:
        request_review(options.request)
        return
    verdict = poll_for_verdict(
        options.repository,
        options.pr_number,
        options.head_sha,
        head_observed_at=options.head_observed_at,
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


if __name__ == "__main__":
    main()
