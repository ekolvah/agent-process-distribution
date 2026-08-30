"""RED contract for an adoption update that cannot hide unresolved state."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopt_agent_process import install_payload, update_payload


def test_previous_release_update_preserves_consumer_owned_bytes(tmp_path: Path) -> None:
    product = tmp_path / "pyproject.toml"
    product.write_bytes(b"[project]\nname = 'product'\n")
    install_payload(tmp_path, {".agent-process/payload/entry.py": b"version: 1\n"})

    update_payload(tmp_path, {".agent-process/payload/entry.py": b"version: 2\n"})

    assert product.read_bytes() == b"[project]\nname = 'product'\n"
    assert (tmp_path / ".agent-process/payload/entry.py").read_bytes() == b"version: 2\n"


def test_new_template_path_collision_fails_without_rejection_artifacts(tmp_path: Path) -> None:
    foreign = tmp_path / ".agent-process/new.yml"
    foreign.parent.mkdir()
    foreign.write_bytes(b"consumer bytes\n")
    install_payload(tmp_path, {".agent-process/payload/entry.py": b"version: 1\n"})

    with pytest.raises(ValueError, match=r"\.agent-process/new.yml"):
        update_payload(tmp_path, {".agent-process/new.yml": b"process bytes\n"})

    assert foreign.read_bytes() == b"consumer bytes\n"
    assert not list(tmp_path.rglob("*.rej"))


def test_successful_update_is_idempotent(tmp_path: Path) -> None:
    payload = {".agent-process/payload/entry.py": b"version: 2\n"}
    install_payload(tmp_path, {".agent-process/payload/entry.py": b"version: 1\n"})

    update_payload(tmp_path, payload)
    entry = tmp_path / ".agent-process/payload/entry.py"
    assert entry.is_file()
    first = entry.read_bytes()
    update_payload(tmp_path, payload)

    assert entry.read_bytes() == first
