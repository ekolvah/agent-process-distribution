"""Tests for `.agent-process/scripts/task_session.py` — the task identity launcher.

The launcher adds one `--settings` JSON layer to a Claude Code command: the project's
`OTEL_RESOURCE_ATTRIBUTES` plus `task_id`/`attempt_id` and a per-launch `service.instance.id`,
and the traces route to the local Alloy receiver. The runner is injected, so no test starts Claude.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from scripts.task_session import compose_attributes, main

_PROJECT_VALUE = "vcs.repository.name=o/r,vcs.repository.url.full=https://github.com/o/r"
_TRACES_ENV = {
    "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
    "OTEL_TRACES_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://127.0.0.1:4318/v1/traces",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/protobuf",
}
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"


class _Recorder:
    def __init__(self, code: int = 0) -> None:
        self.calls: list[list[str]] = []
        self.code = code

    def __call__(self, command: list[str]) -> int:
        self.calls.append(command)
        return self.code


def _repo(tmp_path: Path, settings: object | None) -> Path:
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    if settings is not None:
        (tmp_path / ".claude").mkdir()
        text = settings if isinstance(settings, str) else json.dumps(settings)
        (tmp_path / ".claude" / "settings.json").write_text(text, encoding="utf-8")
    return tmp_path


def _exit_code(argv: list[str], runner: _Recorder) -> int:
    try:
        return main(argv, runner)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(_repo(tmp_path, {"env": {"OTEL_RESOURCE_ATTRIBUTES": _PROJECT_VALUE}}))
    return tmp_path


class TestComposeAttributes:
    def test_appends_task_and_attempt_to_project_value(self) -> None:
        assert (
            compose_attributes(_PROJECT_VALUE, 101, 2, "i-1")
            == f"{_PROJECT_VALUE},task_id=issue-101,attempt_id=2,service.instance.id=i-1"
        )

    @pytest.mark.parametrize("key", ["task_id", "attempt_id", "service.instance.id"])
    def test_rejects_project_value_naming_identity(self, key: str) -> None:
        with pytest.raises(ValueError, match=key):
            compose_attributes(f"{_PROJECT_VALUE},{key}=x", 101, 1, "i-1")


class TestArguments:
    @pytest.mark.parametrize(
        "argv",
        [
            ["--issue", "0", "--", "claude"],
            ["--issue", "-3", "--", "claude"],
            ["--issue", "abc", "--", "claude"],
            ["--issue", "101", "--attempt", "0", "--", "claude"],
            ["--issue", "101", "--attempt", "1.5", "--", "claude"],
            ["--issue", "101", "--"],
        ],
    )
    def test_bad_arguments_exit_2_without_launch(
        self, project: Path, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        runner = _Recorder()
        assert _exit_code(argv, runner) == 2
        assert capsys.readouterr().err.strip()
        assert runner.calls == []

    @pytest.mark.parametrize(
        ("settings", "cause"),
        [
            (None, "settings.json"),
            ({"env": {}}, "OTEL_RESOURCE_ATTRIBUTES"),
            ("{", "not valid JSON"),
            ([], "OTEL_RESOURCE_ATTRIBUTES"),
            ({"env": []}, "OTEL_RESOURCE_ATTRIBUTES"),
            ({"env": {"OTEL_RESOURCE_ATTRIBUTES": 5}}, "OTEL_RESOURCE_ATTRIBUTES"),
            ({"env": {"OTEL_RESOURCE_ATTRIBUTES": f"{_PROJECT_VALUE},task_id=x"}}, "task_id"),
        ],
    )
    def test_project_settings_problems_exit_2_naming_cause(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        settings: object | None,
        cause: str,
    ) -> None:
        monkeypatch.chdir(_repo(tmp_path, settings))
        runner = _Recorder()
        assert _exit_code(["--issue", "101", "--", "claude"], runner) == 2
        assert cause in capsys.readouterr().err
        assert runner.calls == []


class TestLaunch:
    def test_inserts_one_settings_layer_after_the_executable(self, project: Path) -> None:
        runner = _Recorder()
        main(["--issue", "101", "--attempt", "3", "--", "claude", "--model", "opus"], runner)
        [command] = runner.calls
        assert command[:2] == ["claude", "--settings"]
        assert command[3:] == ["--model", "opus"]
        env = json.loads(command[2])["env"]
        assert re.fullmatch(
            re.escape(f"{_PROJECT_VALUE},task_id=issue-101,attempt_id=3,service.instance.id=")
            + _UUID,
            env.pop("OTEL_RESOURCE_ATTRIBUTES"),
        )
        assert env == _TRACES_ENV

    def test_each_launch_gets_its_own_instance(self, project: Path) -> None:
        # A resumed session is a new process whose cumulative counters restart from zero; a
        # shared series would hide the earlier process's tokens behind the reset.
        runner = _Recorder()
        main(["--issue", "7", "--", "claude"], runner)
        main(["--issue", "7", "--", "claude"], runner)
        first, second = (json.loads(c[2])["env"]["OTEL_RESOURCE_ATTRIBUTES"] for c in runner.calls)
        assert first != second

    def test_attempt_defaults_to_1(self, project: Path) -> None:
        runner = _Recorder()
        main(["--issue", "7", "--", "claude"], runner)
        env = json.loads(runner.calls[0][2])["env"]
        assert ",task_id=issue-7,attempt_id=1," in env["OTEL_RESOURCE_ATTRIBUTES"]

    def test_returns_the_command_exit_code(self, project: Path) -> None:
        assert main(["--issue", "7", "--", "claude"], _Recorder(code=5)) == 5
