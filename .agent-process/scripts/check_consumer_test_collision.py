#!/usr/bin/env python3
"""Fail visibly when a foreign file already occupies a reserved consumer test path.

    python .agent-process/scripts/check_consumer_test_collision.py <destination> [--vcs-ref REF]

Copier's own `--conflict {rej,inline}` only marks a conflict for a path it
previously tracked via a prior render's diff; a brand-new template path
colliding with pre-existing, unrelated content at that exact destination
path is invisible to it and would otherwise be silently overwritten by
`copier update`. This script reads `<destination>/.agent-process/copier-answers.yml` for
the template origin (`_src_path`) and the destination's own recorded
answers, renders that same source fresh via the `copier` executable on
`PATH` (the one a consumer installs separately, e.g. through pipx; this
project's own Copier dependency is publisher-only), and reports every
reserved-subtree path whose content already differs before the update runs.

`--vcs-ref` mirrors `copier update`'s own flag: omitted, the target is
whatever a plain `copier update` would pick (the template's latest release
tag, or its latest commit if it has none); passed, it pins the render to
that ref, e.g. `--vcs-ref HEAD` to include local uncommitted template
changes when testing against a working checkout of the template itself.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

_VOLATILE_ANSWER_KEYS = frozenset({"_src_path", "_commit"})
_RESERVED_SUBTREE = "tests/agent_process"


def _load_answers_file(destination: Path) -> tuple[str, dict[str, object]]:
    answers_path = destination / ".agent-process" / "copier-answers.yml"
    if not answers_path.is_file():
        raise FileNotFoundError(
            f"{answers_path} not found; {destination} was never rendered from this template."
        )
    data = yaml.safe_load(answers_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("_src_path"), str):
        raise ValueError(f"{answers_path} must record _src_path")
    src_path = data["_src_path"]
    answers = {key: value for key, value in data.items() if key not in _VOLATILE_ANSWER_KEYS}
    return src_path, answers


def _render_current_template(
    work: Path, src_path: str, answers: dict[str, object], vcs_ref: str | None
) -> Path:
    rendered = work / "rendered"
    answers_path = work / "answers.yml"
    answers_path.write_text(yaml.safe_dump(answers, sort_keys=True), encoding="utf-8")
    copier_executable = shutil.which("copier")
    if copier_executable is None:
        raise RuntimeError(
            "copier executable not found on PATH; install it (e.g. `pipx install copier`) "
            "before running this check."
        )
    command = [
        copier_executable,
        "copy",
        src_path,
        str(rendered),
        "--defaults",
        "--trust",
        "-q",
        "--data-file",
        str(answers_path),
    ]
    if vcs_ref is not None:
        command += ["--vcs-ref", vcs_ref]
    completed = subprocess.run(
        command, text=True, capture_output=True, encoding="utf-8", errors="replace", check=False
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    return rendered


def find_collisions(destination: Path, *, vcs_ref: str | None = None) -> list[str]:
    """Reserved-subtree paths already present at `destination` with foreign content."""
    src_path, answers = _load_answers_file(destination)
    with tempfile.TemporaryDirectory() as temporary:
        rendered = _render_current_template(Path(temporary), src_path, answers, vcs_ref)
        reserved_root = rendered / _RESERVED_SUBTREE
        if not reserved_root.is_dir():
            return []
        collisions = []
        for path in sorted(reserved_root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(rendered).as_posix()
            existing = destination / relative
            if existing.is_file() and existing.read_bytes() != path.read_bytes():
                collisions.append(relative)
        return collisions


def _parse_args(argv: list[str]) -> tuple[str, str | None] | None:
    if len(argv) == 1:
        return argv[0], None
    if len(argv) == 3 and argv[1] == "--vcs-ref":
        return argv[0], argv[2]
    return None


def main(argv: list[str]) -> int:
    parsed = _parse_args(argv)
    if parsed is None:
        print(
            "usage: check_consumer_test_collision.py <destination> [--vcs-ref REF]", file=sys.stderr
        )
        return 2
    raw_destination, vcs_ref = parsed
    destination = Path(raw_destination).resolve()
    collisions = find_collisions(destination, vcs_ref=vcs_ref)
    if not collisions:
        return 0
    print("A file already occupies a path this template reserves for its own consumer tests:")
    for relative in collisions:
        print(f"  {relative}")
    print(
        "Fix direction: move or rename the colliding file before running `copier update`; "
        f"the template owns every path under {_RESERVED_SUBTREE}/."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
