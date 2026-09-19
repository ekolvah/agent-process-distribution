#!/usr/bin/env python3
"""Group 0 of the `tasks` rule as one command: the gate, the branch, the Status, the provenance.

Usage: python .agent-process/scripts/start_change.py <change> --planner <Claude|Codex>
       --implementer <Claude|Codex>

The gate is exit codes, not prose the agent evaluates: the first non-empty line under
`## Verdict` of `openspec/changes/<change>/architect-review.md` starts with `approve`, and the
tracking issue — the number in the `tracking issue <N>` token of Group 0 in `tasks.md`, which
the propose run replaced — is a Project item in `Planned`. Otherwise exit 2 and nothing is
created: on `rework` the verdict is named (apply the findings, re-review); when the token still
carries the placeholder or the issue is not `Planned`, `propose run not finished` names the tail
to run (`create_tracking_issue.py`). Then `gh issue develop -c <N> --name <change>` (the branch
starts from the default branch, `--base` unset), `set_status <N> "In Progress"` and one comment
on the issue, `planner: <p>; implementer: <i>`. A `gh` failure is exit 1 with its stderr; an
unresolved Project name is exit 2, as `set_status` maps it.

Run once per change: a run interrupted before the archive resumes with `git switch <change>`,
after it from `gh pr view <change>` — never with a second `start_change`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from scripts.set_status import Gh, run_gh, set_status
except ModuleNotFoundError:  # documented direct script entry point
    from set_status import Gh, run_gh, set_status

ROOT = Path(__file__).resolve().parents[2]
CARRIERS = ("Claude", "Codex")
PLACEHOLDER = "tracking issue <N>"
_NUMBER = re.compile(r"tracking issue (\d+)")
NOT_FINISHED = (
    "propose run not finished: run its tail "
    "(python .agent-process/scripts/create_tracking_issue.py {change} --priority <High|Medium|Low>) first"
)


def verdict(change_dir: Path) -> str:
    """The first non-empty line under `## Verdict` of architect-review.md."""
    review = change_dir / "architect-review.md"
    if not review.is_file():
        raise FileNotFoundError(f"no architect review at {review}")
    lines = review.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "## Verdict")
    except StopIteration:
        raise ValueError(f"{review}: no `## Verdict` section") from None
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        if line.strip():
            return line.strip()
    raise ValueError(f"{review}: `## Verdict` carries no line")


def tracking_issue(tasks_md: Path) -> int | None:
    """The `tracking issue <N>` token of tasks.md: `None` while it carries the placeholder, the
    number once the propose run wrote it. The literal `<N>` elsewhere in the file is text.
    Neither is a ValueError naming the convention."""
    text = tasks_md.read_text(encoding="utf-8")
    if PLACEHOLDER in text:
        return None
    match = _NUMBER.search(text)
    if match is None:
        raise ValueError(
            f"{tasks_md}: no `{PLACEHOLDER}` token and no `tracking issue <number>` — Group 0 of "
            "tasks.md carries the token and the propose run replaces it"
        )
    return int(match.group(1))


def _status(gh: Gh, number: int) -> str:
    """The Status name of the issue's Project item; `none` when it is no item."""
    out = gh(["gh", "issue", "view", str(number), "--json", "projectItems"])
    try:
        items = json.loads(out)["projectItems"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"`gh issue view {number} --json projectItems` returned {out!r}"
        ) from exc
    if not items:
        return "none"
    return str(items[0].get("status", {}).get("name") or "none")


def start_change(
    change: str, *, planner: str, implementer: str, gh: Gh = run_gh, root: Path = ROOT
) -> int:
    change_dir = root / "openspec" / "changes" / change
    line = verdict(change_dir)
    if not line.startswith("approve"):
        print(
            f"verdict: {line} — apply the findings, re-review (no delivery task runs)",
            file=sys.stderr,
        )
        return 2
    not_finished = NOT_FINISHED.format(change=change)
    try:
        number = tracking_issue(change_dir / "tasks.md")
    except ValueError as exc:
        print(f"{not_finished}; {exc}", file=sys.stderr)
        return 2
    if number is None:
        print(f"{not_finished}; tasks.md still carries `{PLACEHOLDER}`", file=sys.stderr)
        return 2
    status = _status(gh, number)
    if status != "Planned":
        print(f"{not_finished}; issue #{number} Status: {status}", file=sys.stderr)
        return 2
    gh(["gh", "issue", "develop", "-c", str(number), "--name", change])
    set_status(number, "In Progress", gh=gh)
    gh(
        [
            "gh",
            "issue",
            "comment",
            str(number),
            "--body",
            f"planner: {planner}; implementer: {implementer}",
        ]
    )
    print(f"ok: {change} on issue #{number} — branch {change}, In Progress, provenance posted")
    return 0


def main(argv: list[str] | None = None, *, gh: Gh = run_gh, root: Path = ROOT) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("change", help="change name under openspec/changes/")
    parser.add_argument(
        "--planner", choices=CARRIERS, required=True, help="carrier of the propose run"
    )
    parser.add_argument(
        "--implementer", choices=CARRIERS, required=True, help="carrier of this apply"
    )
    ns = parser.parse_args(argv)
    try:
        code = start_change(
            ns.change, planner=ns.planner, implementer=ns.implementer, gh=gh, root=root
        )
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
