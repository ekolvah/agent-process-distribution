"""Edit-time lint: the project's `pre-commit`-stage hooks run on the file just edited.

Driven through the CLI only, as the plugin hook runs it: `post-edit` with the PostToolUse
payload on stdin, the project as the working directory. A failing run exits 2 with its output
on stderr (Claude Code shows it to the agent; the edit already happened); a passing run and a
payload without a path are silent; a `pre-commit` that cannot run is a visible marker.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.publisher.delivery_fakes import SKILL_SCRIPTS
from tests.publisher.init_harness import git
from tests.publisher.lint_harness import FINDING, PRE_PUSH, edit_payload, lint_repo, write_config

_SCRIPT = SKILL_SCRIPTS / "edit_lint.py"


def _run(
    args: list[str], cwd: Path, stdin: str = "", env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        cwd=cwd,
        input=stdin,
        env=env,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _edit(repo: Path) -> str:
    return json.dumps(edit_payload(repo / "a.py"))


def test_commit_stage_finding_reaches_the_agent(tmp_path: Path) -> None:
    """Scenario: Commit-stage finding — exit 2, the hook's output on stderr."""
    repo = lint_repo(tmp_path / "repo", FINDING)
    result = _run(["post-edit"], repo, _edit(repo))
    assert result.returncode == 2, result.stderr
    assert "finding:" in result.stderr
    assert "a.py" in result.stderr


def test_only_pre_push_hooks_run_nothing(tmp_path: Path) -> None:
    """Scenario: Only pre-push hooks declared — exit 0, no output, no pre-push hook runs."""
    repo = lint_repo(tmp_path / "repo", PRE_PUSH)
    result = _run(["post-edit"], repo, _edit(repo))
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert not (repo / "ran").exists()


def _edit_in(path: Path, text: str = "a = 1\n") -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return json.dumps(edit_payload(path))


@pytest.mark.parametrize("case", ["allowed", "other"])
def test_worktree_file_uses_the_worktree_root(tmp_path: Path, case: str) -> None:
    """Scenario: Worktree file — run from the main checkout, the root-anchored `exclude`
    applies to the worktree's file, and a file it does not exclude still reports."""
    repo = lint_repo(tmp_path / "repo", {**FINDING, "exclude": "^allowed/"})
    worktree = tmp_path / "wt"
    git("worktree", "add", "-q", str(worktree), cwd=repo)
    result = _run(["post-edit"], repo, _edit_in(worktree / case / "x.md"))
    if case == "allowed":
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    else:
        assert result.returncode == 2, result.stderr
        assert "finding:" in result.stderr


def test_worktree_branch_config_runs(tmp_path: Path) -> None:
    """Scenario: Worktree branch config — the branch's `pre-commit`-stage hooks run."""
    repo = lint_repo(tmp_path / "repo", PRE_PUSH)
    worktree = tmp_path / "wt"
    git("worktree", "add", "-q", "-b", "lint-rules", str(worktree), cwd=repo)
    branch = {
        **FINDING,
        "id": "branch",
        "name": "branch",
        "entry": FINDING["entry"].replace("finding:", "branch:"),
    }
    write_config(worktree, branch)
    git("commit", "-q", "-am", "branch lint rules", cwd=worktree)
    result = _run(["post-edit"], repo, json.dumps(edit_payload(worktree / "a.py")))
    assert result.returncode == 2, result.stderr
    assert "branch:" in result.stderr


@pytest.mark.parametrize("case", ["no-repo", "git-dir", "not-adopted"])
def test_file_outside_adopted_repository_is_silent(tmp_path: Path, case: str) -> None:
    """Scenario: File outside an adopted repository — exit 0, no output."""
    repo = lint_repo(tmp_path / "repo", FINDING)
    if case == "no-repo":
        payload = _edit_in(tmp_path / "scratchpad" / "pr-body.md")
    elif case == "git-dir":
        payload = json.dumps(edit_payload(repo / ".git" / "info" / "exclude"))
    else:
        other = lint_repo(tmp_path / "other", FINDING, adopted=False)
        payload = json.dumps(edit_payload(other / "a.py"))
    result = _run(["post-edit"], repo, payload)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("case", ["dubious", "extension", "gitfile"])
def test_git_failure_inside_a_repository_is_visible(tmp_path: Path, case: str) -> None:
    """Scenario: Git fails inside a repository — a marker carrying git's message, exit 2."""
    repo = lint_repo(tmp_path / "repo", FINDING)
    env, payload = None, _edit(repo)
    if case == "dubious":
        # A `safe.directory = *` overrides the ownership check; the GitHub runner image sets
        # it in its system config.
        empty = tmp_path / "empty.gitconfig"
        empty.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(empty),
        }
        expected = "dubious ownership"
    elif case == "extension":
        git("config", "core.repositoryformatversion", "1", cwd=repo)
        git("config", "extensions.zzz", "true", cwd=repo)
        expected = "zzz"
    else:
        gitfile = repo / "removed" / ".git"
        gitfile.parent.mkdir()
        gitfile.write_text(f"gitdir: {(tmp_path / 'missing').as_posix()}\n", encoding="utf-8")
        payload = _edit_in(repo / "removed" / "a.py")
        # git for Windows names the missing gitdir; git on Linux prints `(null)` in its place.
        expected = "fatal: not a git repository: "
    result = _run(["post-edit"], repo, payload, env)
    assert result.returncode == 2, result.stderr
    assert "edit-time lint is not active:" in result.stderr
    assert expected in result.stderr


@pytest.mark.parametrize("case", ["no-pre-commit", "no-config"])
def test_pre_commit_that_cannot_run_is_visible(tmp_path: Path, case: str) -> None:
    """Scenarios: pre-commit missing, Linter cannot run — a marker naming the cause, exit 2."""
    env = None
    if case == "no-pre-commit":
        repo = lint_repo(tmp_path / "repo", FINDING)
        empty = tmp_path / "empty"
        empty.mkdir()
        env = {**os.environ, "PATH": str(empty)}
    else:
        repo = lint_repo(tmp_path / "repo")
    result = _run(["post-edit"], repo, _edit(repo), env)
    assert result.returncode == 2, result.stderr
    if case == "no-pre-commit":
        assert "pre-commit" in result.stderr
        assert "not active" in result.stderr
    else:
        assert ".pre-commit-config.yaml" in result.stderr


@pytest.mark.parametrize("stdin", ["", "not json", "{}", json.dumps({"tool_input": {}})])
def test_payload_without_path_is_silent(tmp_path: Path, stdin: str) -> None:
    """A payload bug must not red every edit: exit 0, no output."""
    repo = lint_repo(tmp_path / "repo", FINDING)
    result = _run(["post-edit"], repo, stdin)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("args", [[], ["on-edit"]])
def test_unknown_subcommand_prints_usage(tmp_path: Path, args: list[str]) -> None:
    """Broken wiring is visible: usage on stderr, exit 2."""
    repo = lint_repo(tmp_path / "repo", FINDING)
    result = _run(args, repo, _edit(repo))
    assert result.returncode == 2
    assert "usage" in result.stderr
