"""Map a structured review outcome to a deterministic workflow result.

Merge authority is deliberately narrower than report coverage: `blocking`
reds the required check, `clean` and `rework` pass (the latter with a visible
`::warning::`), and every state that is *not* evidence — empty, malformed,
unknown outcome, or an unavailable live PR context — stays red. Absence of
evidence must never read as success (§IV).

The required check has an owner-requested Codex primary and a Claude availability
fallback. This module validates whichever verdict the workflow selected before
judging it. That question lives here because the validity rule lives here;
asked as a YAML `contains()`/`fromJSON()` expression it would become a second,
untestable home for the same policy.

The rule has no path-based exception any more. A PR touching the review
controller used to pass with a `::warning::` on an empty outcome, because the
action could not review it at all: the App-token exchange refused a workflow file
that differs from `main`. The workflow now runs the review under `github.token`,
so such a PR gets an ordinary verdict — and an empty outcome is an unavailable
review here exactly as anywhere else.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Sequence

try:
    from scripts.gh_io import flatten_pages, publish_step_output, run_gh
except ModuleNotFoundError:  # documented direct script entry point
    from gh_io import flatten_pages, publish_step_output, run_gh

# The Codex adapter translates GitHub review states into this vocabulary; a
# second private copy there would be a second merge bar.
VALID_OUTCOMES = frozenset({"clean", "rework", "blocking"})
VALID_SEVERITIES = frozenset({"blocking", "should-fix", "nice-to-have"})
VALID_CONFIDENCES = frozenset({"high", "medium", "low"})
_DEFAULT_PRODUCER = "Codex review"
_SEVERITY_LABELS = {
    "blocking": "BLOCKING",
    "should-fix": "NON-BLOCKING",
    "nice-to-have": "NON-BLOCKING",
}
_SEVERITY_ORDER = {"blocking": 0, "should-fix": 1, "nice-to-have": 2}
# The reusable workflow greps the trusted checkout for this marker before
# wiring `--publish-pr-comment`: on the introducing PR, the default branch is
# still the pre-#35 script and does not have the flag yet (the trusted
# checkout pattern means the PR's own worktree can never supply it — see
# agent-process.md's transition-PR bootstrap note). A missing marker is a
# visible skip, not a failure, exactly like `STANDARD_REVIEW_PARSER`.
PUBLISH_PR_COMMENT_SUPPORTED = True
# Marks the one sticky PR-conversation comment the Claude fallback owns, so a
# re-run finds and updates it instead of leaving the carrier's own findings
# invisible outside the check summary. Distinct from
# check_blocking_review_threads.py's `_CLASSIFICATION_MARKER`: that one
# classifies individual Codex threads, this one owns one whole-review comment.
_FALLBACK_MARKER = "<!-- agent-review-claude-fallback -->"
# The reusable workflow greps the trusted checkout for this marker before
# wiring `--diagnose-execution-file`, the same bootstrap pattern as
# `PUBLISH_PR_COMMENT_SUPPORTED` above.
DIAGNOSE_EXECUTION_FILE_SUPPORTED = True

# Closed set of known provider-failure signatures. `_classify_provider_status`
# returns only the category name — never the matched text — so a secret or
# other sensitive string embedded in `result`/`errors` cannot reach the log.
_PROVIDER_STATUS_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "auth_or_account",
        re.compile(
            r"\b(401|unauthorized|invalid[ _-]?api[ _-]?key|authentication|oauth|account)\b",
            re.IGNORECASE,
        ),
    ),
    ("rate_limited", re.compile(r"\b(429|rate[ _-]?limit(?:ed)?)\b", re.IGNORECASE)),
    ("overloaded", re.compile(r"\b(529|overloaded)\b", re.IGNORECASE)),
)
_UNKNOWN_PROVIDER_STATUS = "unknown_provider_error"
_SCHEMA_VIOLATION_STATUS = "schema_violation"


class _Options:
    """Parsed CLI options; the payload itself is positional."""

    def __init__(self) -> None:
        self.live_pr_context_status: str | None = None
        self.producer: str = _DEFAULT_PRODUCER
        self.classify: bool = False
        self.publish_summary: bool = False
        self.publish_pr_comment: bool = False
        self.reviewed_head_sha: str | None = None
        self.repo: str | None = None
        self.pr: str | None = None


def _parse_options(args: list[str]) -> _Options:
    options = _Options()
    while args:
        option = args.pop(0)
        if option == "--classify":
            options.classify = True
            continue
        if option == "--publish-summary":
            options.publish_summary = True
            continue
        if option == "--publish-pr-comment":
            options.publish_pr_comment = True
            continue
        if not args:
            print(f"error: expected a value after {option}", file=sys.stderr)
            raise SystemExit(2)
        value = args.pop(0)
        if option == "--live-pr-context-status":
            options.live_pr_context_status = value
        elif option == "--producer":
            options.producer = value
        elif option == "--reviewed-head-sha":
            options.reviewed_head_sha = value
        elif option == "--repo":
            options.repo = value
        elif option == "--pr":
            options.pr = value
        else:
            print(f"error: unexpected argument {option}", file=sys.stderr)
            raise SystemExit(2)

    return options


def _require_live_pr_context(status: str | None) -> None:
    if status is not None and status != "success":
        print(
            "error: live PR context is unavailable; inspect 'Fetch current PR context' "
            "and re-run after GitHub API access recovers.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def validated_evidence(payload: object) -> tuple[str, list[dict[str, str]]] | None:
    """Return only evidence that can support the declared review outcome."""
    if not isinstance(payload, dict) or set(payload) != {"outcome", "findings"}:
        return None
    outcome = payload.get("outcome")
    findings = payload.get("findings")
    if outcome not in VALID_OUTCOMES or not isinstance(findings, list):
        return None

    validated: list[dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"severity", "confidence", "summary"}:
            return None
        severity = finding.get("severity")
        confidence = finding.get("confidence")
        summary = finding.get("summary")
        if (
            severity not in VALID_SEVERITIES
            or confidence not in VALID_CONFIDENCES
            or not isinstance(summary, str)
            or not summary.strip()
        ):
            return None
        validated.append(
            {"severity": severity, "confidence": confidence, "summary": summary.strip()}
        )

    if outcome == "clean":
        return (outcome, validated) if not validated else None
    if outcome == "rework":
        return (
            (outcome, validated)
            if validated and all(finding["severity"] != "blocking" for finding in validated)
            else None
        )
    if outcome == "blocking":
        return (
            (outcome, validated)
            if any(finding["severity"] == "blocking" for finding in validated)
            else None
        )
    return None


def _report_validity(evidence: tuple[str, list[dict[str, str]]] | None) -> None:
    """Publish «did this carrier produce a usable verdict» and exit 0 either way.

    Measuring is not judging: a non-zero exit here would end the job before the
    second carrier was ever asked, and a `blocking` verdict is a result — treating
    it as invalid would let the failover overrule the carrier that found it.
    """
    publish_step_output(f"valid={'true' if evidence is not None else 'false'}")


def _evidence_lines(
    evidence: tuple[str, list[dict[str, str]]], reviewed_head_sha: str
) -> list[str]:
    """Render validated evidence once, shared by the step summary and the PR comment."""
    outcome, findings = evidence
    lines = [
        "## Validated agent-review evidence",
        "",
        f"Reviewed head SHA: `{reviewed_head_sha}`",
        "",
        f"Outcome: `{outcome}`",
        "",
    ]
    if findings:
        ordered = sorted(findings, key=lambda finding: _SEVERITY_ORDER[finding["severity"]])
        lines.extend(
            f"- **{_SEVERITY_LABELS[finding['severity']]} ({finding['confidence']})**: "
            f"{finding['summary']}"
            for finding in ordered
        )
    else:
        lines.append("No findings.")
    return lines


def _publish_summary(
    evidence: tuple[str, list[dict[str, str]]], reviewed_head_sha: str | None
) -> None:
    """Write the validated review evidence to the durable Actions check summary."""
    if not reviewed_head_sha:
        print("error: --publish-summary needs --reviewed-head-sha", file=sys.stderr)
        raise SystemExit(2)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destination:
        print("error: GITHUB_STEP_SUMMARY is unavailable", file=sys.stderr)
        raise SystemExit(2)
    lines = _evidence_lines(evidence, reviewed_head_sha)
    try:
        with open(destination, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError as exc:
        print(f"error: cannot write GITHUB_STEP_SUMMARY {destination!r}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _existing_pr_comments(repo: str, pr: str) -> list[dict[str, object]]:
    """List a PR's conversation comments through the shared `run_gh` boundary.

    Deliberately not `scripts.gh_io.slurp_records`: that helper calls its own
    module-level `run_gh`, which a test here cannot substitute. Going through
    this module's own `run_gh` name keeps one monkeypatch point, matching
    `check_blocking_review_threads.py`'s pattern.
    """
    raw = run_gh(["api", f"repos/{repo}/issues/{pr}/comments", "--paginate", "--slurp"])
    return list(flatten_pages(json.loads(raw)))


def _publish_pr_comment(
    evidence: tuple[str, list[dict[str, str]]],
    reviewed_head_sha: str | None,
    repo: str | None,
    pr: str | None,
) -> None:
    """Publish the Claude fallback's validated evidence as a sticky PR comment.

    Never a GitHub review (`REQUEST_CHANGES`/`APPROVE`): that verdict already
    belongs to the required `agent-review` check, and only the Codex primary
    carrier leaves its own native review. This is a plain, non-verdict
    conversation comment, one per PR, updated in place — keyed on the
    reviewed head SHA so a re-run on the same head is a no-op and a new head
    replaces the stale findings rather than leaving them looking current.
    """
    if not reviewed_head_sha:
        print("error: --publish-pr-comment needs --reviewed-head-sha", file=sys.stderr)
        raise SystemExit(2)
    if not repo or not pr:
        print("error: --publish-pr-comment needs --repo and --pr", file=sys.stderr)
        raise SystemExit(2)
    body = "\n".join([_FALLBACK_MARKER, *_evidence_lines(evidence, reviewed_head_sha)])
    head_line = f"Reviewed head SHA: `{reviewed_head_sha}`"

    existing = [
        comment
        for comment in _existing_pr_comments(repo, pr)
        if isinstance(comment.get("body"), str) and _FALLBACK_MARKER in comment["body"]
    ]
    if existing:
        comment = existing[-1]
        if head_line in str(comment.get("body", "")):
            print("ok: fallback findings already posted for this reviewed head")
            return
        comment_id = comment.get("id")
        if not isinstance(comment_id, int):
            raise RuntimeError("an existing fallback PR comment has no numeric id")
        run_gh(
            [
                "api",
                "--method",
                "PATCH",
                f"repos/{repo}/issues/comments/{comment_id}",
                "-f",
                f"body={body}",
            ]
        )
        return
    run_gh(
        [
            "api",
            "--method",
            "POST",
            f"repos/{repo}/issues/{pr}/comments",
            "-f",
            f"body={body}",
        ]
    )


def _classify_provider_status(texts: list[str]) -> str:
    """Map free-form failure text to a fixed, safe category — never the text itself."""
    for category, pattern in _PROVIDER_STATUS_PATTERNS:
        if any(pattern.search(text) for text in texts):
            return category
    return _UNKNOWN_PROVIDER_STATUS


def _diagnose_execution_file(path: str) -> None:
    """Report only an allowlisted provider status from a Claude execution file.

    This is diagnosis, not a merge gate: it never emits `result`, `errors`,
    prompts, tool/model messages, or any other raw execution-file field — only
    a closed status category — and it always exits non-zero.
    `check_agent_review_outcome.py`'s existing classify/publish/enforce entry
    points remain the sole structured-evidence merge gate; absence of
    evidence must never read as success (§IV).
    """
    try:
        with open(path, encoding="utf-8") as handle:
            messages = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"error: Claude execution file {path!r} is unavailable or malformed: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    if not isinstance(messages, list):
        print(
            f"error: Claude execution file {path!r} is malformed: expected a message array",
            file=sys.stderr,
        )
        raise SystemExit(1)

    result: dict[str, object] | None = None
    for message in messages:
        if isinstance(message, dict) and message.get("type") == "result":
            result = message
    if result is None:
        print(
            f"error: Claude execution file {path!r} is malformed: no result message found",
            file=sys.stderr,
        )
        raise SystemExit(1)

    is_error = result.get("is_error")
    if is_error:
        texts = [
            text
            for text in (
                result.get("result"),
                *(result.get("errors") if isinstance(result.get("errors"), list) else []),
            )
            if isinstance(text, str)
        ]
        status = _classify_provider_status(texts)
    elif validated_evidence(result.get("structured_output")) is None:
        status = _SCHEMA_VIOLATION_STATUS
    else:
        status = _UNKNOWN_PROVIDER_STATUS

    print(f"error: Claude fallback diagnosis: status={status}", file=sys.stderr)
    raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> None:
    """Exit non-zero unless the carrier's validated outcome is ``clean`` or ``rework``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("error: expected one structured review outcome JSON value", file=sys.stderr)
        raise SystemExit(2)
    if args[0] == "--diagnose-execution-file":
        if len(args) != 2:
            print("error: --diagnose-execution-file needs exactly one path", file=sys.stderr)
            raise SystemExit(2)
        _diagnose_execution_file(args[1])
        return
    payload_arg = args.pop(0)
    options = _parse_options(args)

    try:
        payload = json.loads(payload_arg)
    except json.JSONDecodeError:
        payload = None
    evidence = validated_evidence(payload)

    if options.classify:
        _report_validity(evidence)
        return

    producer = options.producer
    _require_live_pr_context(options.live_pr_context_status)
    if evidence is None:
        print(
            f"error: {producer} unavailable: no valid structured review evidence.", file=sys.stderr
        )
        raise SystemExit(2)
    if options.publish_summary:
        _publish_summary(evidence, options.reviewed_head_sha)
        return
    if options.publish_pr_comment:
        _publish_pr_comment(evidence, options.reviewed_head_sha, options.repo, options.pr)
        return

    outcome, _findings = evidence
    if outcome == "clean":
        print(f"ok: {producer} outcome is clean")
        return
    if outcome == "rework":
        # Report completeness is not merge authority. The prompt requires
        # every finding to be reported, so a should-fix finding is the normal
        # outcome of a thorough review — reding the required check on it made a
        # green result unreachable by construction after repeated cosmetic-only
        # rounds. The findings stay visible in the PR and
        # become the maintainer's call, not an automatic barrier.
        print(
            f"::warning::{producer} reported should-fix findings. They are published "
            "in the PR and are the maintainer's call — not an automatic merge blocker. "
            "Only blocking findings red this check."
        )
        return
    if outcome == "blocking":
        print(
            f"error: {producer} reported blocking findings; resolve and re-run review.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    # Naming the carrier matters most here: two carriers whose «unavailable» reads
    # identically leave the operator unable to tell which one came back empty (§IV).
    raise AssertionError(f"validated evidence had an unknown outcome: {outcome!r}")


if __name__ == "__main__":
    main()
