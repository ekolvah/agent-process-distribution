"""``check_red`` of the OpenSpec apply loop (change v2-2d-check-red-test).

``check_red`` is exercised at the ``subprocess.run`` boundary: a fake that records the
command it received, writes the fixture report at the ``--junitxml=`` argument and returns
a ``CompletedProcess``. The fakes cover the configuration; one live test spawns pytest,
because what the run leaves in the working tree is observable only there.

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import load_script


def _fake_pytest(
    monkeypatch: pytest.MonkeyPatch, report_xml: str, *, returncode: int = 1
) -> list[list[str]]:
    """Replace `subprocess.run` of `check_red` with a pytest that writes `report_xml` where
    `--junitxml=` says and exits `returncode`; returns the list the commands are recorded
    into."""
    check_red = load_script("check_red")
    commands: list[list[str]] = []

    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(list(cmd))
        report = next(a for a in cmd if a.startswith("--junitxml="))[len("--junitxml=") :]
        Path(report).write_text(report_xml, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="stopping")

    monkeypatch.setattr(check_red.subprocess, "run", run)
    return commands


QUALITY = ".github/agent-process-quality.json"


def _python_on_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """Put a directory holding an empty `python` alone on `PATH`; return what
    `shutil.which("python")` finds there. Nothing runs it: the runner is faked."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / ("python.exe" if sys.platform == "win32" else "python")
    python.write_text("", encoding="utf-8")
    python.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    found = shutil.which("python")
    assert found is not None and Path(found).parent == bin_dir
    return found


def _root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, declaration: str | None) -> None:
    """Run from `tmp_path`, whose quality declaration is `declaration` (`None`: absent)."""
    monkeypatch.chdir(tmp_path)
    if declaration is not None:
        path = tmp_path / QUALITY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(declaration, encoding="utf-8")


@pytest.mark.parametrize("declaration", [None, '{"test": ""}'], ids=["absent", "malformed"])
def test_refuses_without_quality_declaration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    declaration: str | None,
) -> None:
    """Scenario: No quality command declared — a repository whose tests have no declared
    command gets no verdict: CI would run none of them."""
    check_red = load_script("check_red")
    _root(monkeypatch, tmp_path, declaration)
    commands = _fake_pytest(monkeypatch, "<testsuites/>")
    with pytest.raises(SystemExit) as exc:
        check_red.main(["tests/test_x.py::test_a"])
    assert exc.value.code == 2
    assert QUALITY in capsys.readouterr().err
    assert commands == []


def test_behavioural_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Scenarios: Behavioural change, Runner given, Configuration that cuts the run —
    `check_red` runs `python -m pytest` of the `python` on `PATH`, not of its own interpreter
    (the plugin environment, which has neither pytest nor the consumer's dependencies),
    under its own configuration with its own report path and the node ids, and judges
    RED from that report; no runner argument exists."""
    check_red = load_script("check_red")
    _root(monkeypatch, tmp_path, '{"test": "pytest -q"}')
    python = _python_on_path(monkeypatch, tmp_path)
    node = "tests/publisher/test_x.py::test_a"
    red = (
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>'
    )
    green = (
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_a"/>'
        "</testsuite></testsuites>"
    )

    commands = _fake_pytest(monkeypatch, red)
    check_red.main([node])

    (cmd,) = commands
    assert cmd[:3] == [python, "-m", "pytest"]
    assert "--tb=no" in cmd
    # The run is the script's configuration, not the project's: `--maxfail=0` cancels a
    # fail-fast `-x`/`--maxfail` from `addopts` (pytest's last `maxfail` wins);
    # `-p no:stepwise` makes `--stepwise` a usage error (rc 4, no report → exit 2); an
    # empty `cache_dir` of the script's own leaves `--lf`/`--ff`/`--nf` nothing to replay
    # while the `cache` fixture stays (`-p no:cacheprovider` takes it away). The RED
    # verdict needs every node id run.
    assert "--maxfail=0" in cmd
    assert "no:stepwise" in cmd and cmd[cmd.index("no:stepwise") - 1] == "-p"
    assert "no:cacheprovider" not in cmd
    (report,) = (a for a in cmd if a.startswith("--junitxml="))
    (cache_dir,) = (a for a in cmd if a.startswith("cache_dir="))
    assert cmd[cmd.index(cache_dir) - 1] == "-o"
    assert Path(cache_dir[len("cache_dir=") :]).parent == Path(report[len("--junitxml=") :]).parent
    assert cmd[-1] == node

    _fake_pytest(monkeypatch, green)
    with pytest.raises(SystemExit) as exc:
        check_red.main([node])
    assert exc.value.code == 1

    # No runner argument: `--test` would be an input for a consumer that does not exist.
    with pytest.raises(SystemExit) as exc:
        check_red.main(["--test", "python -m pytest", node])
    assert exc.value.code == 2


def test_no_python_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scenario: No python on PATH — no verdict, the missing `python` named, nothing run: a
    silent fallback to the script's own interpreter would run the tests without the
    consumer's dependencies, unseen."""
    check_red = load_script("check_red")
    _root(monkeypatch, tmp_path, '{"test": "pytest -q"}')
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    commands = _fake_pytest(monkeypatch, "<testsuites/>")
    with pytest.raises(SystemExit) as exc:
        check_red.main(["tests/test_x.py::test_a"])
    assert exc.value.code == 2
    assert "`python`" in capsys.readouterr().err
    assert commands == []


def test_runner_owns_the_selection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The report is the runner's answer to the node ids it received: `check_red` judges
    every testcase in it and re-derives no selection of its own. A node id spelled `./` or
    as an absolute path, or a project whose `rootdir` differs, spells the classname its own
    way; a second interpreter of the node id would drop the test and report "no tests
    collected"."""
    check_red = load_script("check_red")
    _root(monkeypatch, tmp_path, '{"test": "pytest -q"}')
    _fake_pytest(
        monkeypatch,
        '<testsuites><testsuite><testcase classname="tests.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>',
    )
    check_red.main(["sub/tests/test_x.py::test_a"])
    check_red.main(["./tests/test_x.py::test_a"])


def test_run_leaves_the_tree_clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Scenario: Run leaves the tree clean — in a repository with no ignore rule for bytecode,
    a real RED run leaves `git status --porcelain` as it was: no bytecode, no cache, no report
    (`__pycache__` blocks `archive_change` and the merged-worktree cleanup)."""
    check_red = load_script("check_red")
    # An outer setting would make the test pass whatever `check_red` does.
    monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_f.py").write_text(
        "from pkg import f\n\n\ndef test_f():\n    assert f() == 2\n", encoding="utf-8"
    )
    _root(monkeypatch, tmp_path, '{"test": "python -m pytest"}')
    # Committed: an untracked `pkg/` would collapse to `?? pkg/` and hide the bytecode.
    git = ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test"]
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run([*git, "commit", "--quiet", "-m", "init"], cwd=tmp_path, check=True)

    check_red.main(["tests/test_f.py::test_f"])

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert status.stdout == ""


@pytest.mark.parametrize(
    "selection",
    [["tests/test_greet.py::test_greets_by_name"], ["tests/test_greet.py"]],
    ids=["node-id-rc4", "file-path-rc2"],
)
def test_test_of_code_that_does_not_exist_yet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    selection: list[str],
) -> None:
    """Scenario: Test of code that does not exist yet — a test module whose import target is
    missing fails at collection, which pytest ends as an incomplete run (rc 4 on node ids,
    rc 2 on the file path); `check_red` gives no verdict and names the module and the
    `NotImplementedError` stub that reaches a judgeable RED. A live run: the
    rc is pytest's, not a fake's."""
    check_red = load_script("check_red")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_greet.py").write_text(
        "from newpkg.greet import greet\n\n\n"
        'def test_greets_by_name():\n    assert greet("Ann") == "Hello, Ann"\n',
        encoding="utf-8",
    )
    _root(monkeypatch, tmp_path, '{"test": "python -m pytest"}')

    with pytest.raises(SystemExit) as exc:
        check_red.main(selection)

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "test_greet" in err
    assert "NotImplementedError" in err


@pytest.mark.parametrize("returncode", [2, 3, 4])
def test_interrupted_run_is_no_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, returncode: int
) -> None:
    """Scenario: Configuration that cuts the run — pytest's exit code is the signal that the
    run reached the end: 0, 1 and 5 are complete runs; 2 (interrupted: `pytest.exit()` from a
    hook, `--stepwise`, Ctrl-C), 3 (internal error) and 4 (usage error) are not, and the
    report they leave — partial or absent — is no verdict (exit 2), never RED."""
    check_red = load_script("check_red")
    _root(monkeypatch, tmp_path, '{"test": "pytest -q"}')
    red = (
        '<testsuites><testsuite><testcase classname="tests.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>'
    )
    _fake_pytest(monkeypatch, red, returncode=returncode)
    with pytest.raises(SystemExit) as exc:
        check_red.main(["tests/test_x.py::test_a", "tests/test_x.py::test_b"])
    assert exc.value.code == 2

    # 5 (no tests collected) is a complete run: the empty report is judged as such.
    _fake_pytest(monkeypatch, "<testsuites><testsuite/></testsuites>", returncode=5)
    with pytest.raises(SystemExit) as exc:
        check_red.main(["tests/test_x.py::test_a"])
    assert exc.value.code == 1
