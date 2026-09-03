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
# Sub-marker inside a fallback comment's body, distinguishing an unvalidated
# render from a validated one so the sticky-comment update can resolve a
# collision on one head SHA by precedence: validated always wins.
_UNVALIDATED_MARKER = "<!-- agent-review-unvalidated -->"
# The raw carrier payload is arbitrary, untrusted-length text; cap it so an
# oversized payload cannot blow out the check summary or PR comment.
_UNVALIDATED_PAYLOAD_CHAR_LIMIT = 4000
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


def _validate(
    payload: object,
) -> tuple[tuple[str, list[dict[str, str]]] | None, str | None]:
    """Return `(evidence, None)` when valid, else `(None, reason)`.

    The single home for the validity rule: `validated_evidence()` below is a
    thin wrapper, not a second copy of this policy.
    """
    if not isinstance(payload, dict) or set(payload) != {"outcome", "findings"}:
        return None, "payload must be a JSON object with exactly 'outcome' and 'findings'"
    outcome = payload.get("outcome")
    findings = payload.get("findings")
    if outcome not in VALID_OUTCOMES:
        return None, f"unknown outcome {outcome!r}"
    if not isinstance(findings, list):
        return None, "'findings' is not a list"

    validated: list[dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"severity", "confidence", "summary"}:
            return None, "a finding is missing severity/confidence/summary"
        severity = finding.get("severity")
        confidence = finding.get("confidence")
        summary = finding.get("summary")
        if severity not in VALID_SEVERITIES:
            return None, f"a finding has an unknown severity {severity!r}"
        if confidence not in VALID_CONFIDENCES:
            return None, f"a finding has an unknown confidence {confidence!r}"
        if not isinstance(summary, str) or not summary.strip():
            return None, "a finding is missing a summary"
        validated.append(
            {"severity": severity, "confidence": confidence, "summary": summary.strip()}
        )

    if outcome == "clean":
        if validated:
            return None, "outcome 'clean' may not carry a finding"
        return (outcome, validated), None
    if outcome == "rework":
        if not validated:
            return None, "outcome 'rework' requires at least one finding"
        if any(finding["severity"] == "blocking" for finding in validated):
            return None, "outcome 'rework' may not carry a blocking finding"
        return (outcome, validated), None
    if outcome == "blocking":
        if not any(finding["severity"] == "blocking" for finding in validated):
            return None, "outcome 'blocking' requires at least one blocking finding"
        return (outcome, validated), None
    return None, f"unknown outcome {outcome!r}"


def validated_evidence(payload: object) -> tuple[str, list[dict[str, str]]] | None:
    """Return only evidence that can support the declared review outcome."""
    evidence, _reason = _validate(payload)
    return evidence


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


def _payload_is_present(payload_arg: str) -> bool:
    """Carrier produced output worth surfacing, whether or not it later validates.

    Non-empty after `.strip()`, and — when it parses as JSON — not one of the
    values that mean "nothing ran": `null`, `{}`, `[]`, `""`. A non-empty
    string that fails to parse as JSON is present; there is text to show.
    """
    stripped = payload_arg.strip()
    if not stripped:
        return False
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return True
    return parsed not in (None, {}, [], "")


def _run_url() -> str | None:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def _best_effort_fields(payload: object) -> list[str]:
    """Render whatever outcome/finding fields a rejected payload does contain."""
    if not isinstance(payload, dict):
        return []
    lines: list[str] = []
    outcome = payload.get("outcome")
    if isinstance(outcome, str):
        lines.append(f"Reported outcome: `{outcome}`")
    findings = payload.get("findings")
    if isinstance(findings, list):
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            label_bits = [
                str(finding[key])
                for key in ("severity", "confidence")
                if isinstance(finding.get(key), str)
            ]
            label = "/".join(label_bits) if label_bits else "unknown"
            summary = finding.get("summary")
            if isinstance(summary, str) and summary.strip():
                lines.append(f"- **{label}**: {summary.strip()}")
    return lines


def _neutralize_fence_delimiters(text: str) -> str:
    """Prevent an embedded backtick from escaping the fenced raw-payload block

    or forging the backtick-quoted head-SHA anchor the sticky comment matches
    on."""
    return text.replace("`", "'")


def _capped(text: str, limit: int = _UNVALIDATED_PAYLOAD_CHAR_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}... [{len(text) - limit} more chars truncated]"


def _unvalidated_evidence_lines(
    payload_arg: str, payload: object, reason: str, reviewed_head_sha: str | None
) -> list[str]:
    """Render present-but-invalid carrier output for visibility, never as a verdict.

    The raw payload is rendered length-capped inside a fenced block with
    backticks neutralised, so it can never forge the marker or the
    backtick-quoted head-SHA line that comment identity is matched against.
    """
    lines = [
        _UNVALIDATED_MARKER,
        "## Unvalidated agent-review evidence",
        "",
        "This output did not pass validation and must not be read as a verdict; "
        "the required check still failed.",
        "",
        f"Reason: {reason}",
        "",
        f"Reviewed head SHA: `{reviewed_head_sha}`",
    ]
    run_url = _run_url()
    if run_url:
        lines.extend(["", f"Run: {run_url}"])
    best_effort = _best_effort_fields(payload)
    if best_effort:
        lines.append("")
        lines.extend(best_effort)
    lines.extend(
        [
            "",
            "Raw carrier output:",
            "```",
            _neutralize_fence_delimiters(_capped(payload_arg)),
            "```",
        ]
    )
    return lines


def _publish_summary(lines: list[str], reviewed_head_sha: str | None) -> None:
    """Write the given evidence lines to the durable Actions check summary."""
    if not reviewed_head_sha:
        print("error: --publish-summary needs --reviewed-head-sha", file=sys.stderr)
        raise SystemExit(2)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destination:
        print("error: GITHUB_STEP_SUMMARY is unavailable", file=sys.stderr)
        raise SystemExit(2)
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
    lines: list[str],
    *,
    is_validated: bool,
    reviewed_head_sha: str | None,
    repo: str | None,
    pr: str | None,
) -> None:
    """Publish the Claude fallback's evidence — validated or not — as a sticky PR comment.

    Never a GitHub review (`REQUEST_CHANGES`/`APPROVE`): that verdict already
    belongs to the required `agent-review` check, and only the Codex primary
    carrier leaves its own native review. This is a plain, non-verdict
    conversation comment, one per PR, updated in place.

    A collision on one head SHA is resolved by **precedence, not equality**: a
    validated block always wins. It replaces an already-posted unvalidated
    block for that head; an unvalidated block never overwrites a validated
    one. Otherwise, a re-run of the same kind on an unchanged head is a no-op
    and a new head (or a kind change) replaces the stale comment.
    """
    if not reviewed_head_sha:
        print("error: --publish-pr-comment needs --reviewed-head-sha", file=sys.stderr)
        raise SystemExit(2)
    if not repo or not pr:
        print("error: --publish-pr-comment needs --repo and --pr", file=sys.stderr)
        raise SystemExit(2)
    body = "\n".join([_FALLBACK_MARKER, *lines])
    head_line = f"Reviewed head SHA: `{reviewed_head_sha}`"

    existing = [
        comment
        for comment in _existing_pr_comments(repo, pr)
        if isinstance(comment.get("body"), str) and _FALLBACK_MARKER in comment["body"]
    ]
    if existing:
        comment = existing[-1]
        existing_body = str(comment.get("body", ""))
        existing_is_validated = _UNVALIDATED_MARKER not in existing_body
        if existing_is_validated and not is_validated:
            print("ok: an existing validated comment is never overwritten by unvalidated evidence")
            return
        if existing_is_validated == is_validated and head_line in existing_body:
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
        malformed_json = False
    except json.JSONDecodeError:
        payload = None
        malformed_json = True
    evidence, reason = _validate(payload)
    if malformed_json:
        reason = "payload is not valid JSON"

    if options.classify:
        _report_validity(evidence)
        return

    producer = options.producer
    _require_live_pr_context(options.live_pr_context_status)
    if evidence is None:
        if _payload_is_present(payload_arg):
            lines = _unvalidated_evidence_lines(
                payload_arg, payload, reason or "invalid evidence", options.reviewed_head_sha
            )
            if options.publish_summary:
                _publish_summary(lines, options.reviewed_head_sha)
            elif options.publish_pr_comment:
                _publish_pr_comment(
                    lines,
                    is_validated=False,
                    reviewed_head_sha=options.reviewed_head_sha,
                    repo=options.repo,
                    pr=options.pr,
                )
        print(
            f"error: {producer} unavailable: no valid structured review evidence.", file=sys.stderr
        )
        raise SystemExit(2)
    if options.publish_summary:
        _publish_summary(
            _evidence_lines(evidence, options.reviewed_head_sha), options.reviewed_head_sha
        )
        return
    if options.publish_pr_comment:
        _publish_pr_comment(
            _evidence_lines(evidence, options.reviewed_head_sha),
            is_validated=True,
            reviewed_head_sha=options.reviewed_head_sha,
            repo=options.repo,
            pr=options.pr,
        )
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
