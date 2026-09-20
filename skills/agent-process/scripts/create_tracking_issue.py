#!/usr/bin/env python3
"""The tail of the propose run as one command: the tracking issue in `Planned` with its priority.

Usage: python skills/agent-process/scripts/create_tracking_issue.py <change> [--priority <High|Medium|Low>]

`tasks.md` of the change decides the branch through its `tracking issue <N>` token (Group 0;
the same read as `start_change`): while it carries the placeholder, `--priority` is required
— `gh issue create --title "<change>" --body-file openspec/changes/<change>/proposal.md`, the
number (the last path segment of the printed URL; `gh issue create` has no `--json`) is written
into the token at once, and only then `set_status <N> "Planned" --priority <P>`, so a failure
after the create leaves the number in tasks.md and a re-run lands on the existing-issue branch
instead of creating a second issue. When the token already carries a number, `--priority` is
refused (the priority was set at creation) and the call is `set_status <N> "Planned"` alone
(Todo → Planned). A `gh` failure is exit 1 with its stderr; an unresolved Project name is exit
2, as `set_status` maps it; on the create branch both messages end with the resume command.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from set_status import Gh, run_gh, set_status
from start_change import PLACEHOLDER, ROOT, tracking_issue

PRIORITIES = ("High", "Medium", "Low")


def _issue_number(create_output: str) -> int:
    """`gh issue create` prints the issue URL; its last path segment is the number."""
    last = create_output.strip().splitlines()[-1] if create_output.strip() else ""
    tail = last.rstrip("/").rsplit("/", 1)[-1]
    if not tail.isdigit():
        raise RuntimeError(f"`gh issue create` printed no issue URL: {create_output!r}")
    return int(tail)


def create_tracking_issue(
    change: str, *, priority: str | None, gh: Gh = run_gh, root: Path = ROOT
) -> int:
    change_dir = root / "openspec" / "changes" / change
    tasks_md = change_dir / "tasks.md"
    number = tracking_issue(tasks_md)
    if number is not None:
        if priority is not None:
            print(
                f"priority is set at creation; the issue exists (#{number} in tasks.md) — "
                "run without --priority",
                file=sys.stderr,
            )
            return 2
        set_status(number, "Planned", gh=gh)
        print(f"ok: issue #{number} Planned")
        return 0
    if priority is None:
        print(
            "priority required: the change has no tracking issue yet — "
            f"--priority <{'|'.join(PRIORITIES)}>",
            file=sys.stderr,
        )
        return 2
    out = gh(
        [
            "gh",
            "issue",
            "create",
            "--title",
            change,
            "--body-file",
            str(change_dir / "proposal.md"),
        ]
    )
    number = _issue_number(out)
    text = tasks_md.read_text(encoding="utf-8")
    tasks_md.write_text(
        re.sub(re.escape(PLACEHOLDER), f"tracking issue {number}", text, count=1), encoding="utf-8"
    )
    resume = (
        f"python skills/agent-process/scripts/set_status.py {number} Planned --priority {priority}"
    )
    try:
        set_status(number, "Planned", priority=priority, gh=gh)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise type(exc)(f"{exc}; issue #{number} is in tasks.md — resume with `{resume}`") from exc
    print(f"ok: issue #{number} created, Planned, priority {priority}\n{out.strip()}")
    return 0


def main(argv: list[str] | None = None, *, gh: Gh = run_gh, root: Path = ROOT) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("change", help="change name under openspec/changes/")
    parser.add_argument(
        "--priority", choices=PRIORITIES, help="the priority asked from the person (new issue only)"
    )
    ns = parser.parse_args(argv)
    try:
        code = create_tracking_issue(ns.change, priority=ns.priority, gh=gh, root=root)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
