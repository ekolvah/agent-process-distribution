#!/usr/bin/env python3
"""Group 0 of the `tasks` rule as one command: the gate, the branch, the Status, the provenance.

Usage: python skills/agent-process/scripts/start_change.py <change> --planner Claude
       --implementer Claude

First, a project whose `openspec/config.yaml` does not record this skill's release exits 2
with `release drift` and the fix (`init.release_drift`; the publisher's own checkout is exempt).
The gate is exit codes, not prose the agent evaluates: `openspec/changes/<change>/
architect-review.json` is valid against architect-review.schema.json beside this skill and
its verdict is approve, and the
tracking issue — the number in the first `tracking issue <N>` token of `tasks.md` (Group 0),
which the propose run replaced — is an item of the repository's linked Project in `Planned`.
Otherwise exit 2 and nothing is created: on `rework` the verdict is named (apply the findings,
re-review); when the token still carries the placeholder or the issue is not `Planned`,
`propose run not finished` names the tail to run (`create_tracking_issue.py`). A session that
leads another issue exits 2 there too; otherwise it is bound to this one (`session_binding`).

Then `git worktree list --porcelain` names the main worktree (its first entry; a failed
listing is exit 1 before any branch exists), the line `/.claude/worktrees/` is appended to
the repository's `info/exclude` unless present (`git rev-parse --git-path info/exclude`; a
failure is exit 1 before any branch exists), `git remote prune origin` drops the refs to
branches gone on `origin`, and every local branch whose PR is merged and whose tip is that
PR's `headRefOid` is deleted (`git branch -D`, `deleted: <branch>`) once its worktree under
`.claude/worktrees/`, if any, is removed when clean (`removed: <path>`); a differing tip, a
dirty worktree or a failure is kept and named on stderr (`kept: <branch|path|origin> —
<reason>`), never a stop. A branch checked out in the main worktree, in the one containing
the cwd or outside `.claude/worktrees/`, and any whose PR is open, closed or absent, is left.
Then `gh issue develop <N> --name <change>` creates the linked
branch without checkout (from the default branch, `--base` unset), `git fetch origin
<change>` and `git worktree add --track -b <change> <main>/.claude/worktrees/<change>
origin/<change>` carry it in its own worktree, `openspec/changes/<change>/` moves there from
the cwd, its `start_change` task is ticked and the plan committed there (`chore: plan
<change>`, not pushed), then `set_status <N> "In Progress"` and one comment on the issue,
`planner: <p>; implementer: <i>`. The checkout it runs in keeps its branch and every other file. A `gh`
failure is exit 1 with its stderr; an unresolved Project name is exit 2, as `set_status` maps
it; a failure once the branch exists names the steps left, from the one that failed — a
failed `gh issue develop` is followed by `git ls-remote --heads origin <change>`: listed, the
steps start with `git fetch`; empty, `no branch was created` and the run is repeated.

Run once per change: the session enters the worktree the `ok:` line names (`EnterWorktree`
with its path) and runs every later task there. A run interrupted before the archive resumes
by entering the same worktree and the steps the failure named, after the archive from `gh pr
view <change>` — never with a second `start_change` (the link of the branch moves to the PR
once it opens, so a second run sees the issue in `In Progress` and stops).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from archive_change import mark_own_task
from init import release_drift
from session_binding import PLACEHOLDER, bind, ledger_path, tracking_issue
from set_status import Gh, _json, _linked_project, _repo, run_gh, set_status

ROOT = Path.cwd()
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA = SCRIPT_DIR.parent / "architect-review.schema.json"
CARRIERS = ("Claude",)
WORKTREES = Path(".claude") / "worktrees"
NO_PR = "no pull requests found"
NOT_FINISHED = (
    "propose run not finished: run its tail "
    f'(python "{SCRIPT_DIR / "create_tracking_issue.py"}" '
    "{change} --area <name>) first"
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


def first_worktree(listing: str) -> Path:
    """The path of the first entry of `git worktree list --porcelain`: the main worktree."""
    for line in listing.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree "))
    raise RuntimeError(f"`git worktree list --porcelain` listed no worktree: {listing!r}")


def exclude_worktrees(main: Path, gh: Gh) -> None:
    """Keep `.claude/worktrees/` out of the main worktree's status: append its line to the
    repository's `info/exclude` — one file per clone, never committed — unless a line equals
    it. git resolves the file, so a linked worktree's cwd or a separate git dir writes the
    shared one."""
    line = f"/{WORKTREES.as_posix()}/"
    exclude = Path(
        gh(
            [
                "git",
                "-C",
                str(main),
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "info/exclude",
            ]
        ).strip()
    )
    try:
        text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        if line in text.splitlines():
            return
        exclude.parent.mkdir(parents=True, exist_ok=True)
        sep = "" if not text or text.endswith("\n") else "\n"
        with exclude.open("a", encoding="utf-8") as f:
            f.write(f"{sep}{line}\n")
    except OSError as exc:
        raise RuntimeError(f"cannot add `{line}` to {exclude}: {exc}") from exc


def prune_merged_changes(main: Path, root: Path, gh: Gh) -> None:
    """Delete the local branches whose PR is merged and whose tip is that PR's head commit (the
    merge is the person's, after the run that made them; the head stays fetchable at
    `refs/pull/<N>/head`), first removing the clean worktree under `<main>/.claude/worktrees/`
    a branch is checked out in, and prune `origin`'s refs to deleted branches. A differing tip,
    a dirty worktree or a failure is a `kept:` line on stderr, never a stop. A branch checked
    out elsewhere — the main worktree, the one containing `root` (the cwd, whose plan is about
    to move) — and every one whose PR is not merged or absent are left."""
    try:
        gh(["git", "remote", "prune", "origin"])
    except RuntimeError as exc:
        print(f"kept: origin — {exc}", file=sys.stderr)
    base = (main / WORKTREES).resolve()
    here = root.resolve()
    try:
        refs = gh(
            [
                "git",
                "for-each-ref",
                "refs/heads",
                "--format=%(refname:short)%00%(objectname)%00%(worktreepath)",
            ]
        )
    except RuntimeError as exc:
        print(f"kept: local branches — {exc}", file=sys.stderr)
        return
    for line in refs.splitlines():
        branch, tip, listed = line.split("\0")
        path = Path(listed).resolve() if listed else None
        if path is None or (path.parent == base and not here.is_relative_to(path)):
            _prune_branch(branch, tip, path, gh)


def _prune_branch(branch: str, tip: str, path: Path | None, gh: Gh) -> None:
    """`prune_merged_changes` for one branch, checked out in `path` or in no worktree."""
    try:
        pr = _json(gh, ["gh", "pr", "view", branch, "--json", "state,headRefOid"])
        if pr["state"] != "MERGED":
            return
        if pr["headRefOid"] != tip:
            print(f"kept: {branch} — tip is not the merged PR's head", file=sys.stderr)
            return
        if path is not None:
            if gh(["git", "-C", str(path), "status", "--porcelain"]).strip():
                print(f"kept: {path} — uncommitted changes", file=sys.stderr)
                return
            gh(["git", "worktree", "remove", str(path)])
            print(f"removed: {path}")
    except RuntimeError as exc:
        if NO_PR not in str(exc):
            print(f"kept: {path or branch} — {exc}", file=sys.stderr)
        return
    except (KeyError, TypeError) as exc:
        print(f"kept: {branch} — unreadable PR: {exc!r}", file=sys.stderr)
        return
    try:
        gh(["git", "branch", "-D", branch])
    except RuntimeError as exc:
        print(f"kept: {branch} — {exc}", file=sys.stderr)
        return
    print(f"deleted: {branch}")


def main_worktree(root: Path, gh: Gh) -> Path:
    """The main worktree — the worktree base, since a session that carried the previous
    change may still run inside that change's worktree — once its `.claude/worktrees/` is
    excluded from its status and pruned of merged changes."""
    main = first_worktree(gh(["git", "worktree", "list", "--porcelain"])).resolve()
    exclude_worktrees(main, gh)
    prune_merged_changes(main, root, gh)
    return main


def commit_plan(change: str, worktree: Path, gh: Gh) -> None:
    """Tick the `start_change` task of the moved plan and commit the plan in `worktree`
    (not pushed): its first commit carries the Group 0 tick, as every later group's commit
    carries its own."""
    mark_own_task(worktree / "openspec" / "changes" / change / "tasks.md", "start_change", change)
    gh(["git", "-C", str(worktree), "add", f"openspec/changes/{change}"])
    gh(["git", "-C", str(worktree), "commit", "-m", f"chore: plan {change}"])


def start_change(
    change: str, *, planner: str, implementer: str, gh: Gh = run_gh, root: Path = ROOT
) -> int:
    if drift := release_drift(root, SCRIPT_DIR):
        print(drift, file=sys.stderr)
        return 2
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
    bind(number, environ=os.environ, ledger=lambda: ledger_path(gh, root))
    worktree = main_worktree(root, gh) / WORKTREES / change
    source = root / "openspec" / "changes" / change
    target = worktree / "openspec" / "changes" / change
    # Once the remote branch exists a failure names the steps left, so the person completes
    # them by hand — `start_change` is run once per change, never as a resume.
    body = f"planner: {planner}; implementer: {implementer}"
    left = [
        f"git fetch origin {change}",
        f'git worktree add --track -b {change} "{worktree}" origin/{change}',
        f'move "{source}" to "{target}"',
        f'tick the `start_change` task of "{target / "tasks.md"}", '
        f'git -C "{worktree}" add openspec/changes/{change} and '
        f'git -C "{worktree}" commit -m "chore: plan {change}"',
        f'python "{SCRIPT_DIR / "set_status.py"}" {number} "In Progress"',
        f'gh issue comment {number} --body "{body}"',
    ]
    exists = f"the branch {change} exists — finish by hand"
    try:
        # Creates the remote branch only (no `-c`): the checkout it runs in keeps its branch.
        # A failure after the create leaves the branch, which `ls-remote` shows.
        gh(["gh", "issue", "develop", str(number), "--name", change])
    except RuntimeError as exc:
        if not gh(["git", "ls-remote", "--heads", "origin", change]).strip():
            raise RuntimeError(f"{exc}; no branch was created") from exc
        raise RuntimeError(f"{exc}; {exists}: {'; then '.join(left)}") from exc
    try:
        gh(["git", "fetch", "origin", change])
        left.pop(0)
        gh(["git", "worktree", "add", "--track", "-b", change, str(worktree), f"origin/{change}"])
        left.pop(0)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)
        left.pop(0)
        commit_plan(change, worktree, gh)
        left.pop(0)
        set_status(number, "In Progress", gh=gh)
        left.pop(0)
        gh(["gh", "issue", "comment", str(number), "--body", body])
    except OSError as exc:
        raise RuntimeError(f"{exc}; {exists}: {'; then '.join(left)}") from exc
    except (KeyError, ValueError, RuntimeError) as exc:
        raise type(exc)(f"{exc}; {exists}: {'; then '.join(left)}") from exc
    print(
        f"ok: {change} on issue #{number} — worktree {worktree} (enter it), "
        "plan committed, In Progress, provenance posted"
    )
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
