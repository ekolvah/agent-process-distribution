"""Extract the one review contract shared by both review carriers."""

from __future__ import annotations

import argparse
from pathlib import Path


HEADING = "## Code Review Rules"


def extract_review_prompt(text: str) -> str:
    """Return the non-empty Code Review Rules section, or raise a useful error."""
    marker = f"{HEADING}\n"
    if marker not in text:
        raise ValueError(f"missing {HEADING!r} in AGENTS.md")
    section = text.split(marker, 1)[1].split("\n## ", 1)[0].strip()
    if not section:
        raise ValueError(f"{HEADING!r} in AGENTS.md is empty")
    return section


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Print AGENTS.md Code Review Rules.")
    parser.add_argument("path", nargs="?", default="AGENTS.md")
    options = parser.parse_args(argv)
    try:
        print(extract_review_prompt(Path(options.path).read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: cannot extract review prompt: {exc}") from exc


if __name__ == "__main__":
    main()
