"""The readings of an `init` run the installer tests share: the git state, the kind of each
`gh` command the runner logged, the pushes and the `manual` rows."""

from __future__ import annotations

from pathlib import Path

from tests.publisher.init_harness import OWNER, REPO_NAME, Runner, Sandbox, git


def _refs(path: Path) -> str:
    return git("for-each-ref", "--format=%(refname) %(objectname)", cwd=path)


def _git_state(sb: Sandbox) -> tuple[str, str, str]:
    """The consumer's refs and HEAD, and `origin`'s refs. HEAD is read as written, so that an
    unborn one is a state too."""
    head = (sb.root / ".git" / "HEAD").read_text(encoding="utf-8")
    return _refs(sb.root), head, _refs(sb.origin)


AREA_WRITES = (
    "updateProjectV2Field(",
    "createProjectV2View(",
    "updateProjectV2View(",
    "deleteProjectV2View(",
)


POST_MERGE_WRITES = {
    "rulesets": "ruleset",
    "collaborators/": "collaborator",
    "user/repository_invitations/": "accept",
}


def _post_merge_write(args: list[str]) -> str | None:
    if args[0] == "api" and "-X" in args:
        endpoint = args[args.index("-X") + 2]
        (kind,) = [kind for part, kind in POST_MERGE_WRITES.items() if part in endpoint]
        return kind
    if args[:2] == ["api", "graphql"] and "updateProjectV2Collaborators" in args[-1]:
        return "project-role"
    return None


def _gh_kind(args: list[str]) -> str:
    """`read`, `copy`, `link`, `issue`, `pr`, `areas`, or a post-merge write: `ruleset`,
    `collaborator`, `accept`, `project-role`, `auto-merge`, `pr-edit`; any other `gh`
    command fails the test."""
    reads = (
        ["repo", "view"],
        ["issue", "list"],
        ["pr", "list"],
        ["pr", "view"],
        ["secret", "list"],
        ["variable", "list"],
        ["auth", "status"],
        ["auth", "token"],
    )
    if args[:2] in reads:
        return "read"
    if args[0] == "api" and args[1] != "graphql" and "-X" not in args:
        assert args[-1].startswith((f"repos/{OWNER}/{REPO_NAME}", "user/")), args
        return "read"
    written = _post_merge_write(args)
    if written:
        return written
    if args[:2] == ["api", "graphql"] and not any("mutation" in part for part in args):
        return "read"
    kinds = {
        ("project", "copy"): "copy",
        ("project", "link"): "link",
        ("issue", "create"): "issue",
        ("pr", "create"): "pr",
        ("pr", "edit"): "pr-edit",
        ("repo", "edit"): "auto-merge",
    }
    if tuple(args[:2]) in kinds:
        return kinds[args[0], args[1]]
    if args[:2] == ["api", "graphql"] and any(write in args[3] for write in AREA_WRITES):
        return "areas"
    raise AssertionError(f"gh command that is not a read or an allowed write: {args}")


def _pushes(runner: Runner) -> list[list[str]]:
    return [cmd for cmd in runner.log if Path(cmd[0]).stem.lower() == "git" and "push" in cmd]


PROCESS_CHECKS = ("agent-process / quality", "agent-review / agent-review")


def _manual_rows(out: str) -> list[str]:
    """The `manual` rows, asserted to end the output."""
    lines = out.splitlines()
    manual = [ln for ln in lines if ln.startswith("manual ")]
    assert lines[len(lines) - len(manual) :] == manual, lines
    return manual


def _row(manual: list[str], label: str) -> str:
    (row,) = [ln for ln in manual if ln.startswith(f"manual {label}: ")]
    return row
