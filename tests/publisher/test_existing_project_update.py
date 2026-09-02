"""RED contract for an adoption update that cannot hide unresolved state."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.adopt_agent_process import install_payload, update_payload

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
