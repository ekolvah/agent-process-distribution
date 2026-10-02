"""Wait for the Claude review job's review of a PR head to exist.

The review job publishes under the workflow token, inline comment by inline comment, and
closes with one PR comment naming the head (`Reviewed head SHA: <sha>`). ``--wait`` reads
*whether* that closing comment exists, never what the review says (ADR 0027). Inline
comments without it are an interrupted review, not a review of the head (issue 139).
The job reads once before reviewing, so a re-run of a reviewed head returns on it, and
again after the action, because the action can finish green without publishing (ADR 0004).
Absence exits 3, a read error 2.
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
    from gh_io import run_gh  # type: ignore[import-not-found, no-redef]

REVIEWER = "github-actions"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_POLL_SECONDS = 20
_REVIEWED_HEAD = re.compile(r"Reviewed head SHA: (?P<sha>[0-9a-f]{10,40})")
_COMMENTS_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      headRefOid
      comments(last: 30) { nodes { author { login } body } }
    }
  }
}
"""


def _by_reviewer(node: object) -> bool:
    author = node.get("author") if isinstance(node, Mapping) else None
    login = author.get("login") if isinstance(author, Mapping) else None
    return str(login or "").removesuffix("[bot]").lower() == REVIEWER


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
            f"query={_COMMENTS_QUERY}",
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


def reviewed(pull: Mapping[str, object], head: str) -> bool:
    """True when the review job's closing comment names ``head``."""
    for comment in _nodes(pull, "comments"):
        body = comment.get("body") if isinstance(comment, Mapping) else None
        match = _REVIEWED_HEAD.search(body) if isinstance(body, str) else None
        if _by_reviewer(comment) and match is not None and head.startswith(match.group("sha")):
            return True
    return False


def wait_for_review(
    repo: str, pr: str, head: str, *, timeout_seconds: int, poll_seconds: int
) -> bool:
    """Poll until the review of ``head`` exists or ``timeout_seconds`` pass."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if reviewed(fetch_pull_request(repo, pr), head):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_seconds)


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--wait",
        action="store_true",
        required=True,
        help="wait for the review of --head-sha to exist",
    )
    parser.add_argument("--repo", dest="repository", metavar="OWNER/REPO")
    parser.add_argument("--pr", dest="pr_number", metavar="NUMBER")
    parser.add_argument("--head-sha")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    options = parser.parse_args(argv)
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
    try:
        present = wait_for_review(
            options.repository,
            options.pr_number,
            options.head_sha,
            timeout_seconds=options.timeout_seconds,
            poll_seconds=options.poll_seconds,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot read the reviews of the PR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    who = f"review of {options.head_sha}"
    if present:
        print(f"{who}: present")
        return
    print(f"{who}: absent after {options.timeout_seconds}s")
    raise SystemExit(3)


if __name__ == "__main__":
    main()
