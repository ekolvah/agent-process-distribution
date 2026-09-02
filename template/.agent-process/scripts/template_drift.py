"""Compare the self-applied root with a fresh working-tree render."""

from __future__ import annotations

import ast
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
        ".codex/hooks.json",
        ".agent-process/docs/architecture/agent-process.md",
        ".agent-process/scripts/ci_check.py",
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
ARTIFACT_DIRECTORIES = frozenset(
    {".audit-tmp", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}
)
ARTIFACT_DIRECTORY_PREFIXES = ("pytest-cache-files-",)
COPIER_METADATA_PATHS = frozenset({".agent-process/copier-answers.yml"})
SOURCE_ONLY_COPIER_REQUIREMENTS: dict[str, object] = {}


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
    expected_difference_paths: frozenset[str]


def load_answers(root: Path) -> dict[str, object]:
    """Load reproducible answers without machine- or revision-specific metadata."""
    answers = yaml.safe_load(
        (root / ".agent-process" / "copier-answers.yml").read_text(encoding="utf-8")
    )
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

    root_only_paths = paths("root_only_paths")
    expected_difference_paths = paths("expected_difference_paths")
    overlap = root_only_paths & expected_difference_paths
    if overlap:
        raise ValueError(
            "allowlist paths cannot be both root-only and expected-difference: "
            + ", ".join(sorted(overlap))
        )
    return Allowlist(root_only_paths, expected_difference_paths)


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


def _files(directory: Path, *, exclude_root_only_directories: bool = False) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in directory.rglob("*"):
        relative_path = path.relative_to(directory)
        if not path.is_file():
            continue
        if exclude_root_only_directories and relative_path.parts[0] in ROOT_ONLY_DIRECTORIES:
            continue
        if any(
            part in ARTIFACT_DIRECTORIES or part.startswith(ARTIFACT_DIRECTORY_PREFIXES)
            for part in relative_path.parts
        ):
            continue
        files[relative_path.as_posix()] = path
    return files


def _git_visible_files(root: Path) -> frozenset[str] | None:
    """The file set git itself would hand another checkout of `root`.

    `None` means `root` is not a git working tree at all (this module's own
    drift tests copy the source tree without `.git`) — the caller must fall
    back to the unfiltered walk, never to treating this as an empty set.
    `.exists()`, not `.is_dir()`: a linked worktree's `.git` is a file.
    """
    if not (root / ".git").exists():
        return None
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return frozenset(name for name in completed.stdout.split("\0") if name)


def _normalised(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _top_level_names(content: str) -> frozenset[str]:
    """Names a Python module defines at top level: assignments, defs, classes.

    Bootstrap generates the activated `project_settings.py` from scratch, so an
    `expected_difference_paths` entry can never require full-content equality
    for it — the docstring and `require_configured` body legitimately differ.
    Comparing this name set instead still catches a future template-only
    change to the settings API (a renamed, added, or removed field or
    function) that full suppression would otherwise hide.
    """
    names: set[str] = set()
    for node in ast.parse(content).body:
        if isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return frozenset(names)


def _normalised_root(path: str, root: Path) -> tuple[str, str | None]:
    """Remove and validate the one source-only Copier dependency when applicable."""
    content = _normalised(root)
    requirement = SOURCE_ONLY_COPIER_REQUIREMENTS.get(path)
    if requirement is None:
        return content, None

    lines = content.splitlines(keepends=True)
    copier_lines = [line for line in lines if requirement(line.strip())]
    if len(copier_lines) != 1:
        return content, f"missing source-only Copier requirement: {path}"
    return "".join(line for line in lines if not requirement(line.strip())), None


def _diff(path: str, rendered: Path, root_content: str) -> str:
    diff = difflib.unified_diff(
        _normalised(rendered).splitlines(),
        root_content.splitlines(),
        fromfile=f"rendered/{path}",
        tofile=f"root/{path}",
        lineterm="",
    )
    return "\n".join((f"content differs: {path}", *diff))


def compare(root: Path, rendered: Path, allowlist: Allowlist) -> DriftReport:
    """Compare rendered payload files with the self-applied root."""
    root_files = _files(root, exclude_root_only_directories=True)
    root_files = {
        path: file for path, file in root_files.items() if path not in COPIER_METADATA_PATHS
    }
    git_visible = _git_visible_files(root)
    if git_visible is not None:
        root_files = {path: file for path, file in root_files.items() if path in git_visible}
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
            continue
        root_content, root_error = _normalised_root(path, root_path)
        if root_error:
            errors.append(root_error)
            continue
        rendered_content = _normalised(rendered_path)
        if rendered_content == root_content:
            continue
        if path not in allowlist.expected_difference_paths:
            errors.append(_diff(path, rendered_path, root_content))
            continue
        if path.endswith(".py") and _top_level_names(rendered_content) != _top_level_names(
            root_content
        ):
            errors.append(_diff(path, rendered_path, root_content))

    for path in allowlist.root_only_paths:
        if path not in root_files or path in rendered_files:
            errors.append(f"stale root-only allowlist entry: {path}")

    for path in allowlist.expected_difference_paths:
        root_path = root_files.get(path)
        rendered_path = rendered_files.get(path)
        if root_path is None or rendered_path is None:
            errors.append(f"stale expected-difference allowlist entry: {path}")
            continue
        root_content, root_error = _normalised_root(path, root_path)
        if root_error or _normalised(rendered_path) == root_content:
            errors.append(f"stale expected-difference allowlist entry: {path}")

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
