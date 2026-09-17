"""Request the Codex review of a PR, or wait for it to exist on the current head.

Codex's supported GitHub flow is an author comment, ``@codex review``; the
integration then posts a normal GitHub review, or a clean comment naming the
reviewed commit. ``--request`` posts the exact trigger from the authenticated
local PR-author session. ``--wait`` runs in the review job and reads *whether*
a Codex review of the head exists — a native review on that head, or the
app's clean comment naming that head — never what it says (ADR 0027). An
error or usage-limit message from the app is no review: the wait runs to its
timeout and exits 3, the job's condition for the Claude fallback.
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
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_POLL_SECONDS = 20
REQUEST_BODY = "@codex review"
# The app's clean transport names the reviewed commit by a 10-hex prefix; the
# match is a fact about the app, read for presence on this head only.
_REVIEWED_COMMIT = re.compile(r"\*\*Reviewed commit:\*\* `(?P<sha>[0-9a-f]{10})`")
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


def _by_codex(node: object) -> bool:
    author = node.get("author") if isinstance(node, Mapping) else None
    login = author.get("login") if isinstance(author, Mapping) else None
    return _normalise_login(login) == _normalise_login(CODEX_REVIEWER)


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


def codex_reviewed(pull: Mapping[str, object], head: str) -> bool:
    """True when Codex left a review on ``head`` or its clean comment naming ``head``."""
    for review in _nodes(pull, "reviews"):
        commit = review.get("commit") if isinstance(review, Mapping) else None
        oid = commit.get("oid") if isinstance(commit, Mapping) else None
        if _by_codex(review) and oid == head:
            return True
    for comment in _nodes(pull, "comments"):
        body = comment.get("body") if isinstance(comment, Mapping) else None
        match = _REVIEWED_COMMIT.search(body) if isinstance(body, str) else None
        if _by_codex(comment) and match is not None and head.startswith(match.group("sha")):
            return True
    return False


def wait_for_codex_review(
    repo: str, pr: str, head: str, *, timeout_seconds: int, poll_seconds: int
) -> bool:
    """Poll until a Codex review of ``head`` exists or ``timeout_seconds`` pass."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        if codex_reviewed(fetch_pull_request(repo, pr), head):
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
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    options = parser.parse_args(argv)
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
        present = wait_for_codex_review(
            options.repository,
            options.pr_number,
            options.head_sha,
            timeout_seconds=options.timeout_seconds,
            poll_seconds=options.poll_seconds,
        )
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot read the reviews of the PR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if present:
        print(f"codex review of {options.head_sha}: present")
        return
    print(f"codex review of {options.head_sha}: absent after {options.timeout_seconds}s")
    raise SystemExit(3)


if __name__ == "__main__":
    main()
