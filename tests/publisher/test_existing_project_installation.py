"""RED contract for safe adoption by a non-empty consumer repository."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.adopt_agent_process import (
    _MANAGED_FRAGMENT_BEGIN,
    _MANAGED_FRAGMENT_END,
    _MANAGED_FRAGMENT_TARGETS,
    _OWNERSHIP_FILE,
    _PRESERVED_ON_UPDATE_TARGETS,
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
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (destination / ".agent-process/entry.py").read_bytes() == b"version: 2\n"


def test_reinstall_preserves_a_previously_owned_project_settings_file(tmp_path: Path) -> None:
    """Ownership, not the install/update distinction, must gate
    `_PRESERVED_ON_UPDATE_TARGETS`: bootstrap replaces the placeholder with
    live Project IDs after the first install, and a later `install_payload`
    call against that same, already-adopted destination (not only an
    `update_payload` call) must not overwrite that live state with the
    payload's empty placeholder again.
    """
    (target,) = _PRESERVED_ON_UPDATE_TARGETS
    payload = {target: b"# placeholder\n"}
    install_payload(tmp_path, payload)
    (tmp_path / target).write_bytes(b"PROJECT_ID = 42\n")

    install_payload(tmp_path, payload)

    assert (tmp_path / target).read_bytes() == b"PROJECT_ID = 42\n"


def test_install_ignores_conflict_marker_text_outside_the_process_scope(tmp_path: Path) -> None:
    """A product fixture or doc containing literal conflict-marker text is
    not a Copier artifact merely because it lives somewhere in the
    destination; only content at a process-managed path can be one.
    """
    _product(tmp_path)
    unrelated = tmp_path / "docs" / "example-conflict.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("<<<<<<<\nours\n=======\ntheirs\n>>>>>>>\n", encoding="utf-8")

    install_payload(tmp_path, _payload())

    assert unrelated.read_text(encoding="utf-8") == "<<<<<<<\nours\n=======\ntheirs\n>>>>>>>\n"


def test_install_rejects_a_rej_artifact_beside_a_closed_root_file(tmp_path: Path) -> None:
    """A Copier `.rej` artifact takes its scope from the file it rejects, not
    from its own suffixed name: `AGENTS.md.rej` is a reject for the exact
    closed-root path `AGENTS.md`, and stripping only the `.rej` suffix before
    the process-path check is what puts it back in scope.
    """
    _product(tmp_path)
    (tmp_path / "AGENTS.md.rej").write_bytes(b"<<<<<<<\n")

    with pytest.raises(ValueError, match="unresolved Copier conflict artifact"):
        install_payload(tmp_path, _payload())


def test_cli_install_rejects_a_nonexistent_payload_directory(tmp_path: Path) -> None:
    """A mistyped payload path must not silently become an empty payload:
    `Path.rglob()` on a missing directory yields nothing, so `main()` would
    otherwise dispatch to `install_payload` with an empty payload, which
    overwrites the existing ownership manifest with `{"paths": []}` and turns
    every previously installed file into an unowned collision on the next
    real update.
    """
    destination = tmp_path / "destination"
    install_payload(destination, {".agent-process/entry.py": b"version: 1\n"})
    missing_payload_dir = tmp_path / "does-not-exist"

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / ".agent-process/scripts/adopt_agent_process.py"),
            "install",
            str(destination),
            str(missing_payload_dir),
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode != 0, completed.stdout + completed.stderr
    manifest = json.loads(
        (destination / ".agent-process/ownership.json").read_text(encoding="utf-8")
    )
    assert manifest["paths"] == [".agent-process/entry.py"]


def test_adoption_into_an_established_repository_preserves_every_product_file(
    tmp_path: Path,
) -> None:
    """Criterion 1: every file class a real established repository already
    owns — scripts, docs, tests, dependency and project config, and the
    shared AGENTS.md fragment target — survives adoption byte-identical.
    """
    product = {
        "scripts/build.py": b"#!/usr/bin/env python\nprint('build')\n",
        "docs/readme.md": b"# Product docs\n",
        "tests/test_build.py": b"def test_build():\n    assert True\n",
        "requirements.txt": b"requests==2.0.0\n",
        "pyproject.toml": b"[project]\nname = 'product'\n",
        "AGENTS.md": b"# Product instructions\n",
    }
    for relative, content in product.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    payload = _payload() | {"AGENTS.md": b"process instructions\n"}

    install_payload(tmp_path, payload)

    for relative, content in product.items():
        if relative != "AGENTS.md":
            assert (tmp_path / relative).read_bytes() == content
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.startswith("# Product instructions\n")
    assert (
        "<!-- agent-process:begin -->\nprocess instructions\n<!-- agent-process:end -->" in agents
    )
    assert (tmp_path / ".agent-process/ownership.yml").is_file()


def test_no_inert_payload_archive_is_reintroduced(rendered_default: Path) -> None:
    """Criterion 4: the abandoned staged-archive design (`stage_payload()`,
    `_ALLOWED_PREFIXES`, a `.agent-process/payload/` directory) never comes
    back — a rendered consumer receives only the reserved payload itself.
    """
    source = (ROOT / ".agent-process/scripts/adopt_agent_process.py").read_text(encoding="utf-8")
    assert "stage_payload" not in source
    assert "_ALLOWED_PREFIXES" not in source
    assert not (rendered_default / ".agent-process/payload").exists()


def test_update_managed_fragment_ignores_an_inline_marker_mention(tmp_path: Path) -> None:
    """Finding 4: a line that only *mentions* both markers as substrings (for
    example, documentation about the delimiter syntax) is not a real
    fragment. The old substring search sliced out and discarded every
    consumer byte between the two mentions instead of treating this as "no
    fragment yet".
    """
    path = tmp_path / "AGENTS.md"
    original = (
        "# Docs\n"
        "Delimiters look like <!-- agent-process:begin --> ... "
        "<!-- agent-process:end -->.\n"
    )
    path.write_text(original, encoding="utf-8")

    update_managed_fragment(path, "process instructions")

    updated = path.read_text(encoding="utf-8")
    assert updated.startswith(original)
    assert (
        "<!-- agent-process:begin -->\nprocess instructions\n<!-- agent-process:end -->" in updated
    )


def test_preflight_rejects_a_symlinked_managed_fragment_target(tmp_path: Path) -> None:
    """Finding 5 / criterion 6: a symlinked AGENTS.md must be reported by
    preflight, not silently detached into a regular file by the atomic write
    inside `update_managed_fragment`.
    """
    destination = tmp_path / "destination"
    destination.mkdir()
    real = tmp_path / "real-agents.md"
    real.write_text("# shared\n", encoding="utf-8")
    try:
        (destination / "AGENTS.md").symlink_to(real)
    except OSError:
        pytest.skip("symlink creation not permitted in this environment")

    report = preflight(destination, {"AGENTS.md": b"process instructions\n"})

    assert report.collisions == ("AGENTS.md",)
    assert real.read_text(encoding="utf-8") == "# shared\n"


def _validity_directory(destination: Path, target: str) -> None:
    (destination / target).mkdir(parents=True)


def _validity_symlink(destination: Path, target: str) -> None:
    real = destination.parent / f"real-{Path(target).name}"
    real.write_text("shared\n", encoding="utf-8")
    (destination / target).symlink_to(real)


def _validity_rej_artifact(destination: Path, target: str) -> None:
    (destination / target).write_text("# product\n", encoding="utf-8")
    (destination / f"{target}.rej").write_text("<<<<<<<\n", encoding="utf-8")


def _validity_malformed_markers(destination: Path, target: str) -> None:
    (destination / target).write_text(
        "# product\n<!-- agent-process:begin -->\norphan begin\n", encoding="utf-8"
    )


_DESTINATION_VALIDITY_SCENARIOS = (
    ("directory", _validity_directory),
    ("symlink", _validity_symlink),
    ("rej-artifact", _validity_rej_artifact),
    ("malformed-markers", _validity_malformed_markers),
)


@pytest.mark.parametrize("target", sorted(_MANAGED_FRAGMENT_TARGETS))
@pytest.mark.parametrize("name,setup", _DESTINATION_VALIDITY_SCENARIOS)
def test_managed_fragment_destination_validity_table(
    tmp_path: Path, name: str, setup, target: str
) -> None:
    """Criterion 7: one table for every destination-validity hazard at a
    managed-fragment target, instead of one bespoke test per finding.
    """
    destination = tmp_path / "destination"
    destination.mkdir()
    try:
        setup(destination, target)
    except OSError:
        pytest.skip("symlink creation not permitted in this environment")
    before = {
        item.relative_to(destination).as_posix(): item.read_bytes()
        for item in destination.rglob("*")
        if item.is_file()
    }

    with pytest.raises(ValueError):
        install_payload(destination, {target: b"process instructions\n"})

    after = {
        item.relative_to(destination).as_posix(): item.read_bytes()
        for item in destination.rglob("*")
        if item.is_file()
    }
    assert after == before


def test_install_rejects_a_directory_at_the_ownership_manifest_path(tmp_path: Path) -> None:
    """The ownership-manifest destination must be validated before any payload
    write: a preexisting directory there must not be silently treated as "no
    manifest yet", which would let `_apply` write every payload file and only
    then fail on the final manifest write, leaving a partially adopted repo.
    """
    _product(tmp_path)
    (tmp_path / _OWNERSHIP_FILE).mkdir(parents=True)

    with pytest.raises(ValueError, match="ownership manifest"):
        install_payload(tmp_path, _payload())

    assert not (tmp_path / ".github/workflows/ci.yml").is_file()
