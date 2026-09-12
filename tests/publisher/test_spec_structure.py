"""Format guard for the system specs under `docs/spec/` (issue #105).

`docs/spec/README.md` defines the spec format in prose; a format that lives only in prose is
followed less than half the time. This test is the "scripts over instructions" form of that
README: every rule it states that is deterministic becomes an exit code here.

Scope is the directory glob, not a list, so the next spec enters the rule automatically.
Presence != correctness: whether a requirement is *current* is a review question, not a test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "docs" / "spec"
README = SPEC_DIR / "README.md"

# Same marker and floor as `tests/agent_process/test_doc_headers.py`; that guard is scoped to
# the process canon directories and this one to the spec directory, so neither shadows the other.
_HEADER_MARKER = "**Question this document answers:**"
_MIN_ANSWER_CHARS = 20

# `- **DIST-3** (MUST) …` — one requirement per list item, ID first so it is greppable.
_REQUIREMENT = re.compile(r"^- \*\*([A-Z]+)-(\d+)\*\* \((MUST|SHOULD)\) \S")
_REQUIRED_SECTIONS = (
    "## Requirements",
    "## Rationale",
    "## Non-goals",
    "## Open questions",
    "## Traceability",
)
# `NN-slug.md`: the numeric prefix orders the index and leaves room (step of 10) for new areas.
_SPEC_NAME = re.compile(r"^\d{2}-[a-z0-9-]+\.md$")
_MAX_LINES = 150


def _spec_files() -> list[Path]:
    return sorted(path for path in SPEC_DIR.glob("*.md") if path != README)


def _header_answer(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("## "):
            return None
        stripped = line.removeprefix("> ").strip()
        if stripped.startswith(_HEADER_MARKER):
            return stripped.removeprefix(_HEADER_MARKER).strip()
    return None


def _requirements(text: str) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for line in text.splitlines():
        match = _REQUIREMENT.match(line)
        if match:
            found.append((match.group(1), int(match.group(2))))
    return found


def test_spec_directory_has_readme_and_at_least_one_spec() -> None:
    assert README.is_file(), f"missing {README.relative_to(ROOT).as_posix()}"
    assert _spec_files(), f"no `NN-slug.md` spec next to {README.name}"


@pytest.mark.parametrize("path", _spec_files(), ids=lambda p: p.name)
def test_spec_file_conforms_to_the_readme_format(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    if not _SPEC_NAME.match(path.name):
        problems.append("file name is not `NN-slug.md`")
    answer = _header_answer(text)
    if answer is None or len(answer) < _MIN_ANSWER_CHARS:
        problems.append(
            f"header `{_HEADER_MARKER}` missing or shorter than {_MIN_ANSWER_CHARS} chars"
        )
    for section in _REQUIRED_SECTIONS:
        if not re.search(rf"^{re.escape(section)}\s*$", text, re.MULTILINE):
            problems.append(f"missing section `{section}`")
    requirements = _requirements(text)
    if not requirements:
        problems.append("no requirement line `- **PREFIX-N** (MUST|SHOULD) …`")
    prefixes = {prefix for prefix, _ in requirements}
    if len(prefixes) > 1:
        problems.append(f"one prefix per file, found {sorted(prefixes)}")
    numbers = [number for _, number in requirements]
    if len(numbers) != len(set(numbers)):
        problems.append("duplicate requirement number inside the file")
    line_count = len(text.splitlines())
    if line_count > _MAX_LINES:
        problems.append(f"{line_count} lines > {_MAX_LINES}: split by area, not by date")
    assert not problems, f"{path.name}: " + "; ".join(problems)


def test_requirement_prefixes_are_unique_across_specs() -> None:
    # An empty directory would pass vacuously — the silent-skip shape this guard exists to reject.
    assert _spec_files(), "no spec files to compare"
    owners: dict[str, list[str]] = {}
    for path in _spec_files():
        for prefix in {prefix for prefix, _ in _requirements(path.read_text(encoding="utf-8"))}:
            owners.setdefault(prefix, []).append(path.name)
    shared = {prefix: names for prefix, names in owners.items() if len(names) > 1}
    assert not shared, f"requirement prefix owned by several specs: {shared}"


def test_readme_indexes_every_spec_file() -> None:
    readme = README.read_text(encoding="utf-8")
    missing = [path.name for path in _spec_files() if f"({path.name})" not in readme]
    assert not missing, f"README.md index does not link: {missing}"
