"""Owner-only task-attribution contract for issue #101."""

from __future__ import annotations

import json
import importlib.util
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "owner_task_attribution", ROOT / "scripts" / "owner_task_attribution.py"
)
assert SPEC is not None and SPEC.loader is not None
attribution = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(attribution)


PROJECT = "ekolvah/agent-process-distribution"
START = datetime(2026, 9, 12, 10, 0, tzinfo=UTC)


class TestTaskIdentity:
    def test_explicit_issue_wins_and_branch_uses_shared_parser(self) -> None:
        assert attribution.resolve_issue(101, "issue-999-other") == "issue-101"
        assert attribution.resolve_issue(None, "issue-101-bug-telemetry") == "issue-101"
        assert attribution.resolve_issue(None, "main") == "unassigned"

    def test_attempt_reuses_repository_and_issue_unless_new_requested(self) -> None:
        records: list[dict[str, str]] = []
        first = attribution.start_attempt(
            records,
            project=PROJECT,
            task_id="issue-101",
            started_at=START,
            uuid_factory=lambda: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )
        reused = attribution.start_attempt(
            records,
            project=PROJECT,
            task_id="issue-101",
            started_at=START + timedelta(hours=1),
            uuid_factory=lambda: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        )
        later = attribution.start_attempt(
            records,
            project=PROJECT,
            task_id="issue-101",
            started_at=START + timedelta(hours=2),
            new_attempt=True,
            uuid_factory=lambda: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        )

        assert reused == first
        assert first["attempt_id"] == "issue-101-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        assert later["attempt_id"] != first["attempt_id"]
        assert len(records) == 2


class TestClaudeLaunch:
    def test_complete_settings_and_metrics_only_endpoint(self) -> None:
        settings = attribution.compose_claude_settings(
            project=PROJECT,
            task_id="issue-101",
            attempt_id="issue-101-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )
        env = settings["env"]
        pairs = dict(item.split("=", 1) for item in env["OTEL_RESOURCE_ATTRIBUTES"].split(","))

        assert pairs == {
            "vcs.repository.name": PROJECT,
            "task_id": "issue-101",
            "attempt_id": "issue-101-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        }
        assert env["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"] == (
            "http://127.0.0.1:4318/v1/metrics"
        )
        assert "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT" not in env
        assert "OTEL_EXPORTER_OTLP_HEADERS" not in env

    @pytest.mark.parametrize("returncode", [0, 17])
    def test_generated_settings_are_removed_after_process_exit(
        self, tmp_path: Path, returncode: int
    ) -> None:
        seen: dict[str, object] = {}

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            settings_path = Path(command[command.index("--settings") + 1])
            seen["command"] = command
            seen["path"] = settings_path
            seen["settings"] = json.loads(settings_path.read_text(encoding="utf-8"))
            return subprocess.CompletedProcess(command, returncode)

        result = attribution.run_claude(
            ["claude", "--model", "sonnet"],
            project=PROJECT,
            task_id="issue-101",
            attempt_id="issue-101-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            state_dir=tmp_path,
            runner=runner,
        )

        assert result == returncode
        assert seen["command"][:3] == ["claude", "--settings", str(seen["path"])]
        assert not Path(seen["path"]).exists()
        assert list(tmp_path.iterdir()) == []


class TestCodexLaunch:
    def test_codec_round_trip_and_command_are_argument_safe(self) -> None:
        attempt = "issue-101-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        encoded = attribution.encode_codex_environment(PROJECT, "issue-101", attempt)

        assert encoded == f"cpt|{PROJECT}|issue-101|{attempt}"
        assert attribution.decode_codex_environment(encoded) == (PROJECT, "issue-101", attempt)
        assert attribution.codex_command(["codex", "--search"], encoded) == [
            "codex",
            "-c",
            f"otel.environment={encoded}",
            "--search",
        ]

    @pytest.mark.parametrize("value", ["", "a|b", "unattributed"])
    def test_codec_rejects_invalid_components(self, value: str) -> None:
        with pytest.raises(ValueError):
            attribution.encode_codex_environment(PROJECT, value, "attempt")

    def test_decoder_preserves_legacy_and_marks_malformed_packed_values(self) -> None:
        assert attribution.decode_codex_environment(PROJECT) is None
        with pytest.raises(ValueError):
            attribution.decode_codex_environment("cpt|only|two")


class FakePullRequests:
    def __init__(self, records: list[dict[str, str | None]]) -> None:
        self.records = records

    def for_project(self, project: str) -> list[dict[str, str | None]]:
        assert project == PROJECT
        return self.records


class TestAttemptLedger:
    def test_outcomes_follow_attempt_windows_and_live_pr_state(self) -> None:
        attempts = [
            {
                "project": PROJECT,
                "task_id": "issue-101",
                "attempt_id": "attempt-a",
                "started_at": START.isoformat(),
            },
            {
                "project": PROJECT,
                "task_id": "issue-101",
                "attempt_id": "attempt-b",
                "started_at": (START + timedelta(days=1)).isoformat(),
            },
            {
                "project": PROJECT,
                "task_id": "issue-102",
                "attempt_id": "attempt-c",
                "started_at": START.isoformat(),
            },
            {
                "project": PROJECT,
                "task_id": "issue-103",
                "attempt_id": "attempt-d",
                "started_at": START.isoformat(),
            },
        ]
        prs = FakePullRequests(
            [
                {
                    "head_ref": "issue-101-second",
                    "created_at": (START + timedelta(days=1, hours=1)).isoformat(),
                    "merged_at": None,
                    "closed_at": None,
                },
                {
                    "head_ref": "issue-102-closed",
                    "created_at": (START + timedelta(hours=1)).isoformat(),
                    "merged_at": None,
                    "closed_at": (START + timedelta(hours=2)).isoformat(),
                },
                {
                    "head_ref": "issue-103-merged",
                    "created_at": (START + timedelta(hours=1)).isoformat(),
                    "merged_at": (START + timedelta(hours=2)).isoformat(),
                    "closed_at": (START + timedelta(hours=2)).isoformat(),
                },
            ]
        )

        assert attribution.resolve_outcomes(attempts, prs) == {
            "attempt-a": "superseded_without_pr",
            "attempt-b": "open",
            "attempt-c": "closed_unmerged",
            "attempt-d": "merged",
        }

    def test_malformed_and_overlapping_pr_windows_fail(self) -> None:
        malformed = [{"project": PROJECT, "task_id": "issue-101"}]
        with pytest.raises(ValueError):
            attribution.resolve_outcomes(malformed, FakePullRequests([]))

        attempts = [
            {
                "project": PROJECT,
                "task_id": "issue-101",
                "attempt_id": "a",
                "started_at": START.isoformat(),
            },
            {
                "project": PROJECT,
                "task_id": "issue-101",
                "attempt_id": "b",
                "started_at": (START + timedelta(days=1)).isoformat(),
            },
        ]
        overlapping = FakePullRequests(
            [
                {
                    "head_ref": "issue-101-reused",
                    "created_at": (START + timedelta(hours=1)).isoformat(),
                    "merged_at": (START + timedelta(days=2)).isoformat(),
                    "closed_at": (START + timedelta(days=2)).isoformat(),
                }
            ]
        )
        with pytest.raises(ValueError, match="overlap"):
            attribution.resolve_outcomes(attempts, overlapping)


class TestHostDoctor:
    def test_accepts_sanitized_transform_and_metrics_route(self) -> None:
        config = "\n".join(attribution.REQUIRED_ALLOY_STATEMENTS)
        result = attribution.check_host(
            config,
            metrics_endpoint="http://127.0.0.1:4318/v1/metrics",
        )
        assert result.ok
        assert result.errors == ()
        assert "password" not in repr(result).lower()
        assert "token" not in repr(result).lower()

    def test_rejects_missing_transform_or_wrong_endpoint(self) -> None:
        result = attribution.check_host("", metrics_endpoint="https://example.invalid/v1/metrics")
        assert not result.ok
        assert any("Alloy" in error for error in result.errors)
        assert any("metrics endpoint" in error for error in result.errors)
