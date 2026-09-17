#!/usr/bin/env python3
"""Resolve one P0/P1 review thread the fixer's own correction addressed.

Usage: python .agent-process/scripts/resolve_review_thread.py --repo OWNER/REPO --pr N
           --list | --thread NODE-ID --reply-file PATH

CI never infers whether a finding was addressed (ADR 0022): the required
check (`check_blocking_review_threads.py`) answers "may this PR merge?" from
the workflow token over the P0/P1 threads of either reviewer — the Codex app
or the Claude review job — and this script answers "I, the fixer, addressed
this finding" from the maintainer's authenticated local session. Different
actor, credential, and trigger — never wired into a workflow.

`--thread` is the whole step after `wait_for_pr.py`: it refuses while the head's
`agent-review` run is running, resolves the thread, re-runs that run (a resolve
has no event of its own, and the required context is the head's `pull_request`
run — ADR 0027) and posts the reply last. The order lives here, not in a rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence

try:
    from scripts.check_blocking_review_threads import (
        blocking_threads,
        fetch_review_threads,
        head_ref_oid,
        review_threads,
    )
    from scripts.gh_io import run_gh
except ModuleNotFoundError:  # Direct execution from the relocated payload.
    from check_blocking_review_threads import (
        blocking_threads,
        fetch_review_threads,
        head_ref_oid,
        review_threads,
    )
    from gh_io import run_gh

_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { isResolved }
  }
}
"""


def list_blocking(payload: dict) -> list[tuple[str, str, str]]:
    """Return `(thread_id, priority, url)` for every open BLOCKING thread."""
    return blocking_threads(payload)


def resolve(payload: dict, thread_id: str, *, mutate: Callable[[str], object]) -> None:
    """Resolve `thread_id`, refusing a thread reported against the current head.

    `mutate(thread_id) -> object` issues the `resolveReviewThread` mutation and
    returns its decoded response; injected so a test can stub the transport
    (§II) and so a `gh` exit 0 is never trusted without re-reading `isResolved`.
    """
    head = head_ref_oid(payload)
    threads = {thread.thread_id: thread for thread in review_threads(payload)}
    thread = threads.get(thread_id)
    if thread is None:
        raise RuntimeError(f"no open review thread {thread_id!r} on this PR")
    if not thread.blocking:
        raise RuntimeError(
            f"review thread {thread_id} is not BLOCKING (priority {thread.priority}) — "
            "only a BLOCKING thread the fixer's correction addressed may be resolved this way"
        )
    if thread.original_commit_oid is None:
        raise RuntimeError(
            f"review thread {thread_id} has no originalCommit.oid — refusing to resolve blind"
        )
    if thread.original_commit_oid == head:
        raise RuntimeError(
            f"review thread {thread_id} was reported against the current head {head} — "
            "nothing has been pushed past the reviewed commit yet"
        )
    response = mutate(thread_id)
    resolved = (
        isinstance(response, dict)
        and isinstance(response.get("data"), dict)
        and isinstance(response["data"].get("resolveReviewThread"), dict)
        and isinstance(response["data"]["resolveReviewThread"].get("thread"), dict)
        and response["data"]["resolveReviewThread"]["thread"].get("isResolved") is True
    )
    if not resolved:
        raise RuntimeError(
            f"resolveReviewThread for {thread_id} did not report isResolved: true — "
            f"treat the thread as still open: {response!r}"
        )


def close_round(
    payload: dict,
    thread_id: str,
    reply: str,
    *,
    head_run: Callable[[str], tuple[int, str] | None],
    mutate: Callable[[str], object],
    rerun: Callable[[int], None],
    post_reply: Callable[[int, str], None],
) -> int:
    """The step after the wait, in one call: resolve, re-run the head's check, reply.

    `head_run(head_sha) -> (run_id, status) | None` finds the `agent-review` run of
    the head; the step refuses until it concluded — the review of the head is in
    then, Codex's or the fallback's the run started when none came. A resolve has
    no event of its own and the required context is that `pull_request` run, so
    `rerun(run_id)` re-executes it on the resolved state; `post_reply(comment_id,
    body)` answers on the thread last — a resolve is never the last write on a
    thread. Returns the run id. The transports are injected (§II).
    """
    if not reply.strip():
        raise RuntimeError("an empty reply — the thread is answered after the resolve, always")
    head = head_ref_oid(payload)
    run = head_run(head)
    if run is None:
        raise RuntimeError(
            f"no `agent-review` run of the head {head} — nothing to re-run; push first"
        )
    run_id, status = run
    if status != "completed":
        raise RuntimeError(
            f"the `agent-review` run {run_id} of the head {head} is still {status} — "
            "`wait_for_pr.py <PR>` first: the review of the head, Codex's or the fallback's, "
            "is in when it concluded"
        )
    threads = {thread.thread_id: thread for thread in review_threads(payload)}
    resolve(payload, thread_id, mutate=mutate)
    rerun(run_id)
    post_reply(threads[thread_id].comment_id, reply)
    return run_id


def _gh_mutate(thread_id: str) -> dict:
    raw = run_gh(["api", "graphql", "-f", f"query={_MUTATION}", "-F", f"threadId={thread_id}"])
    return json.loads(raw)


def _gh_head_run(head: str) -> tuple[int, str] | None:
    """The newest `agent-review` run the `pull_request` event started on `head`."""
    raw = run_gh(
        [
            "run",
            "list",
            "--commit",
            head,
            "--workflow",
            "agent-review.yml",
            "--event",
            "pull_request",
            "--limit",
            "1",
            "--json",
            "databaseId,status",
        ]
    )
    runs = json.loads(raw)
    if not isinstance(runs, list) or not runs:
        return None
    run = runs[0]
    if not isinstance(run, dict) or not isinstance(run.get("databaseId"), int):
        raise RuntimeError(f"`gh run list` returned no run id: {run!r}")
    return int(run["databaseId"]), str(run.get("status", ""))


def _gh_rerun(run_id: int) -> None:
    run_gh(["run", "rerun", str(run_id)])


def _gh_post_reply(repo: str, pr: int) -> Callable[[int, str], None]:
    def post(comment_id: int, body: str) -> None:
        run_gh(
            [
                "api",
                "-X",
                "POST",
                f"repos/{repo}/pulls/{pr}/comments/{comment_id}/replies",
                "-f",
                f"body={body}",
            ]
        )

    return post


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="OWNER/REPO")
    parser.add_argument("--pr", required=True, type=int, metavar="NUMBER")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="print every open BLOCKING thread")
    group.add_argument(
        "--thread",
        metavar="NODE-ID",
        help="resolve this thread, re-run the head's agent-review run, reply (--reply-file)",
    )
    parser.add_argument(
        "--reply-file",
        metavar="PATH",
        help="the reply posted on the thread after the resolve (UTF-8); required with --thread",
    )
    options = parser.parse_args(argv)
    if options.thread and not options.reply_file:
        parser.error("--thread needs --reply-file: the thread is answered after the resolve")
    return options


def main(argv: Sequence[str] | None = None) -> None:
    options = _parse_options(list(sys.argv[1:] if argv is None else argv))
    try:
        payload = fetch_review_threads(options.repo, options.pr)
        if options.list:
            for thread_id, priority, url in list_blocking(payload):
                print(f"{priority}\t{thread_id}\t{url}")
            return
        with open(options.reply_file, encoding="utf-8") as handle:
            reply = handle.read()
        run_id = close_round(
            payload,
            options.thread,
            reply,
            head_run=_gh_head_run,
            mutate=_gh_mutate,
            rerun=_gh_rerun,
            post_reply=_gh_post_reply(options.repo, options.pr),
        )
        print(f"ok: resolved {options.thread}, re-run {run_id}, replied")
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
