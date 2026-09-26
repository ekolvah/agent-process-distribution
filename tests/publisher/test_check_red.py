"""``check_red`` of the OpenSpec apply loop (change v2-2d-check-red-test).

``check_red`` is exercised at the ``subprocess.run`` boundary: a fake that records the
command it received, writes the fixture report at the ``--junitxml=`` argument and returns
a ``CompletedProcess``. pytest itself is not spawned in the suite; the delivery of the
change runs it live.

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

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


def test_behavioural_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenarios: Behavioural change, Runner given, Configuration that cuts the run —
    `check_red` runs `python -m pytest` of its own interpreter under its own configuration
    with its own report path and the node ids, and judges RED from that report; no runner
    argument exists."""
    check_red = load_script("check_red")
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
    assert cmd[:3] == [sys.executable, "-m", "pytest"]
    assert "--tb=no" in cmd
    # The run is the script's configuration, not the project's: `--maxfail=0` cancels a
    # fail-fast `-x`/`--maxfail` from `addopts` (pytest's last `maxfail` wins);
    # `-p no:stepwise` makes `--stepwise` a usage error (rc 4, no report → exit 2); an
    # empty `cache_dir` of the script's own leaves `--lf`/`--ff`/`--nf` nothing to replay
    # while the `cache` fixture stays (`-p no:cacheprovider` took it away — PR 145,
    # round 9). The RED verdict needs every node id run (rounds 6–9).
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

    # No runner argument: `--test` was an input for a consumer that does not exist
    # (issue 112), and its failure modes cost three review rounds (PR 145).
    with pytest.raises(SystemExit) as exc:
        check_red.main(["--test", "python -m pytest", node])
    assert exc.value.code == 2


def test_runner_owns_the_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """The report is the runner's answer to the node ids it received: `check_red` judges
    every testcase in it and re-derives no selection of its own. A node id spelled `./` or
    as an absolute path, or a project whose `rootdir` differs, spells the classname its own
    way; a second interpreter of the node id would drop the test and report "no tests
    collected" (PR 145)."""
    check_red = load_script("check_red")
    _fake_pytest(
        monkeypatch,
        '<testsuites><testsuite><testcase classname="tests.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>',
    )
    check_red.main(["sub/tests/test_x.py::test_a"])
    check_red.main(["./tests/test_x.py::test_a"])


@pytest.mark.parametrize("returncode", [2, 3, 4])
def test_interrupted_run_is_no_verdict(monkeypatch: pytest.MonkeyPatch, returncode: int) -> None:
    """Scenario: Configuration that cuts the run — pytest's exit code is the signal that the
    run reached the end: 0, 1 and 5 are complete runs; 2 (interrupted: `pytest.exit()` from a
    hook, `--stepwise`, Ctrl-C), 3 (internal error) and 4 (usage error) are not, and the
    report they leave — partial or absent — is no verdict (exit 2), never RED (PR 145,
    round 9)."""
    check_red = load_script("check_red")
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
