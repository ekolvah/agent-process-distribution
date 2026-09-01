#!/usr/bin/env python3
"""Fail visibly when a foreign file already occupies a reserved consumer test path.

    python .agent-process/scripts/check_consumer_test_collision.py <destination> [--vcs-ref REF]

Copier's own `--conflict {rej,inline}` only marks a conflict for a path it
previously tracked via a prior render's diff; a brand-new template path
colliding with pre-existing, unrelated content at that exact destination
path is invisible to it and would otherwise be silently overwritten by
`copier update`. This script reads `<destination>/.copier-answers.yml` for
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

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
sys.path.insert(0, _SCRIPT_DIR)
try:
    from adopt_agent_process import (
        _CLOSED_ROOT_FILES,
        _CLOSED_ROOT_PREFIXES,
        _MANAGED_FRAGMENT_TARGETS,
    )
finally:
    sys.path.remove(_SCRIPT_DIR)

_VOLATILE_ANSWER_KEYS = frozenset({"_src_path", "_commit"})


def _load_answers_file(destination: Path) -> tuple[str, str | None, dict[str, object]]:
    answers_path = destination / ".agent-process" / "copier-answers.yml"
    if not answers_path.is_file():
        raise FileNotFoundError(
            f"{answers_path} not found; {destination} was never rendered from this template."
        )
    data = yaml.safe_load(answers_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("_src_path"), str):
        raise ValueError(f"{answers_path} must record _src_path")
    src_path = data["_src_path"]
    previous_commit = data.get("_commit")
    if not isinstance(previous_commit, str):
        previous_commit = None
    answers = {key: value for key, value in data.items() if key not in _VOLATILE_ANSWER_KEYS}
    return src_path, previous_commit, answers


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


def _previously_rendered_contents(
    work: Path, src_path: str, answers: dict[str, object], previous_commit: str | None
) -> dict[str, bytes]:
    """Content the template rendered for each closed-root path at the consumer's last render.

    Without this, an ordinary release that legitimately changes an
    already-rendered closed-root file (e.g. `.github/workflows/ci.yml`) reads
    as a foreign collision, because the raw byte comparison never distinguishes
    it from a brand-new template path landing on pre-existing, unrelated
    content — the only case this scanner exists to catch (#57 fresh finding).
    Presence alone is not enough to exempt a path: a file the consumer
    overwrote with foreign content since that last render is still a genuine
    collision even though the template already owned that path, so callers
    must compare the destination's current bytes against what is returned
    here, not merely check membership.
    """
    if previous_commit is None:
        return {}
    try:
        previous_rendered = _render_current_template(work, src_path, answers, previous_commit)
    except RuntimeError:
        # The previous ref may be unresolvable (e.g. a shallow local clone);
        # fail toward still reporting every closed-root path as potentially
        # new rather than silently skipping a genuine collision.
        return {}
    return {
        path.relative_to(previous_rendered).as_posix(): path.read_bytes()
        for path in previous_rendered.rglob("*")
        if path.is_file()
    }


def find_collisions(destination: Path, *, vcs_ref: str | None = None) -> list[str]:
    """Closed-root paths already present at `destination` with foreign content."""
    src_path, previous_commit, answers = _load_answers_file(destination)
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        new_work = work / "new"
        old_work = work / "old"
        new_work.mkdir()
        old_work.mkdir()
        rendered = _render_current_template(new_work, src_path, answers, vcs_ref)
        previously_rendered = _previously_rendered_contents(
            old_work, src_path, answers, previous_commit
        )
        collisions = []
        for path in sorted(rendered.rglob("*")):
            if not path.is_file() or path.relative_to(rendered).as_posix().startswith(
                ".agent-process/"
            ):
                continue
            relative = path.relative_to(rendered).as_posix()
            if relative not in _CLOSED_ROOT_FILES and not relative.startswith(
                _CLOSED_ROOT_PREFIXES
            ):
                continue
            if relative in _MANAGED_FRAGMENT_TARGETS:
                # ADR-0019: a consumer's own content coexists with the process's
                # delimited fragment in the same file, so these never collide on
                # differing bytes — they merge instead (adopt_agent_process._path_conflicts
                # applies the same exemption).
                continue
            existing = destination / relative
            if not existing.is_file() or existing.read_bytes() == path.read_bytes():
                continue
            if existing.read_bytes() == previously_rendered.get(relative):
                # Untouched since the consumer's last render; the difference
                # from the new render is an ordinary upstream content change,
                # not foreign content colliding with a newly introduced path.
                continue
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
    print("A file already occupies a closed root path this template reserves:")
    for relative in collisions:
        print(f"  {relative}")
    print(
        "Fix direction: move or rename the colliding file before running `copier update`; "
        "the template owns the documented closed root set."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
