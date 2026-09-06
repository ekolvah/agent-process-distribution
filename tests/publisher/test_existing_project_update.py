"""RED contract for an adoption update that cannot hide unresolved state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.adopt_agent_process import install_payload, preflight, update_payload

ROOT = Path(__file__).resolve().parents[2]


def test_previous_release_update_preserves_consumer_owned_bytes(tmp_path: Path) -> None:
    product = tmp_path / "pyproject.toml"
    product.write_bytes(b"[project]\nname = 'product'\n")
    install_payload(tmp_path, {".agent-process/entry.py": b"version: 1\n"})

    update_payload(tmp_path, {".agent-process/entry.py": b"version: 2\n"})

    assert product.read_bytes() == b"[project]\nname = 'product'\n"
    assert (tmp_path / ".agent-process/entry.py").read_bytes() == b"version: 2\n"


def test_new_template_path_collision_fails_without_rejection_artifacts(tmp_path: Path) -> None:
    foreign = tmp_path / ".agent-process/new.yml"
    foreign.parent.mkdir()
    foreign.write_bytes(b"consumer bytes\n")
    install_payload(tmp_path, {".agent-process/entry.py": b"version: 1\n"})

    with pytest.raises(ValueError, match=r"\.agent-process/new.yml"):
        update_payload(tmp_path, {".agent-process/new.yml": b"process bytes\n"})

    assert foreign.read_bytes() == b"consumer bytes\n"
    assert not list(tmp_path.rglob("*.rej"))


def test_successful_update_is_idempotent(tmp_path: Path) -> None:
    payload = {".agent-process/entry.py": b"version: 2\n"}
    install_payload(tmp_path, {".agent-process/entry.py": b"version: 1\n"})

    update_payload(tmp_path, payload)
    entry = tmp_path / ".agent-process/entry.py"
    assert entry.is_file()
    first = entry.read_bytes()
    update_payload(tmp_path, payload)

    assert entry.read_bytes() == first


def test_update_does_not_treat_scanner_source_as_an_inline_conflict(tmp_path: Path) -> None:
    payload = {
        ".agent-process/scripts/adopt_agent_process.py": (
            b'_UNRESOLVED_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")\n'
        )
    }
    install_payload(tmp_path, payload)

    update_payload(tmp_path, payload)

    assert (tmp_path / ".agent-process/scripts/adopt_agent_process.py").read_bytes() == payload[
        ".agent-process/scripts/adopt_agent_process.py"
    ]


def test_update_does_not_treat_a_setext_heading_as_an_inline_conflict(tmp_path: Path) -> None:
    payload = {".agent-process/docs/note.md": b"Title\n=======\n\nBody text.\n"}
    install_payload(tmp_path, payload)

    update_payload(tmp_path, payload)

    assert (tmp_path / ".agent-process/docs/note.md").read_bytes() == payload[
        ".agent-process/docs/note.md"
    ]


def test_update_preserves_a_bootstrap_generated_project_settings_file(tmp_path: Path) -> None:
    placeholder = {".agent-process/scripts/project_settings.py": b"PROJECT_NUMBER = None\n"}
    install_payload(tmp_path, placeholder)
    settings = tmp_path / ".agent-process/scripts/project_settings.py"
    settings.write_bytes(b"PROJECT_NUMBER = 42\n")

    update_payload(tmp_path, placeholder)

    assert settings.read_bytes() == b"PROJECT_NUMBER = 42\n"


def test_cli_preflight_recognizes_ownership_on_an_already_adopted_destination(
    tmp_path: Path,
) -> None:
    """The standalone CLI `preflight` operation must read the same ownership
    manifest `update` does; it is run ahead of `update` on an already-adopted
    project, so a payload path the manifest already records is not a new
    collision merely because its content is changing in this release.
    """
    destination = tmp_path / "destination"
    install_payload(destination, {".agent-process/entry.py": b"version: 1\n"})
    payload_dir = tmp_path / "payload"
    (payload_dir / ".agent-process").mkdir(parents=True)
    (payload_dir / ".agent-process" / "entry.py").write_bytes(b"version: 2\n")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / ".agent-process/scripts/adopt_agent_process.py"),
            "preflight",
            str(destination),
            str(payload_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_preflight_rejects_a_malformed_managed_fragment_before_any_write(tmp_path: Path) -> None:
    """A malformed marker set must fail preflight before any payload byte is
    written — never mid-write inside `update_managed_fragment` after other
    payload files in the same apply have already landed (#61 finding 2).
    """
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# Product\n<!-- agent-process:begin -->\norphan begin, no matching end\n",
        encoding="utf-8",
    )
    install_payload(tmp_path, {".agent-process/entry.py": b"version: 1\n"})

    report = preflight(tmp_path, {"AGENTS.md": b"process instructions\n"})
    assert report.collisions == ("AGENTS.md",)

    with pytest.raises(ValueError, match="AGENTS.md"):
        update_payload(
            tmp_path,
            {"AGENTS.md": b"process instructions\n", ".agent-process/entry.py": b"version: 2\n"},
        )

    assert agents.read_text(encoding="utf-8") == (
        "# Product\n<!-- agent-process:begin -->\norphan begin, no matching end\n"
    )
    assert (tmp_path / ".agent-process/entry.py").read_bytes() == b"version: 1\n"


def test_update_removes_retired_owned_paths_and_reports_each_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ADR-0018 licenses removing a path the manifest owns once the new
    release no longer ships it; §IV forbids doing so silently (#61 finding 3).
    """
    install_payload(
        tmp_path,
        {
            ".agent-process/entry.py": b"version: 1\n",
            ".agent-process/retired-hook.py": b"old hook\n",
        },
    )

    update_payload(tmp_path, {".agent-process/entry.py": b"version: 2\n"})

    assert not (tmp_path / ".agent-process/retired-hook.py").exists()
    manifest = json.loads((tmp_path / ".agent-process/ownership.json").read_text(encoding="utf-8"))
    assert manifest["paths"] == [".agent-process/entry.py"]
    assert ".agent-process/retired-hook.py" in capsys.readouterr().out
