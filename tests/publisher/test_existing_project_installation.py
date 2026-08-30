"""RED contract for safe adoption by a non-empty consumer repository."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.adopt_agent_process import (
    CONFLICT_MARKERS,
    install_payload,
    preflight,
    stage_payload,
    update_managed_fragment,
)


def _product(destination: Path) -> dict[str, bytes]:
    files = {
        ".github/workflows/ci.yml": b"name: Product CI\non: [push]\njobs: {product: {runs-on: ubuntu-latest}}\n",
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
        ".github/workflows/agent-process-quality.yml": (
            b"name: Agent process quality\non: [pull_request]\njobs:\n  quality:\n    uses: owner/process/.github/workflows/reusable-quality.yml@"
            + b"0" * 40
            + b"\n"
        ),
        ".github/workflows/agent-process-pr-link.yml": (
            b"name: Agent process PR link\non: [pull_request]\njobs:\n  pr-link:\n    uses: owner/process/.github/workflows/reusable-pr-link.yml@"
            + b"0" * 40
            + b"\n"
        ),
        ".github/workflows/agent-process-review.yml": (
            b"name: Agent process review\non: [pull_request]\njobs:\n  agent-review:\n    uses: owner/process/.github/workflows/reusable-agent-review.yml@"
            + b"0" * 40
            + b"\n"
        ),
        ".agent-process/ownership.yml": b"version: 1\n",
    }


def test_preflight_reports_all_collisions_before_writing(tmp_path: Path) -> None:
    product = _product(tmp_path)
    payload = _payload() | {"pyproject.toml": b"process config\n", "AGENTS.md": b"process\n"}

    report = preflight(tmp_path, payload)

    assert report.collisions == ("AGENTS.md", "pyproject.toml")
    assert {relative: (tmp_path / relative).read_bytes() for relative in product} == product


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
    assert (workflows / "ci.yml").is_file()
    names = ("agent-process-quality.yml", "agent-process-pr-link.yml", "agent-process-review.yml")
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
    assert all(marker in first for marker in CONFLICT_MARKERS.managed)


def test_normal_render_stages_an_installable_reserved_payload(tmp_path: Path) -> None:
    rendered = tmp_path / "rendered"
    (rendered / "scripts").mkdir(parents=True)
    (rendered / "docs").mkdir()
    (rendered / ".github/workflows").mkdir(parents=True)
    (rendered / "scripts/issue_branch.py").write_bytes(b"process entrypoint\n")
    (rendered / "docs/agent-process.md").write_bytes(b"process docs\n")
    caller = rendered / ".github/workflows/agent-process-quality.yml"
    caller.write_bytes(b"jobs: {quality: {}}\n")

    staged = stage_payload(rendered)

    assert staged[".agent-process/payload/scripts/issue_branch.py"] == b"process entrypoint\n"
    assert staged[".agent-process/payload/docs/agent-process.md"] == b"process docs\n"
    assert staged[".github/workflows/agent-process-quality.yml"] == b"jobs: {quality: {}}\n"
