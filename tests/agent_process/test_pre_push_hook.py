"""`.agent-process/.githooks/pre-push`: the hook runs `ci_check.py` alone.

Behavioral tests: the hook executes through `bash` in a temporary tree with call-counting
stubs. Text grep is useless here—the original defect was `||` semantics, not line presence.
Local enforcement is supplementary; the ruleset is the final barrier (change
v2-4a-review-protection, design D4).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOK = _REPO_ROOT / ".agent-process" / ".githooks" / "pre-push"


class TestPrePushHook:
    """The hook truly executes: stubs count calls, order, and stderr."""

    _STUB = (
        "#!/usr/bin/env bash\n"
        'printf "%s|%s|GIT_DIR=%s\\n" "$STUB_ID" "$*" "${GIT_DIR-unset}" '
        '>> "$PWD/hook-calls.log"\n'
        'if [ "$1" = "-c" ]; then exit 0; fi\n'
        'name=$(basename "$1")\n'
        'echo "stderr-from-$name" >&2\n'
        'if [ -f "rc-$name" ]; then exit "$(cat "rc-$name")"; fi\n'
        "exit 0\n"
    )

    @staticmethod
    def _stub(path: Path, stub_id: str) -> None:
        """Place an executable interpreter stub identifying itself with `stub_id`."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            TestPrePushHook._STUB.replace("$STUB_ID", stub_id),
            encoding="utf-8",
            newline="\n",
        )
        path.chmod(0o755)

    @staticmethod
    def _bash() -> str:
        """Absolute path to `bash`—the test below must restrict PATH without losing the shell."""
        bash = shutil.which("bash")
        assert bash, "bash недоступен: хук нечем исполнить, гард выродился бы в grep"
        return bash

    @classmethod
    def _run(
        cls, tmp_path: Path, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Execute the real `.githooks/pre-push` in a temporary tree."""
        subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
        return subprocess.run(
            [cls._bash(), _HOOK.as_posix()],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    @staticmethod
    def _gate_calls(tmp_path: Path) -> list[str]:
        """Gate invocations (the interpreter `-c` probe is excluded from the log)."""
        log = tmp_path / "hook-calls.log"
        if not log.exists():
            return []
        return [line for line in log.read_text(encoding="utf-8").splitlines() if ".py" in line]

    def test_push_runs_ci_check_alone(self, tmp_path: Path) -> None:
        """No protection probe: the one recorded gate call is `ci_check.py`."""
        self._stub(tmp_path / ".venv" / "Scripts" / "python", "scripts")
        result = self._run(tmp_path)
        calls = self._gate_calls(tmp_path)
        assert result.returncode == 0, result.stderr
        assert len(calls) == 1, calls
        assert ".agent-process/scripts/ci_check.py" in calls[0]

    def test_clears_repository_local_git_environment(self, tmp_path: Path) -> None:
        self._stub(tmp_path / ".venv" / "Scripts" / "python", "scripts")
        result = self._run(tmp_path, env={**os.environ, "GIT_DIR": str(_REPO_ROOT / ".git")})
        calls = self._gate_calls(tmp_path)

        assert result.returncode == 0, result.stderr
        assert calls, "no gate invocations logged"
        assert all("GIT_DIR=unset" in call for call in calls)

    @pytest.mark.parametrize(
        ("git_function", "diagnostic"),
        [
            ("git() { echo 'git discovery unavailable' >&2; return 1; }\n", "failed"),
            ("git() { return 0; }\n", "returned no names"),
        ],
    )
    def test_git_local_environment_discovery_failure_exits_two(
        self, tmp_path: Path, git_function: str, diagnostic: str
    ) -> None:
        self._stub(tmp_path / ".venv" / "Scripts" / "python", "scripts")
        bash_env = tmp_path / "fail-git.sh"
        bash_env.write_text(
            git_function,
            encoding="utf-8",
            newline="\n",
        )
        env = {**os.environ, "BASH_ENV": bash_env.as_posix()}
        result = self._run(tmp_path, env=env)

        assert result.returncode == 2
        assert f"git rev-parse --local-env-vars {diagnostic}" in result.stderr
        assert not self._gate_calls(tmp_path)

    def test_failing_gate_is_not_rerun_under_the_next_interpreter(self, tmp_path: Path) -> None:
        """A red gate is a verdict, not an interpreter-discovery failure."""
        self._stub(tmp_path / ".venv" / "Scripts" / "python", "scripts")
        self._stub(tmp_path / ".venv" / "bin" / "python", "bin")
        (tmp_path / "rc-ci_check.py").write_text("1", encoding="utf-8")
        result = self._run(tmp_path)
        calls = self._gate_calls(tmp_path)
        assert result.returncode != 0
        assert not any(c.startswith("bin|") for c in calls)
        assert sum("ci_check.py" in c for c in calls) == 1

    def test_gate_exit_code_is_propagated(self, tmp_path: Path) -> None:
        """`2` (tool did not run) and `1` (red) must remain distinct externally."""
        self._stub(tmp_path / ".venv" / "Scripts" / "python", "scripts")
        (tmp_path / "rc-ci_check.py").write_text("2", encoding="utf-8")
        assert self._run(tmp_path).returncode == 2

    def test_gate_stderr_is_not_swallowed(self, tmp_path: Path) -> None:
        """`2>/dev/null` remains only on the interpreter probe, not a gate run."""
        self._stub(tmp_path / ".venv" / "Scripts" / "python", "scripts")
        (tmp_path / "rc-ci_check.py").write_text("1", encoding="utf-8")
        result = self._run(tmp_path)
        assert "stderr-from-ci_check.py" in result.stderr

    def test_hook_has_no_crlf_in_the_working_tree(self) -> None:
        """CRLF in shebang kills the hook entirely—`.gitattributes` keeps it LF-only.

        With `core.autocrlf=true` (Git for Windows default) and no attribute, a fresh clone would receive
        `#!/usr/bin/env bash\\r`, bash would fail with “bad interpreter,” and the pre-push gate would silently
        stop running.
        """
        assert b"\r\n" not in _HOOK.read_bytes()

    def test_missing_interpreter_fails_loudly(self, tmp_path: Path) -> None:
        """No candidate found—visible failure, not a silently skipped gate (§IV)."""
        env = {"PATH": str(Path(self._bash()).parent)}
        result = self._run(tmp_path, env=env)
        assert result.returncode != 0
        assert result.stderr.strip(), "молчаливый отказ хука неотличим от зелёного прогона"
