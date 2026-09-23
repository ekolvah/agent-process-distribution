#!/usr/bin/env python3
"""Group 0 of the `tasks` rule as one command: the gate, the branch, the Status, the provenance.

Usage: python skills/agent-process/scripts/start_change.py <change> --planner <Claude|Codex>
       --implementer <Claude|Codex>

The gate is exit codes, not prose the agent evaluates: `openspec/changes/<change>/
architect-review.json` is valid against architect-review.schema.json beside this skill and
its verdict is approve, and the
tracking issue — the number in the first `tracking issue <N>` token of `tasks.md` (Group 0),
which the propose run replaced — is an item of the repository's linked Project in `Planned`.
Otherwise exit 2 and nothing is created: on `rework` the verdict is named (apply the findings,
re-review); when the token still carries the placeholder or the issue is not `Planned`,
`propose run not finished` names the tail to run (`create_tracking_issue.py`). Then
`gh issue develop -c <N> --name <change>` (the branch starts from the default branch, `--base`
unset), `set_status <N> "In Progress"` and one comment on the issue, `planner: <p>;
implementer: <i>`. A `gh` failure is exit 1 with its stderr; an unresolved Project name is
exit 2, as `set_status` maps it; a failure once the branch exists names the steps left —
`gh issue develop` creates the remote branch before it checks it out, so its failure is
followed by `git ls-remote --heads origin <change>`: listed, the steps start with
`git switch <change>`; empty, `no branch was created` and the run is repeated.

Run once per change: a run interrupted before the archive resumes with `git switch <change>`
and the steps the failure named, after the archive from `gh pr view <change>` — never with a
second `start_change` (the link of the branch moves to the PR once it opens, so a second run
sees the issue in `In Progress` and stops).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from set_status import Gh, _linked_project, _repo, run_gh, set_status

ROOT = Path.cwd()
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA = SCRIPT_DIR.parent / "architect-review.schema.json"
CARRIERS = ("Claude", "Codex")
PLACEHOLDER = "tracking issue <N>"
_TOKEN = re.compile(r"tracking issue (<N>|\d+)")
NOT_FINISHED = (
    "propose run not finished: run its tail "
    f'(python "{SCRIPT_DIR / "create_tracking_issue.py"}" '
    "{change} --priority <High|Medium|Low>) first"
)


def verdict(change_dir: Path) -> str:
    """The verdict of architect-review.json once the file is valid against the skill's schema;
    every validation error is named. `jsonschema` is imported here, so the scripts that only
    import this module run without it; its absence is an error, never a pass."""
    try:
        import jsonschema
    except ModuleNotFoundError as exc:
        raise ValueError(f"architect review not validated: {exc}") from exc
    review = change_dir / "architect-review.json"
    if not review.is_file():
        raise FileNotFoundError(f"no architect review at {review}")
    data = json.loads(review.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(data),
        key=lambda error: [str(part) for part in error.path],
    )
    if errors:
        raise ValueError(
            "\n".join(f"{review}: {error.json_path}: {error.message}" for error in errors)
        )
    return str(data["verdict"])


def tracking_issue(tasks_md: Path) -> int | None:
    """The `tracking issue <N>` token of tasks.md: `None` while it carries the placeholder, the
    number once the propose run wrote it. The first token in the file decides — Group 0 is
    the first group — so the literal `<N>`, the whole token or another `tracking issue 9` in
    a later line (a test description, a quoted rule) is text. No token is a ValueError naming
    the convention."""
    match = _TOKEN.search(tasks_md.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(
            f"{tasks_md}: no `{PLACEHOLDER}` token and no `tracking issue <number>` — Group 0 of "
            "tasks.md carries the token and the propose run replaces it"
        )
    return None if match.group(1) == "<N>" else int(match.group(1))


def _status(gh: Gh, number: int) -> str:
    """The Status name of the issue's item on the linked Project — the one `set_status`
    writes, matched by title (`gh issue view --json projectItems` prints one entry per
    Project with the Project's `title`); `none` when the issue is no item of it."""
    owner, name, projects = _repo(gh)
    linked = str(_linked_project(owner, name, projects)["title"])
    out = gh(["gh", "issue", "view", str(number), "--json", "projectItems"])
    try:
        items = json.loads(out)["projectItems"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"`gh issue view {number} --json projectItems` returned {out!r}"
        ) from exc
    for item in items:
        if str(item.get("title")) == linked:
            return str((item.get("status") or {}).get("name") or "none")
    return "none"


def start_change(
    change: str, *, planner: str, implementer: str, gh: Gh = run_gh, root: Path = ROOT
) -> int:
    change_dir = root / "openspec" / "changes" / change
    line = verdict(change_dir)
    if line != "approve":
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
    # Once the remote branch exists a failure names the steps left, so the person completes
    # them by hand — `start_change` is run once per change, never as a resume.
    body = f"planner: {planner}; implementer: {implementer}"
    left = [
        f"git switch {change}",
        f'python "{SCRIPT_DIR / "set_status.py"}" {number} "In Progress"',
        f'gh issue comment {number} --body "{body}"',
    ]
    exists = f"the branch {change} exists — finish by hand"
    try:
        # Creates the remote branch, then checks it out: a failed checkout leaves the branch,
        # which `ls-remote` shows; a failed create leaves nothing.
        gh(["gh", "issue", "develop", "-c", str(number), "--name", change])
    except RuntimeError as exc:
        if not gh(["git", "ls-remote", "--heads", "origin", change]).strip():
            raise RuntimeError(f"{exc}; no branch was created") from exc
        raise RuntimeError(f"{exc}; {exists}: {'; then '.join(left)}") from exc
    left.pop(0)
    try:
        set_status(number, "In Progress", gh=gh)
        left.pop(0)
        gh(["gh", "issue", "comment", str(number), "--body", body])
    except (KeyError, ValueError, RuntimeError) as exc:
        raise type(exc)(f"{exc}; {exists}: {'; then '.join(left)}") from exc
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
