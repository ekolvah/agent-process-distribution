"""Compare the self-applied root with a fresh working-tree render."""

from __future__ import annotations

import difflib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

VOLATILE_ANSWER_KEYS = frozenset({"_commit", "_src_path"})
REQUIRED_GENERATED_PATHS = frozenset(
    {
        "AGENTS.md",
        ".agents/skills/implement-issue/SKILL.md",
        ".claude/settings.json",
        ".codex/hooks.json",
        "docs/architecture/agent-process.md",
        "scripts/ci_check.py",
    }
)
ROOT_ONLY_DIRECTORIES = frozenset(
    {
        ".claude-plugin",
        ".render-bootstrap-probe",
        "agents",
        "commands",
        "evidence",
        "template",
    }
)
# Build artefacts never belong to a payload at any depth.  The source-only
# directories above exist only at the checkout root, so matching them at any
# depth would hide nested payload paths such as .agents/skills/*/agents/.
ARTIFACT_DIRECTORIES = frozenset({".git", ".pytest_cache", ".ruff_cache", "__pycache__"})
COPIER_METADATA_PATHS = frozenset({".copier-answers.yml"})


@dataclass(frozen=True)
class DriftReport:
    """Failures found by the gate; every undeclared root-only path fails."""

    errors: tuple[str, ...]

    def format(self) -> str:
        """Describe failures with the one permitted repair direction."""
        parts = [*self.errors]
        if self.errors:
            parts.append(
                "Fix direction: edit template/ and re-render; never hand-edit the generated "
                "root copy. Declare genuine source-only paths in template-drift-allowlist.yml."
            )
        return "\n\n".join(parts)


@dataclass(frozen=True)
class Allowlist:
    """Declared source-repository exceptions to byte-for-byte equality."""

    root_only_paths: frozenset[str]
    expected_to_differ_paths: frozenset[str]


def load_answers(root: Path) -> dict[str, object]:
    """Load reproducible answers without machine- or revision-specific metadata."""
    answers = yaml.safe_load((root / ".copier-answers.yml").read_text(encoding="utf-8"))
    if not isinstance(answers, dict):
        raise ValueError(".copier-answers.yml must contain a mapping")
    return {key: value for key, value in answers.items() if key not in VOLATILE_ANSWER_KEYS}


def load_allowlist(root: Path) -> Allowlist:
    """Read the two declared exception kinds."""
    data = yaml.safe_load((root / "template-drift-allowlist.yml").read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("template-drift-allowlist.yml must contain a mapping")

    def paths(key: str) -> frozenset[str]:
        rows = data.get(key, [])
        if not isinstance(rows, list):
            raise ValueError(f"{key} must be a list")
        result: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str):
                raise ValueError(f"{key} rows must contain path")
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                raise ValueError(f"{key} rows must contain a reason")
            result.add(row["path"])
        return frozenset(result)

    return Allowlist(paths("root_only_paths"), paths("expected_to_differ_paths"))


def render_working_tree(root: Path, destination: Path) -> Path:
    """Render a git-free copy so uncommitted template edits are visible."""
    source = destination.parent / "source"
    source.mkdir()
    shutil.copy2(root / "copier.yml", source / "copier.yml")
    shutil.copytree(root / "template", source / "template")
    answers_path = destination.parent / "answers.yml"
    answers_path.write_text(yaml.safe_dump(load_answers(root), sort_keys=True), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            str(source),
            str(destination),
            "--defaults",
            "--trust",
            "--data-file",
            str(answers_path),
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return destination


def _files(directory: Path) -> dict[str, Path]:
    return {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
        and path.relative_to(directory).parts[0] not in ROOT_ONLY_DIRECTORIES
        and not ARTIFACT_DIRECTORIES & set(path.relative_to(directory).parts)
    }


def _normalised(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _diff(path: str, rendered: Path, root: Path) -> str:
    diff = difflib.unified_diff(
        _normalised(rendered).splitlines(),
        _normalised(root).splitlines(),
        fromfile=f"rendered/{path}",
        tofile=f"root/{path}",
        lineterm="",
    )
    return "\n".join((f"content differs: {path}", *diff))


def compare(root: Path, rendered: Path, allowlist: Allowlist) -> DriftReport:
    """Compare rendered payload files with the self-applied root."""
    root_files = _files(root)
    rendered_files = _files(rendered)
    rendered_files = {
        path: file for path, file in rendered_files.items() if path not in COPIER_METADATA_PATHS
    }
    errors: list[str] = []

    missing_required = REQUIRED_GENERATED_PATHS - rendered_files.keys()
    if missing_required:
        errors.append(
            "vacuous render is missing known generated paths: "
            + ", ".join(sorted(missing_required))
        )

    for path, rendered_path in rendered_files.items():
        root_path = root_files.get(path)
        if root_path is None:
            errors.append(f"missing generated file: {path}")
        elif path not in allowlist.expected_to_differ_paths and _normalised(
            rendered_path
        ) != _normalised(root_path):
            errors.append(_diff(path, rendered_path, root_path))

    for path in allowlist.expected_to_differ_paths:
        if path not in root_files or path not in rendered_files:
            errors.append(f"stale expected-to-differ allowlist entry: {path}")
        elif _normalised(root_files[path]) == _normalised(rendered_files[path]):
            errors.append(f"stale expected-to-differ allowlist entry: {path}")

    for path in allowlist.root_only_paths:
        if path not in root_files or path in rendered_files:
            errors.append(f"stale root-only allowlist entry: {path}")

    for path in sorted(root_files.keys() - rendered_files.keys()):
        if path in allowlist.root_only_paths:
            continue
        errors.append(f"undeclared extra file: {path}")

    return DriftReport(tuple(errors))


def check(root: Path) -> DriftReport:
    """Render the working tree and return all declared and undeclared drift."""
    with tempfile.TemporaryDirectory() as temporary:
        rendered = render_working_tree(root, Path(temporary) / "rendered")
        return compare(root, rendered, load_allowlist(root))
