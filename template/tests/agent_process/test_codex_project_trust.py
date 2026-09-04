"""Behavioural contract for the read-only Codex project-trust preflight."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_codex_project_trust as trust

_ROOT = (
    r"C:\repo\agent-process-distribution"
    if sys.platform == "win32"
    else "/repo/agent-process-distribution"
)


def _fake_git_toplevel(monkeypatch: pytest.MonkeyPatch, stdout: str, returncode: int = 0) -> None:
    def run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == ["git", "rev-parse", "--show-toplevel"]
        return subprocess.CompletedProcess(args, returncode, stdout, "")

    monkeypatch.setattr(trust.subprocess, "run", run)


def _write_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str) -> Path:
    config = tmp_path / "config.toml"
    config.write_text(text, encoding="utf-8")
    monkeypatch.setattr(trust, "_CONFIG_PATH", config)
    return config


def test_trusted_entry_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_git_toplevel(monkeypatch, _ROOT)
    root = Path(_ROOT).resolve()
    _write_config(
        tmp_path, monkeypatch, f'[projects."{root.as_posix()}"]\ntrust_level = "trusted"\n'
    )

    trust.main()

    assert "ok" in capsys.readouterr().out


def test_no_projects_table_exits_one_with_remediation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_git_toplevel(monkeypatch, _ROOT)
    _write_config(tmp_path, monkeypatch, 'model = "gpt-5.6-terra"\n')

    with pytest.raises(SystemExit, match="1"):
        trust.main()

    output = capsys.readouterr().err
    assert "not marked trusted" in output
    assert "trust_level" in output


def test_entry_present_but_not_trusted_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_git_toplevel(monkeypatch, _ROOT)
    root = Path(_ROOT).resolve()
    _write_config(
        tmp_path, monkeypatch, f'[projects."{root.as_posix()}"]\ntrust_level = "untrusted"\n'
    )

    with pytest.raises(SystemExit, match="1"):
        trust.main()


def test_missing_config_file_exits_one_and_names_the_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_git_toplevel(monkeypatch, _ROOT)
    monkeypatch.setattr(trust, "_CONFIG_PATH", tmp_path / "does-not-exist" / "config.toml")

    with pytest.raises(SystemExit, match="1"):
        trust.main()

    assert "does not exist" in capsys.readouterr().err


def test_malformed_config_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_git_toplevel(monkeypatch, _ROOT)
    _write_config(tmp_path, monkeypatch, "not [ valid toml")

    with pytest.raises(SystemExit, match="2"):
        trust.main()

    assert "cannot read or parse" in capsys.readouterr().err


def test_unresolvable_git_root_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_git_toplevel(monkeypatch, "", returncode=128)
    _write_config(tmp_path, monkeypatch, "")

    with pytest.raises(SystemExit, match="2"):
        trust.main()

    assert "cannot resolve" in capsys.readouterr().err


def test_other_projects_do_not_satisfy_trust(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_git_toplevel(monkeypatch, _ROOT)
    other = Path(
        "/repo/some-other-project" if sys.platform != "win32" else r"C:\repo\some-other-project"
    )
    _write_config(
        tmp_path, monkeypatch, f'[projects."{other.as_posix()}"]\ntrust_level = "trusted"\n'
    )

    with pytest.raises(SystemExit, match="1"):
        trust.main()


def test_documented_script_command_is_invocable_from_a_checkout() -> None:
    completed = subprocess.run(
        [sys.executable, ".agent-process/scripts/check_codex_project_trust.py"],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode in (0, 1), completed.stderr
