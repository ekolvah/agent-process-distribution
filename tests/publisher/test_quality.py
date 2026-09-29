"""The repository's quality declaration (change declare-quality-with-first-tests, issue 249).

`.github/agent-process-quality.json` is the consumer's: the change that adds the first
tests declares its `test` command, and CI and `check_red` read it. The script is imported
inside the tests so that a missing script fails its own scenario.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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


# --- the pre-push hook (change consumer-pre-push-hook, issue 188) ------------------------

ROOT = Path(__file__).resolve().parents[2]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, encoding="utf-8")


def _pushed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, declaration: dict | None) -> Path:
    """A checkout being pushed, the hook's working directory (pre-commit runs from the root)."""
    _git(tmp_path, "init", "-q")
    if declaration is not None:
        _declare(tmp_path, json.dumps(declaration))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_hook_exits_with_test_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Declared test fails — the test runs once, without `setup` or `checks`."""
    quality = load_script("quality")
    root = _pushed(
        monkeypatch,
        tmp_path,
        {
            "setup": "echo setup >> setup.txt",
            "test": "echo run >> runs.txt; exit 3",
            "checks": "echo checks >> checks.txt",
        },
    )
    assert quality.hook() == 3, capfd.readouterr()
    assert (root / "runs.txt").read_text(encoding="utf-8").splitlines() == ["run"]
    assert not (root / "setup.txt").exists() and not (root / "checks.txt").exists()
    _declare(root, json.dumps({"test": "exit 0"}))
    assert quality.hook() == 0


def test_hook_without_declaration_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: No declaration."""
    quality = load_script("quality")
    _pushed(monkeypatch, tmp_path, None)
    assert quality.hook() == 0
    err = capfd.readouterr().err
    assert DECLARATION in err and "no quality command" in err, err


def test_hook_malformed_declaration_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    quality = load_script("quality")
    _pushed(monkeypatch, tmp_path, {"test": 1})
    assert quality.hook() == 1
    err = capfd.readouterr().err
    assert DECLARATION in err and "`test` is not a string" in err, err


def test_hook_hides_local_git_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Scenario: Push from a linked worktree — git hands the hook `GIT_DIR`."""
    quality = load_script("quality")
    root = _pushed(
        monkeypatch,
        tmp_path,
        {"test": 'echo "${GIT_DIR-unset} ${GIT_INDEX_FILE-unset}" > seen.txt'},
    )
    monkeypatch.setenv("GIT_DIR", str(root / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(root / ".git" / "index"))
    assert quality.hook() == 0
    assert (root / "seen.txt").read_text(encoding="utf-8").strip() == "unset unset"


PREFIX_PROBE = (
    "import os, sys; "
    "open('seen.txt', 'w').write(sys.prefix + chr(10) + os.environ.get('VIRTUAL_ENV', 'unset'))"
)


def test_hook_keeps_the_pushers_venv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Scenario: This repository's push — `quality.py --hook` runs where pre-commit applied no
    env patch, so the interpreter and venv it runs in are the pusher's own (design D4)."""
    quality = load_script("quality")
    root = _pushed(monkeypatch, tmp_path, {"test": f'python -c "{PREFIX_PROBE}"'})
    monkeypatch.setenv("VIRTUAL_ENV", sys.prefix)
    monkeypatch.setenv(
        "PATH", os.pathsep.join([str(Path(sys.executable).parent), os.environ["PATH"]])
    )
    assert quality.hook(hook_env=False) == 0
    prefix, venv = (root / "seen.txt").read_text(encoding="utf-8").splitlines()
    assert Path(prefix).resolve() == Path(sys.prefix).resolve()
    assert venv == sys.prefix


@pytest.mark.parametrize("name", ["BASH", "GIT"], ids=["no-bash", "no-git"])
def test_hook_faults_exit_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    name: str,
) -> None:
    quality = load_script("quality")
    root = _pushed(monkeypatch, tmp_path, {"test": "echo ran > ran.txt"})
    monkeypatch.setattr(quality, name, "agent-process-missing-executable")
    assert quality.hook() == 2
    assert "agent-process-missing-executable" in capfd.readouterr().err
    assert not (root / "ran.txt").exists()


def test_hook_repository_runs_at_pre_push(tmp_path: Path) -> None:
    """Scenarios: Consumer render, Declared test runs python — pre-commit installs this
    repository as a hook repository and runs `quality` at `pre-push`; the declared `python` is
    the pusher's, not the hook env pre-commit built (design D1, D4, D5). Needs the network."""
    probe = "import sys; print('prefix=' + sys.prefix)"
    _git(tmp_path, "init", "-q")
    _declare(tmp_path, json.dumps({"test": f'python -c "{probe}"; exit 7'}))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "declare")
    python = shutil.which("python")
    assert python, "python is not on PATH"
    expected = subprocess.run(
        [python, "-c", "import sys; print(sys.prefix)"],
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pre_commit",
            "try-repo",
            str(ROOT),
            "quality",
            "--hook-stage",
            "pre-push",
            "--all-files",
            "--verbose",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    out = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0, out
    assert f"prefix={expected}" in out, out
