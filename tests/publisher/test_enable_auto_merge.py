"""`enable_auto_merge.py` (change approval-merges, design D1).

One test per scenario of the `review-and-merge` delta; the scenario name is the test name.
The script is loaded inside each test, so a missing script fails its own scenario. The fake
`gh` answers the `reviewDecision` read, records every call and raises `RuntimeError` on the
merge as `run_gh` does when gh refuses.
"""

from __future__ import annotations

import json

import pytest

from tests.publisher.delivery_fakes import load_script

PR = 9
MERGE = ["gh", "pr", "merge", str(PR), "--auto", "--squash"]
REFUSED = "GraphQL: Auto merge is not allowed for this repository (enablePullRequestAutoMerge)"


class FakeGh:
    def __init__(self, decision: str, *, refuse: bool = False) -> None:
        self.decision = decision
        self.refuse = refuse
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str]) -> str:
        self.calls.append(cmd)
        if cmd == ["gh", "pr", "view", str(PR), "--json", "reviewDecision"]:
            return json.dumps({"reviewDecision": self.decision})
        if cmd == MERGE:
            if self.refuse:
                raise RuntimeError(f"`{' '.join(cmd)}` failed (rc=1): {REFUSED}")
            return ""
        raise AssertionError(f"unexpected gh call: {cmd}")


def _run(gh: FakeGh, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    module = load_script("enable_auto_merge")
    with pytest.raises(SystemExit) as exc:
        module.main([str(PR)], gh=gh)
    captured = capsys.readouterr()
    return int(exc.value.code or 0), captured.out + captured.err


def test_approval_required(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh("REVIEW_REQUIRED")
    code, out = _run(gh, capsys)
    assert code == 0, out
    assert gh.calls[-1] == MERGE
    assert "approval merges" in out


@pytest.mark.parametrize("decision", ["", "APPROVED"], ids=["empty", "approved"])
def test_no_approval_required(decision: str, capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh(decision)
    code, out = _run(gh, capsys)
    assert code == 1, out
    assert not any(cmd[:3] == ["gh", "pr", "merge"] for cmd in gh.calls)
    assert "the person merges" in out


def test_auto_merge_refused(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh("REVIEW_REQUIRED", refuse=True)
    code, out = _run(gh, capsys)
    assert code == 2, out
    assert REFUSED in out
