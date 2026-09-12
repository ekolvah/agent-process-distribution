"""Owner-only task-attribution contract for issue #101."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "owner_task_attribution", ROOT / "scripts" / "owner_task_attribution.py"
)
assert SPEC is not None and SPEC.loader is not None
attribution = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = attribution
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
    def test_windows_command_resolves_an_executable_shim(self) -> None:
        probes: list[str] = []

        def which(value: str) -> str | None:
            probes.append(value)
            return "C:/npm/claude.cmd" if value == "claude.cmd" else None

        assert attribution.resolve_command(["claude", "-p", "ok"], windows=True, which=which) == [
            "C:/npm/claude.cmd",
            "-p",
            "ok",
        ]
        assert probes == ["claude.exe", "claude.cmd"]

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
        assert env["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"] == ("http://127.0.0.1:4318/v1/metrics")
        # A caller shell without the exporter selection must not turn a measured
        # launch into a silent no-op: the layer switches the metrics route on itself.
        assert env["CLAUDE_CODE_ENABLE_TELEMETRY"] == "1"
        assert env["OTEL_METRICS_EXPORTER"] == "otlp"
        assert env["OTEL_EXPORTER_OTLP_METRICS_PROTOCOL"] == "http/protobuf"
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
    @staticmethod
    def _sanitized_config(
        *,
        receiver_output: str | None = None,
        transform_output: str | None = None,
        statements_block: str = "metric_statements",
        statements_context: str = "datapoint",
    ) -> str:
        receiver_output = receiver_output or "otelcol.processor.filter.codex_cardinality.input"
        transform_output = transform_output or "otelcol.processor.deltatocumulative.codex.input"
        transform_statements = "\n".join(
            statement
            for statement in attribution.REQUIRED_ALLOY_STATEMENTS
            if statement != attribution.CODEX_CARDINALITY_FILTER
        )
        return f"""\
otelcol.receiver.otlp "codex" {{
  output {{ metrics = [{receiver_output}] }}
}}
otelcol.processor.filter "codex_cardinality" {{
  metrics {{ metric = [`{attribution.CODEX_CARDINALITY_FILTER}`] }}
  output {{ metrics = [otelcol.processor.transform.codex_attribution.input] }}
}}
otelcol.processor.transform "codex_attribution" {{
  {statements_block} {{ context = "{statements_context}" statements = [{transform_statements}] }}
  output {{ metrics = [{transform_output}] }}
}}
otelcol.processor.deltatocumulative "codex" {{
  output {{ metrics = [otelcol.processor.batch.codex.input] }}
}}
otelcol.processor.batch "codex" {{
  output {{ metrics = [otelcol.exporter.otlphttp.grafana.input] }}
}}
otelcol.exporter.otlphttp "grafana" {{}}
"""

    def test_accepts_sanitized_transform_and_metrics_route(self) -> None:
        result = attribution.check_host(
            self._sanitized_config(),
            metrics_endpoint="http://127.0.0.1:4318/v1/metrics",
        )
        assert result.ok
        assert result.errors == ()
        assert "password" not in repr(result).lower()
        assert "token" not in repr(result).lower()

    def test_rejects_config_without_codex_cardinality_filter(self) -> None:
        # Without the filter Codex's ~200 histogram names saturate the tenant series
        # limit and every new task-labelled series is silently discarded.
        config = self._sanitized_config().replace(attribution.CODEX_CARDINALITY_FILTER, "false")
        result = attribution.check_host(config, metrics_endpoint="http://127.0.0.1:4318/v1/metrics")
        assert not result.ok
        assert any("cardinality" in error for error in result.errors)
        assert 'IsMatch(name, "^codex' in attribution.CODEX_CARDINALITY_FILTER

    def test_rejects_missing_transform_or_wrong_endpoint(self) -> None:
        result = attribution.check_host("", metrics_endpoint="https://example.invalid/v1/metrics")
        assert not result.ok
        assert any("Alloy" in error for error in result.errors)
        assert any("metrics endpoint" in error for error in result.errors)

    def test_rejects_disconnected_transform_even_when_all_rules_are_present(self) -> None:
        result = attribution.check_host(
            self._sanitized_config(transform_output="otelcol.processor.batch.codex.input"),
            metrics_endpoint="http://127.0.0.1:4318/v1/metrics",
        )

        assert not result.ok
        assert any("pipeline" in error for error in result.errors)

    def test_rejects_processor_bypassing_fanout(self) -> None:
        result = attribution.check_host(
            self._sanitized_config(
                receiver_output=(
                    "otelcol.processor.filter.codex_cardinality.input, "
                    "otelcol.processor.batch.codex.input"
                )
            ),
            metrics_endpoint="http://127.0.0.1:4318/v1/metrics",
        )

        assert not result.ok
        assert any("pipeline" in error for error in result.errors)

    @pytest.mark.parametrize(
        ("block", "context"),
        [("trace_statements", "span"), ("metric_statements", "metric")],
    )
    def test_rejects_rules_outside_the_datapoint_metric_statements(
        self, block: str, context: str
    ) -> None:
        # The same OTTL text under trace_statements or in metric context never
        # touches metric datapoints, so the connected route ships no labels.
        result = attribution.check_host(
            self._sanitized_config(statements_block=block, statements_context=context),
            metrics_endpoint="http://127.0.0.1:4318/v1/metrics",
        )

        assert not result.ok
        assert any("transform" in error for error in result.errors)
