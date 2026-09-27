"""The review job's reader: whether its closing comment names the head."""

from __future__ import annotations

import inspect
import json
import subprocess
import sys

import pytest

from scripts import head_review

_HEAD = "a" * 40
_CODEX = "chatgpt-codex-connector[bot]"
_JOB = "github-actions[bot]"


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


def _native_review(oid: str, login: str = _CODEX) -> dict[str, object]:
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


def _closing(head: str, login: str = _JOB) -> dict[str, object]:
    return {"author": {"login": login}, "body": f"No findings. Reviewed head SHA: {head}"}


def _serve(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> _FakeTime:
    fake = _FakeTime()
    monkeypatch.setattr(head_review, "run_gh", lambda args: json.dumps(payload))
    monkeypatch.setattr(head_review.time, "monotonic", fake.monotonic)
    monkeypatch.setattr(head_review.time, "sleep", fake.sleep)
    return fake


def test_wait_polls_to_the_timeout_for_a_review_of_an_older_head(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A review of an older head is not a review of this one: the wait keeps
    polling until the timeout and reports absence with exit 3, not 1 (a crash
    of the script stays distinguishable as exit 2)."""
    fake = _serve(monkeypatch, _payload(comments=[_closing("b" * 40)]))

    with pytest.raises(SystemExit) as exit_info:
        head_review.main(_wait_argv(timeout="60", poll="20"))

    assert exit_info.value.code == 3
    assert "absent after" in capsys.readouterr().out
    assert fake.sleeps == [20.0, 20.0, 20.0]


def test_presence_is_only_the_review_jobs_closing_comment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: New head — only the closing comment of the review job naming the head is
    its review; a Codex review, a Codex clean comment and a stranger's quote are none."""
    codex_clean = {
        "author": {"login": _CODEX},
        "body": f"Codex Review: Didn't find any major issues.\n\n**Reviewed commit:** `{_HEAD[:10]}`",
    }
    for absent in (
        _payload(reviews=[_native_review(_HEAD)]),
        _payload(comments=[codex_clean]),
        _payload(comments=[_closing(_HEAD, login="author")]),
        _payload(comments=[_closing("b" * 40)]),
    ):
        _serve(monkeypatch, absent)
        with pytest.raises(SystemExit) as exit_info:
            head_review.main(_wait_argv(timeout="0"))
        assert exit_info.value.code == 3

    _serve(monkeypatch, _payload(comments=[_closing(_HEAD)]))
    head_review.main(_wait_argv(timeout="0"))
    assert "present" in capsys.readouterr().out


def test_rerun_reads_the_closing_comment_not_inline_nodes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenarios: Re-run on a reviewed head, Re-run on an interrupted review — the job
    publishes finding by finding, each a review node under its login, and closes with one
    comment naming the head. Nodes without that comment are an interrupted review
    (issue 139); with it the re-run returns without a second review."""
    interrupted = _native_review(_HEAD, login=_JOB)

    fake = _serve(monkeypatch, _payload(reviews=[interrupted]))
    with pytest.raises(SystemExit) as exit_info:
        head_review.main(_wait_argv(timeout="0"))
    assert exit_info.value.code == 3

    fake = _serve(monkeypatch, _payload(reviews=[interrupted], comments=[_closing(_HEAD)]))
    head_review.main(_wait_argv())
    assert "present" in capsys.readouterr().out
    assert fake.sleeps == []


def test_reviewer_flag_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    """The flag is refused by the parser, not by a failing read: the served head has a
    closing comment, so any exit other than argparse's would be a presence."""
    _serve(monkeypatch, _payload(comments=[_closing(_HEAD)]))
    with pytest.raises(SystemExit) as exit_info:
        head_review.main([*_wait_argv(), "--reviewer", "github-actions"])

    assert exit_info.value.code == 2


def test_wait_reads_nothing_but_presence() -> None:
    """ADR 0027: the read is *whether* a review exists, never what it says."""
    source = inspect.getsource(head_review)
    for parser_word in ("severity", "finding", "evidence", "verdict", "outcome"):
        assert parser_word not in source


def test_module_entry_point_runs_the_cli() -> None:
    result = subprocess.run(
        [sys.executable, ".agent-process/scripts/head_review.py", "--help"],
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
    )

    assert result.returncode == 0
    assert "--request" not in result.stdout
    assert "--wait" in result.stdout
