"""The repository's quality declaration (change declare-quality-with-first-tests, issue 249).

`.github/agent-process-quality.json` is the consumer's: the change that adds the first
tests declares its `test` command, and CI and `check_red` read it. The script is imported
inside the tests so that a missing script fails its own scenario.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.publisher.delivery_fakes import load_script

DECLARATION = ".github/agent-process-quality.json"


def _declare(root: Path, text: str) -> None:
    path = root / DECLARATION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _outputs(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_read_declaration(tmp_path: Path) -> None:
    quality = load_script("quality")
    assert quality.read(tmp_path) is None

    _declare(tmp_path, json.dumps({"test": "pytest -q"}))
    found = quality.read(tmp_path)
    assert (found.setup, found.test, found.checks) == ("", "pytest -q", "")

    _declare(tmp_path, json.dumps({"setup": "s", "test": "t", "checks": "c"}))
    found = quality.read(tmp_path)
    assert (found.setup, found.test, found.checks) == ("s", "t", "c")


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "[]",
        json.dumps({"setup": "s"}),
        json.dumps({"test": ""}),
        json.dumps({"test": "   "}),
        json.dumps({"test": 1}),
        json.dumps({"test": "t", "setup": 1}),
        json.dumps({"test": "t", "checks": []}),
        json.dumps({"test": "a\nchecks=[]"}),
    ],
    ids=[
        "not-json",
        "list",
        "test-missing",
        "test-empty",
        "test-blank",
        "test-number",
        "setup-number",
        "checks-list",
        "test-newline",
    ],
)
def test_read_rejects_malformed(tmp_path: Path, text: str) -> None:
    quality = load_script("quality")
    _declare(tmp_path, text)
    with pytest.raises(ValueError, match=r"\.github/agent-process-quality\.json") as exc:
        quality.read(tmp_path)
    # The message names the fault, not only the file.
    assert str(exc.value).replace(DECLARATION, "").strip(" :")


def _github_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, Path]:
    quality = load_script("quality")
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    code = quality.main(["--github-output"])
    return code, capsys.readouterr().out, output


def test_github_output_declared(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _declare(tmp_path, json.dumps({"setup": "s", "test": "t", "checks": "c"}))
    code, _, output = _github_output(monkeypatch, tmp_path, capsys)
    assert code == 0
    assert _outputs(output) == {"setup": "s", "test": "t", "checks": "c"}


def test_github_output_absent_warns(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, output = _github_output(monkeypatch, tmp_path, capsys)
    assert code == 0
    assert out.startswith("::warning::") and DECLARATION in out, out
    assert _outputs(output).get("test", "") == ""


def test_github_output_malformed_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _declare(tmp_path, json.dumps({"test": ""}))
    code, out, _ = _github_output(monkeypatch, tmp_path, capsys)
    assert code == 1
    assert out.startswith("::error::") and DECLARATION in out, out
