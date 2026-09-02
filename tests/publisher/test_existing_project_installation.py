"""RED contract for safe adoption by a non-empty consumer repository."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.adopt_agent_process import (
    _MANAGED_FRAGMENT_BEGIN,
    _MANAGED_FRAGMENT_END,
    _payload_from_directory,
    install_payload,
    preflight,
    update_managed_fragment,
)

ROOT = Path(__file__).resolve().parents[2]


def _product(destination: Path) -> dict[str, bytes]:
    files = {
        "pyproject.toml": b"[project]\nname = 'product'\ndependencies = ['product-dep']\n",
        ".gitignore": b"product-cache/\n",
        ".github/pull_request_template.md": b"# Product PR\n",
        "AGENTS.md": b"# Product instructions\n",
    }
    for relative, content in files.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return files


def _payload() -> dict[str, bytes]:
    return {
        ".github/workflows/ci.yml": (
            b"name: Agent process quality\non: [pull_request]\njobs:\n  quality:\n    uses: owner/process/.github/workflows/reusable-quality.yml@"
            + b"0" * 40
            + b"\n"
        ),
        ".github/workflows/pr-link.yml": (
            b"name: Agent process PR link\non: [pull_request]\njobs:\n  pr-link:\n    uses: owner/process/.github/workflows/reusable-pr-link.yml@"
            + b"0" * 40
            + b"\n"
        ),
        ".github/workflows/agent-review.yml": (
            b"name: Agent process review\non: [pull_request]\njobs:\n  agent-review:\n    uses: owner/process/.github/workflows/reusable-agent-review.yml@"
            + b"0" * 40
            + b"\n"
        ),
        ".agent-process/ownership.yml": b"version: 1\n",
    }


def test_preflight_reports_all_collisions_before_writing(tmp_path: Path) -> None:
    product = _product(tmp_path)
    payload = _payload() | {"pyproject.toml": b"process config\n"}

    report = preflight(tmp_path, payload)

    assert report.collisions == ("pyproject.toml",)
    assert {relative: (tmp_path / relative).read_bytes() for relative in product} == product


def test_preflight_never_reports_a_managed_fragment_target_as_a_collision(tmp_path: Path) -> None:
    _product(tmp_path)
    payload = _payload() | {
        "AGENTS.md": b"process instructions\n",
        ".gitignore": b"process-cache/\n",
    }

    report = preflight(tmp_path, payload)

    assert report.collisions == ()


def test_install_merges_agents_md_into_a_differing_product_file(tmp_path: Path) -> None:
    _product(tmp_path)
    payload = _payload() | {"AGENTS.md": b"process instructions"}

    install_payload(tmp_path, payload)

    installed = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert installed.startswith("# Product instructions\n")
    assert (
        "<!-- agent-process:begin -->\nprocess instructions\n<!-- agent-process:end -->"
        in installed
    )


def test_install_preserves_product_gates_and_configuration(tmp_path: Path) -> None:
    product = _product(tmp_path)

    install_payload(tmp_path, _payload())

    assert {relative: (tmp_path / relative).read_bytes() for relative in product} == product
    ownership = tmp_path / ".agent-process/ownership.yml"
    assert ownership.is_file()
    assert ownership.read_bytes() == b"version: 1\n"


def test_process_callers_use_reserved_paths_without_replacing_product_ci(tmp_path: Path) -> None:
    _product(tmp_path)

    install_payload(tmp_path, _payload())

    workflows = tmp_path / ".github/workflows"
    names = ("ci.yml", "pr-link.yml", "agent-review.yml")
    assert all((workflows / name).is_file() for name in names)
    callers = [yaml.safe_load((workflows / name).read_text(encoding="utf-8")) for name in names]
    assert [next(iter(caller["jobs"])) for caller in callers] == [
        "quality",
        "pr-link",
        "agent-review",
    ]


def test_shared_singleton_update_is_idempotent_and_preserves_surrounding_content(
    tmp_path: Path,
) -> None:
    path = tmp_path / "AGENTS.md"
    path.write_text("# Product instructions\n", encoding="utf-8")

    update_managed_fragment(path, "follow docs/architecture/agent-process.md")
    first = path.read_text(encoding="utf-8")
    update_managed_fragment(path, "follow docs/architecture/agent-process.md")

    assert path.read_text(encoding="utf-8") == first
    assert first.startswith("# Product instructions\n")
    assert _MANAGED_FRAGMENT_BEGIN in first
    assert _MANAGED_FRAGMENT_END in first


def test_normal_render_stages_an_installable_reserved_payload(tmp_path: Path) -> None:
    rendered = tmp_path / "rendered"
    (rendered / ".agent-process/scripts").mkdir(parents=True)
    (rendered / ".agent-process/docs").mkdir()
    (rendered / ".github/workflows").mkdir(parents=True)
    (rendered / ".agent-process/scripts/issue_branch.py").write_bytes(b"process entrypoint\n")
    (rendered / ".agent-process/docs/agent-process.md").write_bytes(b"process docs\n")
    caller = rendered / ".github/workflows/ci.yml"
    caller.write_bytes(b"jobs: {quality: {}}\n")

    staged = _payload_from_directory(rendered)

    assert staged[".agent-process/scripts/issue_branch.py"] == b"process entrypoint\n"
    assert staged[".agent-process/docs/agent-process.md"] == b"process docs\n"
    assert staged[".github/workflows/ci.yml"] == b"jobs: {quality: {}}\n"


def test_normal_render_installs_the_selected_claude_adapter_at_the_root(tmp_path: Path) -> None:
    rendered = tmp_path / "rendered"
    (rendered / ".claude").mkdir(parents=True)
    (rendered / ".claude/settings.json").write_bytes(b'{"deny": []}\n')

    staged = _payload_from_directory(rendered)

    assert staged[".claude/settings.json"] == b'{"deny": []}\n'


def test_preflight_rejects_a_directory_at_a_payload_file_path(tmp_path: Path) -> None:
    (tmp_path / ".agent-process/entry.py").mkdir(parents=True)

    report = preflight(tmp_path, {".agent-process/entry.py": b"process\n"})

    assert report.collisions == (".agent-process/entry.py",)


def test_preflight_rejects_a_symlinked_destination_parent(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    destination = tmp_path / "destination"
    destination.mkdir()
    try:
        (destination / ".agent-process").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation not permitted in this environment")

    report = preflight(destination, {".agent-process/scripts/entry.py": b"process\n"})

    assert report.collisions == (".agent-process/scripts/entry.py",)
    assert not (outside / "entry.py").exists()


def test_cli_install_succeeds_against_an_already_adopted_destination_with_changed_owned_content(
    tmp_path: Path,
) -> None:
    """`main()` computes `owned_paths` once from the destination's ownership
    manifest and uses it for its own preflight check before dispatching to
    `install_payload`/`update_payload` — but `install_payload` always calls
    `_apply(..., updating=False)`, which discards that manifest and re-checks
    with an empty owned-path set. A path the CLI's own preflight just cleared
    as owned then collides again one call later, raising inside `main` on a
    destination the CLI itself just judged safe to write.
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
            "install",
            str(destination),
            str(payload_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (destination / ".agent-process/entry.py").read_bytes() == b"version: 2\n"
