"""The installation PR's steps of `init.py` (design D4 of install-links-an-issue); not a
command. `onboarding-branch` runs before the file steps, preceded by `onboarding-root` in a
repository with no commits, and commit, issue, push and PR after the Project steps. They exist only when a file step is planned or the checkout is on the
installation branch, are classified from git and `gh` reads, and re-read in `apply`."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable

from steps import InstallError, Step

ONBOARDING = ("onboarding-commit", "onboarding-issue", "onboarding-push", "onboarding-pr")


@dataclass
class Target:
    """Where the installation PR goes, the process boundary `init` passes — `git` runs in the
    consumer's root, `gh` checks its exit code, `gh_json` parses its output — the issue the
    PR closes once that is known, and whether `origin` has no commits yet."""

    version: str
    repo: str
    default: str
    git: Callable[..., subprocess.CompletedProcess[str]]
    gh: Callable[..., subprocess.CompletedProcess[str]]
    gh_json: Callable[..., Any]
    issue: int | None = None
    empty: bool = False

    @property
    def branch(self) -> str:
        return f"agent-process/install-{self.version}"

    @property
    def title(self) -> str:
        return f"chore: install agent-process {self.version}"

    @property
    def issue_title(self) -> str:
        return f"Install agent-process {self.version}"

    def out(self, *args: str) -> str:
        done = self.git(*args)
        if done.stdout is None:
            raise InstallError(f"`git {args[0]}` output not captured")
        return done.stdout.strip()

    def remote_head(self) -> str | None:
        """The commit the branch points to on `origin`, read live, or None when absent."""
        ref = f"refs/heads/{self.branch}"
        for line in self.out("ls-remote", "--heads", "origin", ref).splitlines():
            sha, _, name = line.partition("\t")
            if name == ref:
                return sha
        return None

    def listed(self, *args: str) -> list[dict[str, Any]]:
        data = self.gh_json(*args[:2], "--repo", self.repo, *args[2:])
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise InstallError(f"`gh {args[0]} {args[1]}` printed an unexpected shape: {data}")
        return data

    def open_issues(self) -> list[int]:
        """The open issues titled exactly so, from the list API (no search-index lag)."""
        fields = ("--state", "open", "--json", "number,title", "--limit", "1000")
        listed = self.listed("issue", "list", *fields)
        try:
            return [int(i["number"]) for i in listed if i.get("title") == self.issue_title]
        except (KeyError, TypeError, ValueError):
            raise InstallError(f"`gh issue list` printed an unexpected shape: {listed}") from None


def _blocked(detail: str) -> tuple[list[Step], list[Step]]:
    return [Step("onboarding-branch", "conflict", detail)], []


def plan(to: Target, planned: bool) -> tuple[list[Step], list[Step]]:
    """The branch step (after `onboarding-root` in a repository with no commits), which runs
    before the file steps, and the four that run after the Project steps; none when no file
    step is planned and the checkout is not on the branch."""
    current = to.out("branch", "--show-current")
    if current == to.branch:
        return _on_branch(to, planned)
    if not planned:
        return [], []
    cause = _empty_start(to) if to.empty else _unsafe_start(to, current)
    if cause:
        return _blocked(cause)
    committing = _commit_step(to, planned)
    after = [committing, _issue_step(to), _push_step(to, committing), _pr_step(to, [])]
    if to.empty:
        return [_root_step(to), _branch_step(to)], after
    return [_branch_step(to)], after


def _branch_step(to: Target) -> Step:
    """The branch from the checkout, or from the initial commit `onboarding-root` fetched."""
    if to.empty:
        args = ("switch", "--no-track", "-c", to.branch, f"origin/{to.default}")
        detail = f"{to.branch} from the initial commit"
    else:
        args, detail = ("switch", "-c", to.branch), f"{to.branch} from {to.default}"

    def switch() -> bool:
        to.git(*args)
        return True

    return Step("onboarding-branch", "planned", detail, switch)


def _root_step(to: Target) -> Step:
    """A commit with no files on the default branch of a repository with none, the base the PR
    needs (#271). The push has no force, so a default branch pushed meanwhile rejects it."""

    def push_root() -> bool:
        # The worktree is clean, so the unborn checkout's index is the empty tree.
        root = to.out("commit-tree", to.out("write-tree"), "-m", "Initial commit")
        to.git("push", "--quiet", "origin", f"{root}:refs/heads/{to.default}")
        to.git("fetch", "--quiet", "origin", to.default)
        return True

    detail = f"an empty initial commit -> origin/{to.default}"
    return Step("onboarding-root", "planned", detail, push_root)


def _empty_start(to: Target) -> str | None:
    """Why a checkout cannot start a repository with no commits. Its branch is not compared
    with the settings' name: an unborn branch has nothing to lose, and cannot switch to it."""
    if to.git("rev-parse", "--verify", "--quiet", "HEAD", check=False).returncode == 0:
        return (
            "`origin` has no commits and the checkout has; "
            f"`git push -u origin HEAD:{to.default}`, then rerun"
        )
    if to.out("status", "--porcelain", "--untracked-files=all"):
        return (
            "the worktree has changes and the repository has no commits; "
            "move them out of the worktree, then rerun"
        )
    return _branch_exists(to)


def _unsafe_start(to: Target, current: str) -> str | None:
    """Why a run off the branch cannot start it, naming the command that resolves it."""
    if to.git("rev-parse", "--verify", "--quiet", "HEAD", check=False).returncode != 0:
        return f"the checkout has no commits; `git pull origin {to.default}`, then rerun"
    if current != to.default:
        where = f"`{current}`" if current else "a detached HEAD"
        return f"on {where}, not `{to.default}`; `git switch {to.default}`, then rerun"
    if to.out("status", "--porcelain", "--untracked-files=all"):
        return "the worktree has changes; commit or `git stash` them, then rerun"
    return _branch_exists(to)


def _branch_exists(to: Target) -> str | None:
    local = to.git("rev-parse", "--verify", "--quiet", f"refs/heads/{to.branch}", check=False)
    if local.returncode == 0 or to.remote_head():
        return f"`{to.branch}` exists but is not checked out; `git switch {to.branch}`, then rerun"
    return None


def _on_branch(to: Target, planned: bool) -> tuple[list[Step], list[Step]]:
    """On the branch, its PRs decide: a merged one ends the onboarding, a closed one blocks."""
    fields = ("--head", to.branch, "--state", "all", "--json", "number,state,url")
    pulls = to.listed("pr", "list", *fields)
    if not any(pull.get("state") == "OPEN" for pull in pulls):
        merged = [pull.get("url") for pull in pulls if pull.get("state") == "MERGED"]
        if merged and planned:
            return _blocked(
                f"the PR {merged[0]} of `{to.branch}` is merged; `git switch {to.default}` "
                "and `git pull`, then rerun"
            )
        if merged:
            done = [Step(label, "unchanged", f"{merged[0]} merged") for label in ONBOARDING]
            return [Step("onboarding-branch", "unchanged", f"{merged[0]} merged")], done
        if pulls:
            return _blocked(
                f"the PR {pulls[0].get('url')} of `{to.branch}` was closed unmerged; "
                f"reopen it or remove `{to.branch}`"
            )
    committing = _commit_step(to, planned)
    after = [committing, _issue_step(to), _push_step(to, committing), _pr_step(to, pulls)]
    return [Step("onboarding-branch", "unchanged", to.branch)], after


def _commit_step(to: Target, planned: bool) -> Step:
    def commit() -> bool:
        to.git("add", "-A")
        # A planned file write can restore the committed bytes: re-read what is staged.
        if to.git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return False
        to.git("commit", "--quiet", "-m", to.title)
        return True

    step = Step("onboarding-commit", "planned", f"{to.title!r} on {to.branch}", commit)
    if planned or to.out("status", "--porcelain", "--untracked-files=all"):
        return step
    ahead = int(to.out("rev-list", "--count", f"origin/{to.default}..HEAD"))
    if ahead:
        return Step("onboarding-commit", "unchanged", f"{to.branch} is {ahead} ahead")
    detail = f"nothing to commit and `{to.branch}` is not ahead of `origin/{to.default}`"
    return Step("onboarding-commit", "conflict", detail)


def _issue_step(to: Target) -> Step:
    numbers = to.open_issues()
    if len(numbers) > 1:
        listed = ", ".join(f"#{number}" for number in numbers)
        return Step("onboarding-issue", "conflict", f"{listed} are titled {to.issue_title!r}")
    if numbers:
        to.issue = numbers[0]
        return Step("onboarding-issue", "unchanged", f"#{numbers[0]} {to.issue_title!r}")

    def open_issue() -> bool:
        body = (
            f"Install agent-process {to.version} with its `init.py`; "
            "the installation PR closes this issue."
        )
        create = ("create", "--repo", to.repo, "--title", to.issue_title, "--body", body)
        to.gh("issue", *create)
        found = to.open_issues()
        if len(found) != 1:
            raise InstallError(f"expected one open issue {to.issue_title!r} in {to.repo}: {found}")
        to.issue = found[0]
        return True

    return Step("onboarding-issue", "planned", f"{to.issue_title!r} in {to.repo}", open_issue)


def _push_step(to: Target, committing: Step) -> Step:
    def push() -> bool:
        if to.remote_head() == to.out("rev-parse", "HEAD"):
            return False
        to.git("push", "--quiet", "-u", "origin", to.branch)
        return True

    step = Step("onboarding-push", "planned", f"{to.branch} -> origin", push)
    if committing.status == "planned":
        return step
    head = to.out("rev-parse", "HEAD")
    if to.remote_head() == head:
        return Step("onboarding-push", "unchanged", f"origin/{to.branch} at {head[:12]}")
    return step


def _pr_step(to: Target, pulls: list[dict[str, Any]]) -> Step:
    opened = [pull for pull in pulls if pull.get("state") == "OPEN"]
    if opened:
        return Step("onboarding-pr", "unchanged", str(opened[0].get("url")))
    step = Step("onboarding-pr", "planned", f"{to.branch} -> {to.default}, closing the issue")

    def open_pr() -> bool:
        if to.issue is None:
            raise InstallError("the installation PR has no issue to close")
        body = f"Closes #{to.issue}\n\nInstalls agent-process {to.version} with its `init.py`."
        refs = ("--base", to.default, "--head", to.branch)
        create = ("create", "--repo", to.repo, *refs, "--title", to.title, "--body", body)
        to.gh("pr", *create)
        listed = to.listed(
            "pr", "list", "--head", to.branch, "--state", "open", "--json", "number,url"
        )
        if len(listed) != 1:
            raise InstallError(f"expected one open PR of `{to.branch}` in {to.repo}: {listed}")
        step.detail = str(listed[0].get("url"))
        return True

    step.apply = open_pr
    return step


if __name__ == "__main__":
    sys.exit("onboarding.py is imported by init.py; run `agent-process init`")
