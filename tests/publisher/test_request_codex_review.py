"""The Codex transport: post the request, read whether a review of the head exists."""

from __future__ import annotations

import inspect
import json
import subprocess
import sys

import pytest

from scripts import request_codex_review

_HEAD = "a" * 40
_REVIEWER = "chatgpt-codex-connector[bot]"


def test_request_command_posts_the_exact_codex_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(request_codex_review, "run_gh", lambda args: calls.append(args) or "")

    request_codex_review.main(["--request", "37"])

    assert calls == [["pr", "comment", "37", "--body", "@codex review"]]


def test_request_command_surfaces_a_github_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_args: list[str]) -> str:
        raise RuntimeError("gh pr comment failed: permission denied")

    monkeypatch.setattr(request_codex_review, "run_gh", fail)

    with pytest.raises(RuntimeError, match="permission denied"):
        request_codex_review.request_review("37")


def _payload(
    *, reviews: list[dict[str, object]] = (), comments: list[dict[str, object]] = ()
) -> dict[str, object]:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "headRefOid": _HEAD,
                    "reviews": {"nodes": list(reviews)},
                    "comments": {"nodes": list(comments)},
                }
            }
        }
    }


def _native_review(oid: str, login: str = _REVIEWER) -> dict[str, object]:
    return {"author": {"login": login}, "commit": {"oid": oid}}


class _FakeTime:
    """A clock the wait reads and a sleep that advances it — no real waiting."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _wait_argv(timeout: str = "60", poll: str = "20") -> list[str]:
    return [
        "--wait",
        "--repo",
        "owner/repo",
        "--pr",
        "37",
        "--head-sha",
        _HEAD,
        "--timeout-seconds",
        timeout,
        "--poll-seconds",
        poll,
    ]


def _serve(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> _FakeTime:
    fake = _FakeTime()
    monkeypatch.setattr(request_codex_review, "run_gh", lambda args: json.dumps(payload))
    monkeypatch.setattr(request_codex_review.time, "monotonic", fake.monotonic)
    monkeypatch.setattr(request_codex_review.time, "sleep", fake.sleep)
    return fake


def test_wait_is_present_for_a_native_review_on_the_head(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = _serve(monkeypatch, _payload(reviews=[_native_review(_HEAD)]))

    request_codex_review.main(_wait_argv())

    assert "present" in capsys.readouterr().out
    assert fake.sleeps == []


def test_wait_polls_to_the_timeout_for_a_review_of_an_older_head(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A review of an older head is not a review of this one: the wait keeps
    polling until the timeout and reports absence with exit 3, not 1 (a crash
    of the script stays distinguishable as exit 2)."""
    fake = _serve(monkeypatch, _payload(reviews=[_native_review("b" * 40)]))

    with pytest.raises(SystemExit) as exit_info:
        request_codex_review.main(_wait_argv(timeout="60", poll="20"))

    assert exit_info.value.code == 3
    assert "absent after" in capsys.readouterr().out
    assert fake.sleeps == [20.0, 20.0, 20.0]


def test_wait_is_present_for_the_clean_comment_naming_the_head(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    comment = {
        "author": {"login": _REVIEWER},
        "body": "Codex Review: Didn't find any major issues. :tada:\n\n"
        f"**Reviewed commit:** `{_HEAD[:10]}`",
    }
    _serve(monkeypatch, _payload(comments=[comment]))

    request_codex_review.main(_wait_argv())

    assert "present" in capsys.readouterr().out


def test_wait_ignores_a_limit_message_and_a_stranger_naming_the_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An error or usage-limit message from the app is no review; a human
    quoting the head is no review either."""
    comments = [
        {
            "author": {"login": _REVIEWER},
            "body": "You have reached your Codex usage limits for code reviews.",
        },
        {"author": {"login": "author"}, "body": f"**Reviewed commit:** `{_HEAD[:10]}`"},
    ]
    _serve(monkeypatch, _payload(comments=comments))

    with pytest.raises(SystemExit) as exit_info:
        request_codex_review.main(_wait_argv(timeout="20", poll="20"))

    assert exit_info.value.code == 3


def test_wait_reads_nothing_but_presence() -> None:
    """ADR 0027: the read is *whether* a Codex review exists, never what it says."""
    source = inspect.getsource(request_codex_review)
    for parser_word in ("severity", "finding", "evidence", "verdict", "outcome"):
        assert parser_word not in source


def test_module_entry_point_runs_the_cli() -> None:
    result = subprocess.run(
        [sys.executable, ".agent-process/scripts/request_codex_review.py", "--help"],
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
    )

    assert result.returncode == 0
    assert "--request" in result.stdout
    assert "--wait" in result.stdout
