"""RED contract: the closed-root collision scanner must not flag managed-fragment
targets, and must not flag an ordinary upstream update to a file the template
already owned.

`adopt_agent_process._path_conflicts` already exempts `AGENTS.md` and
`.gitignore` from raw-byte collision because a consumer's own content merges
with the process's delimited fragment instead of colliding with it (ADR-0019).
`find_collisions` scans the same closed root set but never applied that same
exemption, so any consumer with real custom content in either file gets a
false-positive collision report that blocks `copier update`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.check_consumer_test_collision import find_collisions


def test_find_collisions_exempts_managed_fragment_targets(
    rendered_default: Path, tmp_path: Path
) -> None:
    consumer = tmp_path / "consumer"
    shutil.copytree(rendered_default, consumer)
    (consumer / "AGENTS.md").write_text("# Product instructions\n", encoding="utf-8")
    (consumer / ".gitignore").write_text("product-cache/\n", encoding="utf-8")

    collisions = find_collisions(consumer, vcs_ref="HEAD")

    assert "AGENTS.md" not in collisions
    assert ".gitignore" not in collisions


def _git(args: list[str], *, cwd: Path) -> None:
    env = {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **env},
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_find_collisions_does_not_flag_an_ordinary_upstream_update(tmp_path: Path) -> None:
    """A closed-root path the template already owned as of the consumer's last
    render (recorded via `_commit`) must not be flagged just because the new
    release legitimately changed its content — that is an ordinary `copier
    update`, not foreign content colliding with a newly introduced template
    path (#57 fresh finding). A minimal synthetic template with two commits
    reproduces the finding's own example (`.github/workflows/ci.yml`
    legitimately changing between releases) without depending on how this
    repository's own self-recorded answers happen to look.
    """
    template_repo = tmp_path / "template_repo"
    workflows = template_repo / "template" / ".github" / "workflows"
    workflows.mkdir(parents=True)
    answers_dir = template_repo / "template" / ".agent-process"
    answers_dir.mkdir(parents=True)
    (template_repo / "copier.yml").write_text(
        "_subdirectory: template\n_answers_file: .agent-process/copier-answers.yml\n",
        encoding="utf-8",
    )
    # Copier only writes the answers file if the template itself provides a
    # source file whose rendered path equals `_answers_file` — mirroring
    # this repository's own template/.agent-process/copier-answers.yml.jinja.
    (answers_dir / "copier-answers.yml.jinja").write_text(
        "{{ _copier_answers | to_nice_yaml }}\n", encoding="utf-8"
    )
    (workflows / "ci.yml").write_text("name: CI\nversion: 1\n", encoding="utf-8")
    _git(["init", "-q"], cwd=template_repo)
    _git(["add", "-A"], cwd=template_repo)
    _git(["commit", "-q", "-m", "v1"], cwd=template_repo)
    old_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=template_repo, text=True, capture_output=True, check=True
    ).stdout.strip()

    (workflows / "ci.yml").write_text("name: CI\nversion: 2\n", encoding="utf-8")
    _git(["add", "-A"], cwd=template_repo)
    _git(["commit", "-q", "-m", "v2"], cwd=template_repo)
    new_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=template_repo, text=True, capture_output=True, check=True
    ).stdout.strip()

    consumer = tmp_path / "consumer"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "copier",
            "copy",
            str(template_repo),
            str(consumer),
            "--vcs-ref",
            old_commit,
            "--defaults",
            "--trust",
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (consumer / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    ) == "name: CI\nversion: 1\n"

    collisions = find_collisions(consumer, vcs_ref=new_commit)

    assert ".github/workflows/ci.yml" not in collisions
