#!/usr/bin/env python3
"""Launch owner-local agents with task telemetry attribution.

This is deliberately publisher-root-only. It describes the owner's measurement
host; it is not part of the agent-process payload rendered into adopters.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, cast

_ROOT = Path(__file__).resolve().parents[1]
_PROCESS_ROOT = _ROOT / ".agent-process"
if str(_PROCESS_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROCESS_ROOT))

from scripts.open_pr import ISSUE_BRANCH_RE  # type: ignore[import-not-found]  # noqa: E402

METRICS_ENDPOINT = "http://127.0.0.1:4318/v1/metrics"
STATE_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / (
    "agent-process/telemetry"
)
LEDGER_PATH = STATE_ROOT / "attempts.jsonl"
ALLOY_CONFIG_PATH = Path.home() / ".config" / "alloy" / "config.alloy"
_PACKED_PATTERN = r"^cpt[|][^|]+[|][^|]+[|][^|]+$"
_PACKED_PREFIX = "cpt|"
_REQUIRED_FIELDS = ("project", "task_id", "attempt_id", "started_at")

# Codex exports ~200 metric names, mostly histograms; one app-server session put
# ~14 800 series into the tenant and pinned it at max_global_series_per_user, after
# which every new task-labelled series was silently discarded. Only the turn-level
# metrics the measurement reads survive; Claude names are untouched.
CODEX_CARDINALITY_FILTER = (
    'HasPrefix(name, "codex") and not IsMatch(name, "^codex[._](turn[._]token_usage'
    '|turn[._]e2e_duration_ms|conversation[._]turn_count|process[._]start)$")'
)

REQUIRED_ALLOY_STATEMENTS = (
    CODEX_CARDINALITY_FILTER,
    'set(attributes["vcs.repository.name"], resource.attributes["vcs.repository.name"]) '
    'where resource.attributes["vcs.repository.name"] != nil',
    'set(attributes["task_id"], resource.attributes["task_id"]) '
    'where resource.attributes["task_id"] != nil',
    'set(attributes["attempt_id"], resource.attributes["attempt_id"]) '
    'where resource.attributes["attempt_id"] != nil',
    'set(attributes["vcs.repository.name"], Split(resource.attributes["env"], "|")[1]) '
    f'where IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}")',
    'set(attributes["task_id"], Split(resource.attributes["env"], "|")[2]) '
    f'where IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}")',
    'set(attributes["attempt_id"], Split(resource.attributes["env"], "|")[3]) '
    f'where IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}")',
    'set(attributes["vcs.repository.name"], resource.attributes["env"]) '
    'where resource.attributes["env"] != nil and '
    f'not HasPrefix(resource.attributes["env"], "{_PACKED_PREFIX}")',
    'set(attributes["vcs.repository.name"], "unattributed") '
    f'where resource.attributes["env"] != nil and HasPrefix(resource.attributes["env"], '
    f'"{_PACKED_PREFIX}") and not IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}")',
    'set(attributes["task_id"], "unassigned") where '
    'resource.attributes["task_id"] == nil and (resource.attributes["env"] == nil or '
    f'not IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}"))',
    'set(attributes["attempt_id"], "unassigned") where '
    'resource.attributes["attempt_id"] == nil and (resource.attributes["env"] == nil or '
    f'not IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}"))',
    'set(attributes["attribution_error"], "malformed") '
    f'where resource.attributes["env"] != nil and HasPrefix(resource.attributes["env"], '
    f'"{_PACKED_PREFIX}") and not IsMatch(resource.attributes["env"], "{_PACKED_PATTERN}")',
)


def _alloy_component_body(config: str, component: str, label: str) -> str | None:
    """Return one active Alloy component body, excluding line comments."""
    uncommented = re.sub(r"(?m)//.*$", "", config)
    match = re.search(
        rf'^\s*{re.escape(component)}\s+"{re.escape(label)}"\s*\{{',
        uncommented,
        flags=re.MULTILINE,
    )
    if match is None:
        return None
    depth = 1
    for index in range(match.end(), len(uncommented)):
        if uncommented[index] == "{":
            depth += 1
        elif uncommented[index] == "}":
            depth -= 1
            if depth == 0:
                return uncommented[match.end() : index]
    return None


def _has_active_attribution_pipeline(config: str) -> bool:
    """Confirm the owner attribution processors sit on the receiver-to-exporter path."""
    receiver = _alloy_component_body(config, "otelcol.receiver.otlp", "codex")
    cardinality = _alloy_component_body(config, "otelcol.processor.filter", "codex_cardinality")
    transform = _alloy_component_body(config, "otelcol.processor.transform", "codex_attribution")
    delta = _alloy_component_body(config, "otelcol.processor.deltatocumulative", "codex")
    batch = _alloy_component_body(config, "otelcol.processor.batch", "codex")
    exporter = _alloy_component_body(config, "otelcol.exporter.otlphttp", "grafana")
    components = (receiver, cardinality, transform, delta, batch, exporter)
    if any(body is None for body in components):
        return False
    assert receiver is not None and cardinality is not None and transform is not None
    assert delta is not None and batch is not None
    transform_rules = REQUIRED_ALLOY_STATEMENTS[1:]
    return (
        CODEX_CARDINALITY_FILTER in cardinality
        and all(statement in transform for statement in transform_rules)
        and "otelcol.processor.filter.codex_cardinality.input" in receiver
        and "otelcol.processor.transform.codex_attribution.input" in cardinality
        and "otelcol.processor.deltatocumulative.codex.input" in transform
        and "otelcol.processor.batch.codex.input" in delta
        and "otelcol.exporter.otlphttp.grafana.input" in batch
    )


class PullRequestSource(Protocol):
    """External boundary used by attempt outcome resolution."""

    def for_project(self, project: str) -> list[dict[str, str | None]]: ...


@dataclass(frozen=True)
class HostCheck:
    ok: bool
    errors: tuple[str, ...]


def resolve_issue(explicit_issue: int | None, branch: str) -> str:
    """Resolve the stable task name, reusing the process branch parser."""
    if explicit_issue is not None:
        if explicit_issue <= 0:
            raise ValueError("issue number must be positive")
        return f"issue-{explicit_issue}"
    match = ISSUE_BRANCH_RE.match(branch.strip())
    return f"issue-{match.group(1)}" if match else "unassigned"


def _aware_datetime(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"invalid {field}: timezone is required")
    return parsed


def _validate_record(record: dict[str, Any]) -> None:
    missing = [field for field in _REQUIRED_FIELDS if not isinstance(record.get(field), str)]
    if missing:
        raise ValueError(f"malformed attempt record: missing {', '.join(missing)}")
    _aware_datetime(cast("str", record["started_at"]), field="started_at")


def start_attempt(
    records: list[dict[str, str]],
    *,
    project: str,
    task_id: str,
    started_at: datetime,
    new_attempt: bool = False,
    carrier: str = "unknown",
    uuid_factory: Callable[[], object] = uuid.uuid4,
) -> dict[str, str]:
    """Reuse the latest repository+task attempt or append a new start."""
    if not project or not task_id:
        raise ValueError("project and task_id are required")
    if started_at.tzinfo is None:
        raise ValueError("started_at must be timezone-aware")
    for record in records:
        _validate_record(record)
    matching = [
        record
        for record in records
        if record["project"] == project and record["task_id"] == task_id
    ]
    if matching and not new_attempt:
        return max(matching, key=lambda row: _aware_datetime(row["started_at"], field="started_at"))

    attempt_uuid = str(uuid_factory())
    if not attempt_uuid or "|" in attempt_uuid:
        raise ValueError("uuid_factory returned an invalid attempt component")
    record = {
        "project": project,
        "task_id": task_id,
        "attempt_id": f"{task_id}-{attempt_uuid}",
        "started_at": started_at.isoformat(),
        "carrier": carrier,
    }
    records.append(record)
    return record


def _validate_attribute(value: str, *, name: str, forbidden: str) -> None:
    if not value or any(char in value for char in forbidden):
        raise ValueError(f"{name} is empty or contains a reserved delimiter")


def _validate_task_attempt(task_id: str, attempt_id: str) -> None:
    if task_id == "unassigned":
        if attempt_id != "unassigned":
            raise ValueError("an unassigned task must have an unassigned attempt")
        return
    if re.fullmatch(r"issue-[1-9][0-9]*", task_id) is None:
        raise ValueError("task_id must be issue-N or unassigned")
    prefix = f"{task_id}-"
    if not attempt_id.startswith(prefix) or not attempt_id.removeprefix(prefix):
        raise ValueError("attempt_id must belong to task_id")


def compose_claude_settings(
    *, project: str, task_id: str, attempt_id: str
) -> dict[str, dict[str, str]]:
    """Build one complete settings layer; partial resource values are forbidden."""
    for name, value in (("project", project), ("task_id", task_id), ("attempt_id", attempt_id)):
        _validate_attribute(value, name=name, forbidden=",=")
    _validate_task_attempt(task_id, attempt_id)
    attributes = ",".join(
        (
            f"vcs.repository.name={project}",
            f"task_id={task_id}",
            f"attempt_id={attempt_id}",
        )
    )
    # The layer selects the metrics exporter itself: a shell without the owner's
    # OTEL_* variables would otherwise run Claude with zero metric readers and the
    # measured launch would export nothing without any error. Logs keep the
    # caller's direct route and headers.
    return {
        "env": {
            "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
            "OTEL_METRICS_EXPORTER": "otlp",
            "OTEL_EXPORTER_OTLP_METRICS_PROTOCOL": "http/protobuf",
            "OTEL_RESOURCE_ATTRIBUTES": attributes,
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": METRICS_ENDPOINT,
        }
    }


def _claude_command(command: Sequence[str], settings_path: Path) -> list[str]:
    if not command:
        raise ValueError("agent command is required")
    if "--settings" in command:
        raise ValueError("Claude command already contains --settings")
    return [command[0], "--settings", str(settings_path), *command[1:]]


def resolve_command(
    command: Sequence[str],
    *,
    windows: bool = sys.platform == "win32",
    which: Callable[[str], str | None] = shutil.which,
) -> list[str]:
    """Resolve Windows npm shims before recording an attempt start."""
    if not command:
        raise ValueError("agent command is required")
    executable = command[0]
    candidates = (
        [executable]
        if not windows or Path(executable).suffix
        else [f"{executable}{suffix}" for suffix in (".exe", ".cmd", ".bat", ".com")]
    )
    resolved = next((path for candidate in candidates if (path := which(candidate))), None)
    if resolved is None:
        raise FileNotFoundError(f"agent executable not found: {executable}")
    return [resolved, *command[1:]]


def run_claude(
    command: Sequence[str],
    *,
    project: str,
    task_id: str,
    attempt_id: str,
    state_dir: Path = STATE_ROOT,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> int:
    """Run Claude with an explicit temporary settings layer and always remove it."""
    state_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        prefix="claude-attribution-",
        dir=state_dir,
        delete=False,
    )
    settings_path = Path(handle.name)
    try:
        with handle:
            json.dump(
                compose_claude_settings(
                    project=project,
                    task_id=task_id,
                    attempt_id=attempt_id,
                ),
                handle,
                indent=2,
            )
            handle.write("\n")
        completed = runner(_claude_command(command, settings_path), check=False)
        return completed.returncode
    finally:
        settings_path.unlink(missing_ok=True)


def encode_codex_environment(project: str, task_id: str, attempt_id: str) -> str:
    for name, value in (("project", project), ("task_id", task_id), ("attempt_id", attempt_id)):
        _validate_attribute(value, name=name, forbidden="|")
    _validate_task_attempt(task_id, attempt_id)
    return f"{_PACKED_PREFIX}{project}|{task_id}|{attempt_id}"


def decode_codex_environment(value: str) -> tuple[str, str, str] | None:
    """Decode the private packed form; legacy project-only values return None."""
    if not value.startswith(_PACKED_PREFIX):
        return None
    if not re.fullmatch(_PACKED_PATTERN, value):
        raise ValueError("malformed packed Codex environment")
    _, project, task_id, attempt_id = value.split("|")
    return project, task_id, attempt_id


def codex_command(command: Sequence[str], environment: str) -> list[str]:
    if not command:
        raise ValueError("agent command is required")
    decode_codex_environment(environment)
    return [command[0], "-c", f"otel.environment={environment}", *command[1:]]


def _pr_issue(head_ref: str) -> str | None:
    match = ISSUE_BRANCH_RE.match(head_ref)
    return f"issue-{match.group(1)}" if match else None


def resolve_outcomes(attempts: list[dict[str, str]], source: PullRequestSource) -> dict[str, str]:
    """Resolve each attempt from its start window and live PR evidence."""
    seen_ids: set[str] = set()
    grouped: dict[tuple[str, str], list[tuple[datetime, dict[str, str]]]] = {}
    for record in attempts:
        _validate_record(record)
        attempt_id = record["attempt_id"]
        if attempt_id in seen_ids:
            raise ValueError(f"malformed attempt ledger: duplicate {attempt_id}")
        seen_ids.add(attempt_id)
        started = _aware_datetime(record["started_at"], field="started_at")
        grouped.setdefault((record["project"], record["task_id"]), []).append((started, record))

    results: dict[str, str] = {}
    prs_by_project: dict[str, list[dict[str, str | None]]] = {}
    for (project, task_id), rows in grouped.items():
        rows.sort(key=lambda item: item[0])
        if any(rows[index][0] == rows[index - 1][0] for index in range(1, len(rows))):
            raise ValueError(f"overlap: attempts for {project} {task_id} share a start")
        project_prs = prs_by_project.setdefault(project, source.for_project(project))
        task_prs = [pr for pr in project_prs if _pr_issue(str(pr.get("head_ref") or "")) == task_id]

        for index, (start, record) in enumerate(rows):
            end = rows[index + 1][0] if index + 1 < len(rows) else None
            candidates: list[tuple[datetime, dict[str, str | None]]] = []
            for pr in task_prs:
                created_raw = pr.get("created_at")
                if not isinstance(created_raw, str):
                    raise ValueError("malformed pull request: created_at is required")
                created = _aware_datetime(created_raw, field="created_at")
                if created >= start and (end is None or created < end):
                    candidates.append((created, pr))
            if len(candidates) > 1:
                raise ValueError(f"overlap: several PRs map to attempt {record['attempt_id']}")
            if not candidates:
                results[record["attempt_id"]] = (
                    "superseded_without_pr" if end is not None else "open"
                )
                continue

            _, pr = candidates[0]
            terminal_raw = pr.get("merged_at") or pr.get("closed_at")
            if end is not None and terminal_raw is None:
                raise ValueError(f"overlap: open PR crosses attempt {record['attempt_id']} window")
            if end is not None and isinstance(terminal_raw, str):
                terminal = _aware_datetime(terminal_raw, field="PR terminal timestamp")
                if terminal > end:
                    raise ValueError(f"overlap: PR crosses attempt {record['attempt_id']} window")
            if pr.get("merged_at"):
                results[record["attempt_id"]] = "merged"
            elif pr.get("closed_at"):
                results[record["attempt_id"]] = "closed_unmerged"
            else:
                results[record["attempt_id"]] = "open"
    return results


def check_host(alloy_config: str, *, metrics_endpoint: str | None) -> HostCheck:
    """Check only non-secret owner-host invariants."""
    cardinality = _alloy_component_body(
        alloy_config, "otelcol.processor.filter", "codex_cardinality"
    )
    transform = _alloy_component_body(
        alloy_config, "otelcol.processor.transform", "codex_attribution"
    )
    errors = []
    if cardinality is None or CODEX_CARDINALITY_FILTER not in cardinality:
        errors.append("Alloy Codex cardinality filter is missing")
    if any(
        transform is None or statement not in transform
        for statement in REQUIRED_ALLOY_STATEMENTS[1:]
    ):
        errors.append("Alloy task-attribution transform is incomplete")
    if not _has_active_attribution_pipeline(alloy_config):
        errors.append("Alloy task-attribution pipeline is disconnected")
    if metrics_endpoint != METRICS_ENDPOINT:
        errors.append(f"metrics endpoint must be {METRICS_ENDPOINT}")
    return HostCheck(ok=not errors, errors=tuple(dict.fromkeys(errors)))


def _load_ledger(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    records: list[dict[str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed ledger line {number}: {exc}") from exc
        if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
            raise ValueError(f"malformed ledger line {number}: expected an object")
        record = cast("dict[str, str]", value)
        _validate_record(record)
        records.append(record)
    return records


def _append_record(path: Path, record: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _captured(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    if completed.stdout is None or completed.stderr is None:
        raise RuntimeError(f"capture failed for {' '.join(command)}")
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or f"{' '.join(command)} failed")
    return completed.stdout.strip()


def _project(cwd: Path) -> str:
    return _captured(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], cwd=cwd
    )


def _branch(cwd: Path) -> str:
    return _captured(["git", "branch", "--show-current"], cwd=cwd)


class GhPullRequests:
    def for_project(self, project: str) -> list[dict[str, str | None]]:
        raw = _captured(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                project,
                "--state",
                "all",
                "--limit",
                "1000",
                "--json",
                "headRefName,createdAt,mergedAt,closedAt",
            ]
        )
        values = json.loads(raw)
        if not isinstance(values, list):
            raise RuntimeError("gh pr list returned a non-list")
        return [
            {
                "head_ref": row.get("headRefName"),
                "created_at": row.get("createdAt"),
                "merged_at": row.get("mergedAt"),
                "closed_at": row.get("closedAt"),
            }
            for row in values
            if isinstance(row, dict)
        ]


def _user_metrics_endpoint() -> str | None:
    if sys.platform != "win32":
        return os.environ.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
    except FileNotFoundError:
        return None
    return str(value)


def _listener_ready(host: str = "127.0.0.1", port: int = 4318) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _command_tail(values: Sequence[str]) -> list[str]:
    command = list(values)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise ValueError("put the agent command after --")
    return command


def _launch(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    project = _project(cwd)
    task_id = resolve_issue(args.issue, _branch(cwd))
    command = resolve_command(_command_tail(args.command))
    if task_id == "unassigned":
        attempt_id = "unassigned"
    else:
        records = _load_ledger(args.ledger)
        before = len(records)
        record = start_attempt(
            records,
            project=project,
            task_id=task_id,
            started_at=datetime.now().astimezone(),
            new_attempt=args.new_attempt,
            carrier=args.carrier,
        )
        if len(records) > before:
            _append_record(args.ledger, record)
        attempt_id = record["attempt_id"]

    if args.carrier == "claude":
        return run_claude(
            command,
            project=project,
            task_id=task_id,
            attempt_id=attempt_id,
            state_dir=args.ledger.parent,
        )
    environment = encode_codex_environment(project, task_id, attempt_id)
    return subprocess.run(codex_command(command, environment), check=False).returncode


def _outcomes(args: argparse.Namespace) -> int:
    records = _load_ledger(args.ledger)
    print(json.dumps(resolve_outcomes(records, GhPullRequests()), indent=2, sort_keys=True))
    return 0


def _doctor(args: argparse.Namespace) -> int:
    try:
        config = args.alloy_config.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read Alloy config: {exc}", file=sys.stderr)
        return 2
    result = check_host(config, metrics_endpoint=_user_metrics_endpoint())
    errors = list(result.errors)
    if not _listener_ready():
        errors.append("Alloy listener is not reachable on 127.0.0.1:4318")
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("ok: owner task-attribution host route is configured")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    launch = subparsers.add_parser("launch", help="launch a measured local agent")
    launch.add_argument("--issue", type=int)
    launch.add_argument("--carrier", required=True, choices=("claude", "codex"))
    launch.add_argument("--new-attempt", action="store_true")
    launch.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    launch.add_argument("command", nargs=argparse.REMAINDER)
    launch.set_defaults(handler=_launch)

    outcomes = subparsers.add_parser("outcomes", help="resolve attempt outcomes from GitHub")
    outcomes.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    outcomes.set_defaults(handler=_outcomes)

    doctor = subparsers.add_parser("doctor", help="validate the active owner host route")
    doctor.add_argument("--alloy-config", type=Path, default=ALLOY_CONFIG_PATH)
    doctor.set_defaults(handler=_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return cast("int", args.handler(args))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
