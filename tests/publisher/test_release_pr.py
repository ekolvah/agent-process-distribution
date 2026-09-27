"""A release PR is recognised by its diff (ADR 0031)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import release_pr
from scripts.release_pr import release_verdict

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "release-please-config.json").read_text(encoding="utf-8"))
MANIFEST = ".release-please-manifest.json"
PLUGIN = ".claude-plugin/plugin.json"
MARKETPLACE = ".claude-plugin/marketplace.json"
INIT = "skills/agent-process/scripts/init.py"


def _texts(version: str) -> dict[str, str]:
    return {
        MANIFEST: json.dumps({".": version}),
        PLUGIN: json.dumps({"name": "agent-process", "version": version, "hooks": "./hooks.json"}),
        MARKETPLACE: json.dumps({"plugins": [{"name": "agent-process", "version": version}]}),
        INIT: f'import sys\n\nVERSION = "{version}"  # x-release-please-version\n',
    }


BASE = _texts("2.0.0")
HEAD = _texts("2.1.0")
CHANGES = [
    (MARKETPLACE, "modified"),
    (PLUGIN, "modified"),
    (MANIFEST, "modified"),
    ("CHANGELOG.md", "modified"),
    (INIT, "modified"),
]


def _verdict(
    *,
    config: dict | None = CONFIG,
    changes: list[tuple[str, str]] = CHANGES,
    head: dict[str, str] | None = None,
) -> str | None:
    head_text = head if head is not None else HEAD
    return release_verdict(config, changes, BASE, head_text)


def test_release_pr_is_recognised() -> None:
    assert _verdict() is None


def test_other_change_in_a_version_file_is_not_a_release_pr() -> None:
    hooked = dict(HEAD, **{PLUGIN: HEAD[PLUGIN].replace("./hooks.json", "./evil.json")})
    reason = _verdict(head=hooked)
    assert reason is not None
    assert PLUGIN in reason

    edited = dict(HEAD, **{INIT: HEAD[INIT].replace("import sys", "import os")})
    reason = _verdict(head=edited)
    assert reason is not None
    assert INIT in reason


def test_file_outside_the_set_is_not_a_release_pr() -> None:
    script = "skills/agent-process/scripts/start_change.py"
    reason = _verdict(changes=[*CHANGES, (script, "modified")])
    assert reason is not None
    assert script in reason

    reason = _verdict(changes=[*CHANGES, ("release-please-config.json", "modified")])
    assert reason is not None
    assert "release-please-config.json" in reason


def test_version_file_added_or_removed_is_not_a_release_pr() -> None:
    for status in ("added", "removed", "renamed"):
        changes = [(path, status if path == PLUGIN else kind) for path, kind in CHANGES]
        reason = _verdict(changes=changes)
        assert reason is not None
        assert PLUGIN in reason


def test_manifest_unchanged_is_not_a_release_pr() -> None:
    unchanged = dict(BASE)
    reason = _verdict(changes=[(PLUGIN, "modified"), ("CHANGELOG.md", "modified")], head=unchanged)
    assert reason is not None
    assert MANIFEST in reason


def test_no_release_configuration_means_no_release_pr() -> None:
    reason = _verdict(config=None)
    assert reason is not None
    assert "release-please-config.json" in reason


def _serve(monkeypatch: pytest.MonkeyPatch, head: dict[str, str], changes: list) -> None:
    def run_gh(args: list[str]) -> str:
        endpoint = args[-1]
        if "/compare/" in endpoint:
            return json.dumps({"files": [{"filename": p, "status": s} for p, s in changes]})
        if endpoint.endswith("/contents/?ref=BASE"):
            return json.dumps([{"name": "release-please-config.json", "type": "file"}])
        path, ref = endpoint.split("/contents/", 1)[1].split("?ref=")
        if path == "release-please-config.json":
            return json.dumps(CONFIG)
        return (BASE if ref == "BASE" else head)[path]

    monkeypatch.setattr(release_pr, "run_gh", run_gh)


ARGS = ["--repo", "o/r", "--pr", "7", "--base-sha", "BASE", "--head-sha", "HEAD"]


def test_main_publishes_the_verdict(monkeypatch, tmp_path, capsys) -> None:
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))

    _serve(monkeypatch, HEAD, CHANGES)
    release_pr.main(ARGS)
    _serve(monkeypatch, HEAD, [*CHANGES, ("README.md", "modified")])
    release_pr.main(ARGS)

    assert output.read_text(encoding="utf-8").splitlines() == ["release=true", "release=false"]
    out = capsys.readouterr().out
    assert "release PR: 2.1.0" in out
    assert "not a release PR:" in out
    assert "README.md" in out


def test_truncated_compare_is_not_a_release_pr(monkeypatch, capsys) -> None:
    """The compare API lists at most 300 files: a list that long may hide a file outside
    the set, so it is never a release PR."""
    _serve(monkeypatch, HEAD, [*CHANGES, *[(f"docs/{n}.md", "modified") for n in range(295)]])

    release_pr.main(ARGS)

    out = capsys.readouterr().out
    assert "release=false" in out
    assert "300 files" in out


def test_failed_read_fails_the_check(monkeypatch, capsys) -> None:
    def run_gh(args: list[str]) -> str:
        raise RuntimeError("gh api failed: HTTP 502")

    monkeypatch.setattr(release_pr, "run_gh", run_gh)

    with pytest.raises(SystemExit) as exit_info:
        release_pr.main(ARGS)

    assert exit_info.value.code == 2
    assert "HTTP 502" in capsys.readouterr().err
