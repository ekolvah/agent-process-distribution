"""Request the Codex review of a PR, or wait for a review to exist on the current head.

Codex's supported GitHub flow is an author comment, ``@codex review``; the
integration then posts a normal GitHub review, or a clean comment naming the
reviewed commit. ``--request`` posts the exact trigger from the authenticated
local PR-author session. ``--wait`` runs in the review job and reads *whether*
a review of the head by any ``--reviewer`` (Codex alone by default) exists — a
native review on that head, or the reviewer's clean comment naming that head —
never what it says (ADR 0027). An error or usage-limit message from the app is
no review: the wait runs to its timeout and exits 3, the job's condition for
the Claude fallback. The job's wait names the Codex app and ``github-actions``,
so a re-run of a head the fallback reviewed returns on that review instead of
reviewing the head again (issue 139). The same read with ``--reviewer
github-actions`` alone verifies that the fallback published under the workflow
token: the action can finish green without a comment (ADR 0004), and a silent
fallback is no review of the head. For that login only the closing comment
naming the head is presence — ``FALLBACK_REVIEWER`` says why.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Mapping, Sequence

try:
    from scripts.gh_io import run_gh
except ModuleNotFoundError:  # documented direct script entry point
    from gh_io import run_gh

CODEX_REVIEWER = "chatgpt-codex-connector[bot]"
# The Claude review job publishes under the workflow token, inline comment by inline
# comment — each a review node on the head. An action interrupted after its first
# comment has left such a node, so for this login a native review is never presence:
# its review is the closing comment naming the head, posted last (issue 139). The
# Codex app submits its review in one piece.
FALLBACK_REVIEWER = "github-actions[bot]"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_POLL_SECONDS = 20
REQUEST_BODY = "@codex review"
# The clean publication names the reviewed head: Codex by a 10-hex prefix
# (`**Reviewed commit:** \`abcdef0123\``), the Claude review job by the contract's
# `Reviewed head SHA: <sha>`. Both are read for presence on this head only.
_REVIEWED_COMMIT = re.compile(
    r"(?:\*\*Reviewed commit:\*\* `|Reviewed head SHA: )(?P<sha>[0-9a-f]{10,40})"
)
_REVIEWS_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      headRefOid
      reviews(last: 30) { nodes { author { login } commit { oid } } }
      comments(last: 30) { nodes { author { login } body } }
    }
  }
}
"""


def request_review(pr_number: str) -> None:
    """Ask Codex to review ``pr_number`` through the authenticated local session."""
    run_gh(["pr", "comment", pr_number, "--body", REQUEST_BODY])


def _normalise_login(value: object) -> str:
    return str(value or "").removesuffix("[bot]").lower()


def _by(reviewers: Sequence[str], node: object) -> bool:
    author = node.get("author") if isinstance(node, Mapping) else None
    login = author.get("login") if isinstance(author, Mapping) else None
    return _normalise_login(login) in {_normalise_login(reviewer) for reviewer in reviewers}


def _nodes(pull: Mapping[str, object], field: str) -> list[object]:
    connection = pull.get(field)
    nodes = connection.get("nodes") if isinstance(connection, Mapping) else None
    if not isinstance(nodes, list):
        raise RuntimeError(f"GraphQL payload has no {field}")
    return nodes


def fetch_pull_request(repo: str, pr: str) -> Mapping[str, object]:
    owner, name = repo.split("/", 1)
    raw = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={_REVIEWS_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={pr}",
        ]
    )
    payload = json.loads(raw)
    data = payload.get("data") if isinstance(payload, Mapping) else None
    repository = data.get("repository") if isinstance(data, Mapping) else None
    pull = repository.get("pullRequest") if isinstance(repository, Mapping) else None
    if not isinstance(pull, Mapping):
        raise RuntimeError("GraphQL payload has no pull request")
    return pull


def reviewed(
    pull: Mapping[str, object], head: str, reviewers: Sequence[str] = (CODEX_REVIEWER,)
) -> bool:
    """True when any of ``reviewers`` left a review on ``head`` or a clean comment naming it.

    For ``FALLBACK_REVIEWER`` the comment alone counts (see the constant).
    """
    fallback = _normalise_login(FALLBACK_REVIEWER)
    atomic = [reviewer for reviewer in reviewers if _normalise_login(reviewer) != fallback]
    for review in _nodes(pull, "reviews"):
        commit = review.get("commit") if isinstance(review, Mapping) else None
        oid = commit.get("oid") if isinstance(commit, Mapping) else None
        if _by(atomic, review) and oid == head:
            return True
    for comment in _nodes(pull, "comments"):
        body = comment.get("body") if isinstance(comment, Mapping) else None
        match = _REVIEWED_COMMIT.search(body) if isinstance(body, str) else None
        if _by(reviewers, comment) and match is not None and head.startswith(match.group("sha")):
            return True
    return False


def wait_for_review(  # noqa: PLR0913 -- baseline: polling clock and limits are injected for tests
    repo: str,
    pr: str,
    head: str,
    *,
    reviewers: Sequence[str],
    timeout_seconds: int,
    poll_seconds: int,
) -> bool:
    """Poll until a review of ``head`` by any of ``reviewers`` exists or ``timeout_seconds`` pass."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if reviewed(fetch_pull_request(repo, pr), head, reviewers):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_seconds)


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--request", metavar="PR", help="post the Codex trigger to this PR")
    mode.add_argument(
        "--wait", action="store_true", help="wait for a Codex review of --head-sha to exist"
    )
    parser.add_argument("--repo", dest="repository", metavar="OWNER/REPO")
    parser.add_argument("--pr", dest="pr_number", metavar="NUMBER")
    parser.add_argument("--head-sha")
    # Repeatable; the default is applied after parsing — an `append` onto a non-empty
    # default would make `--reviewer github-actions` alone read the Codex app too.
    parser.add_argument(
        "--reviewer",
        dest="reviewers",
        action="append",
        metavar="LOGIN",
        help="whose review of --head-sha to wait for; repeatable, any of them counts "
        "(default: the Codex app)",
    )
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    options = parser.parse_args(argv)
    if options.reviewers is None:
        options.reviewers = [CODEX_REVIEWER]
    if options.wait:
        missing = [
            flag
            for flag, value in (
                ("--repo", options.repository),
                ("--pr", options.pr_number),
                ("--head-sha", options.head_sha),
            )
            if value is None
        ]
        if missing:
            parser.error("--wait requires " + ", ".join(missing))
    return options


def main(argv: Sequence[str] | None = None) -> None:
    options = _parse_options(argv)
    if options.request is not None:
        request_review(options.request)
        return
    try:
        present = wait_for_review(
            options.repository,
            options.pr_number,
            options.head_sha,
            reviewers=options.reviewers,
            timeout_seconds=options.timeout_seconds,
            poll_seconds=options.poll_seconds,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot read the reviews of the PR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    who = f"review of {options.head_sha} by {' or '.join(options.reviewers)}"
    if present:
        print(f"{who}: present")
        return
    print(f"{who}: absent after {options.timeout_seconds}s")
    raise SystemExit(3)


if __name__ == "__main__":
    main()
