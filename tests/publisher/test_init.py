"""The local installer lifecycle (change v2-2g-b-local-installer-lifecycle, design D6).

Tests drive the transitions — preview, release selection, write, interruption, retry,
conflict — against real `git` and a local bare repository whose tag `v{CURRENT}` carries this
tree's `skills/agent-process/` and whose tag `v{OTHER}` carries a recording stub `init.py`.
The runner is the process boundary: it logs every command, emulates `npx` (writing the
observed OpenSpec file set) and runs everything else for real. The module is imported inside the tests so that a missing
symbol fails its own test body.

`gh` never reaches GitHub: the runner hands it to `FakeGitHub` (change
v2-2g-c-project-provisioning, design D6), which answers the two reads in their observed
shapes and applies `project copy` and `project link` to its own Projects.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.publisher.init_harness import (
    BRANCH,
    CURRENT,
    HOST,
    LABELS,
    OTHER,
    ROOT,
    Runner,
    Sandbox,
    commit_seed,
    consumer_repo,
    git,
    home_baseline,
    install,
    load_init,
    relative,
    snapshot,
    transitions,
)


def test_fixture_tags_carry_releases(process_repo: Path) -> None:
    released = git("show", f"v{CURRENT}:skills/agent-process/SKILL.md", cwd=process_repo)
    assert released.startswith("---\nname: agent-process")
    stub = git("show", f"v{OTHER}:skills/agent-process/scripts/init.py", cwd=process_repo)
    assert f"stub-release v{OTHER}" in stub


# --- the lifecycle table ----------------------------------------------------------------


@pytest.mark.parametrize("platform", ["win32", "linux"])
@pytest.mark.parametrize("mode", ["dry-run", "confirm", "retry"])
@pytest.mark.parametrize("scenario", ["fresh", "same-version", "upgrade"])
def test_lifecycle(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], scenario: str, mode: str, platform: str
) -> None:
    init = load_init()
    home = snapshot(sandbox.home)
    if scenario != "fresh":
        assert install(init, sandbox, "--confirm", platform=platform) == 0
    if mode == "retry":
        version = OTHER if scenario == "upgrade" else CURRENT
        assert install(init, sandbox, "--confirm", "--version", version, platform=platform) == 0
    capfd.readouterr()
    before = snapshot(sandbox.root, sandbox.home)
    version = ["--version", OTHER] if scenario == "upgrade" else []
    flag = "--dry-run" if mode == "dry-run" else "--confirm"
    code = install(init, sandbox, flag, *version, platform=platform)
    out = capfd.readouterr().out
    after = snapshot(sandbox.root, sandbox.home)
    assert code == 0, out
    assert out.splitlines()[0] == f"repository: {sandbox.repo}"
    seen = transitions(out)
    assert snapshot(sandbox.home) == home
    if scenario == "upgrade":
        assert f"stub-release v{OTHER}" in out
        argv = json.loads(next(ln for ln in out.splitlines() if ln.startswith("argv "))[5:])
        assert flag in argv and "--selected-release" in argv
        assert seen == ({} if mode == "dry-run" else {"hand-off": "planned"})
        assert after == before
        return
    if scenario == "fresh" and mode != "retry":
        expected = "planned" if mode == "dry-run" else "written"
    else:
        expected = "unchanged"
    assert seen == dict.fromkeys(LABELS, expected), out
    if expected != "written":
        assert after == before


def test_other_version_dry_run_leaves_no_state(
    sandbox: Sandbox,
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    init = load_init()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    monkeypatch.setenv("STUB_EXIT", "3")
    before = snapshot(sandbox.root, sandbox.home)
    code = install(init, sandbox, "--dry-run", "--version", OTHER)
    out = capfd.readouterr().out
    assert code == 3
    assert f"stub-release v{OTHER}" in out
    lines = out.splitlines()
    argv = json.loads(next(ln for ln in lines if ln.startswith("argv "))[5:])
    assert argv == ["--dry-run", "--version", OTHER, "--selected-release"]
    assert f"cwd {sandbox.root}" in lines
    assert snapshot(sandbox.root, sandbox.home) == before
    assert list(scratch.iterdir()) == []


def test_confirm_selects_release_before_composing(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    code = install(init, sandbox, "--confirm", "--version", OTHER, runner=runner)
    out = capfd.readouterr().out
    assert code == 0, out
    ran = Path(next(line[5:] for line in out.splitlines() if line.startswith("file ")))
    assert Path(os.path.realpath(sandbox.home)) not in Path(os.path.realpath(ran)).parents
    assert not ran.parents[3].exists()
    assert snapshot(sandbox.home) == home_baseline(sandbox)
    handoff = next(i for i, cmd in enumerate(runner.log) if cmd[0] == sys.executable)
    assert any("clone" in cmd for cmd in runner.log[:handoff])
    assert not any(Path(cmd[0]).name.lower().startswith("npx") for cmd in runner.log)
    assert snapshot(sandbox.root) == {}


def test_confirm_leaves_the_user_profile_alone(sandbox: Sandbox) -> None:
    """Scenario: Confirmed install of the running release — the user profile is untouched."""
    init = load_init()
    before = snapshot(sandbox.home)
    assert install(init, sandbox, "--confirm") == 0
    assert snapshot(sandbox.home) == before


def test_openspec_tools_are_claude_only(sandbox: Sandbox) -> None:
    """Scenario: Fresh repository — OpenSpec writes the Claude Code tool files only."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    npx = [cmd for cmd in runner.log if Path(cmd[0]).name.lower().startswith("npx")]
    openspec = next(cmd for cmd in npx if "init" in cmd)
    assert openspec[openspec.index("--tools") + 1] == "claude"
    assert not [rel for rel in init.OPENSPEC_OUTPUT if rel.startswith(".agents/")]


def test_user_skill_path_is_left_alone(sandbox: Sandbox) -> None:
    """Scenario: Target the installer does not own — a directory at the former Codex skill
    link is the person's: a confirmed run succeeds and leaves it byte-identical."""
    init = load_init()
    sandbox.link.mkdir(parents=True)
    (sandbox.link / "SKILL.md").write_text("mine\n", encoding="utf-8")
    before = snapshot(sandbox.link)

    assert install(init, sandbox, "--confirm") == 0

    assert snapshot(sandbox.link) == before


# --- interruption and retry -------------------------------------------------------------


class Interrupted(Exception):
    pass


def _final(sb: Sandbox) -> dict[str, Any]:
    return {
        "root": relative(snapshot(sb.root), sb.root),
        "github": sb.github.state(),
        "origin": git("for-each-ref", "--format=%(refname)", cwd=sb.origin).splitlines(),
        "tree": git("rev-parse", f"{BRANCH}^{{tree}}", cwd=sb.origin),
        "ahead": git("rev-list", "--count", f"main..{BRANCH}", cwd=sb.origin),
    }


def test_retry_after_each_write(
    tmp_path: Path,
    process_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    init = load_init()
    monkeypatch.setenv("AGENT_PROCESS_REPOSITORY", str(process_repo))

    def fresh_sandbox(name: str) -> Sandbox:
        base = tmp_path / name
        sb = Sandbox(base / "consumer", base / "home", process_repo, base / "other")
        for path in (sb.root, sb.home, sb.other):
            path.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(sb.home))
        monkeypatch.setenv("USERPROFILE", str(sb.home))
        consumer_repo(sb)
        return sb

    reference = fresh_sandbox("reference")
    labels: list[str] = []
    assert install(init, reference, "--confirm", on_write=labels.append) == 0
    expected = _final(reference)
    assert labels, "an uninterrupted run reports its writes"

    for label in labels:
        sb = fresh_sandbox(f"at-{label}")
        runner = Runner(init, HOST, sb.github)

        def interrupt(seen: str, at: str = label) -> None:
            if seen == at:
                raise Interrupted(at)

        with pytest.raises(Interrupted):
            install(init, sb, "--confirm", runner=runner, on_write=interrupt)
        capfd.readouterr()
        assert install(init, sb, "--confirm", runner=runner) == 0
        out = capfd.readouterr().out
        assert transitions(out)[label] == "unchanged", (label, out)
        assert _final(sb) == expected, label
        keys = runner.state_changing()
        assert len(keys) == len(set(keys)), (label, keys)


# --- rendering and arguments ------------------------------------------------------------


def test_caller_inputs() -> None:
    """The caller passes no command: the quality commands are the repository's declaration
    (declare-quality-with-first-tests D2)."""
    init = load_init()
    text = init.render_workflow(CURRENT)
    assert text.splitlines()[0] == "# agent-process:managed"
    workflow = yaml.safe_load(text)
    assert list(workflow["jobs"]) == ["agent-process"]
    job = workflow["jobs"]["agent-process"]
    assert job["uses"] == (
        f"ekolvah/agent-process-distribution/.github/workflows/quality.yml@v{CURRENT}"
    )
    assert "with" not in job


_LEVELS = {"none": 0, "read": 1, "write": 2}


def test_review_caller_render() -> None:
    init = load_init()
    text = init.render_review_workflow(CURRENT)
    assert text.splitlines()[0] == "# agent-process:managed"
    assert "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}" in text
    workflow = yaml.safe_load(text)
    assert workflow.get("on", workflow.get(True)) == {
        "pull_request": {"types": ["opened", "synchronize"]}
    }
    assert list(workflow["jobs"]) == ["agent-review"]
    job = workflow["jobs"]["agent-review"]
    assert job["uses"] == (
        f"ekolvah/agent-process-distribution/.github/workflows/reusable-agent-review.yml@v{CURRENT}"
    )
    assert "with" not in job
    callee = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "reusable-agent-review.yml").read_text(encoding="utf-8")
    )
    schema = callee.get("on", callee.get(True))["workflow_call"]
    assert not any(spec.get("required") for spec in (schema.get("inputs") or {}).values())
    assert set(job["secrets"]) == set(schema["secrets"])
    assert job["secrets"] == {"claude_code_oauth_token": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"}
    granted = workflow["permissions"]
    for scope, level in callee["permissions"].items():
        assert _LEVELS[granted.get(scope, "none")] >= _LEVELS[level], scope


def test_init_takes_no_quality_command(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Install asks for no quality command: a repository without tests has none, and the
    change that adds the first tests declares it (issue 249)."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    for flag in ["--test", "--setup"]:
        assert install(init, sandbox, "--confirm", flag, "x", runner=runner) == 2, flag
    assert runner.log == []
    assert snapshot(sandbox.root, sandbox.home) == home_baseline(sandbox)


QUALITY = ".github/agent-process-quality.json"


@pytest.mark.parametrize("declared", ["absent", "malformed", "declared"])
def test_quality_command_marker(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], declared: str
) -> None:
    """Scenarios: Install without tests, Declared quality command — while the repository
    declares no `test`, every run prints one `manual quality-command:` row; the installer
    never writes the declaration."""
    init = load_init()
    declaration = sandbox.root / QUALITY
    text = {"absent": None, "malformed": '{"test": ""}', "declared": '{"test": "pytest -q"}'}
    if text[declared] is not None:
        declaration.parent.mkdir(parents=True, exist_ok=True)
        declaration.write_text(text[declared], encoding="utf-8")
        commit_seed(sandbox)
    for mode in ["--dry-run", "--confirm"]:
        capfd.readouterr()
        assert install(init, sandbox, mode) == 0
        lines = capfd.readouterr().out.splitlines()
        rows = [ln for ln in lines if ln.startswith("manual quality-command: ")]
        if declared == "declared":
            assert rows == [], rows
        else:
            assert len(rows) == 1, lines
            assert QUALITY in rows[0]
        if text[declared] is None:
            assert not declaration.exists()
        else:
            assert declaration.read_text(encoding="utf-8") == text[declared]


def test_version_matches_plugin() -> None:
    init = load_init()
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert init.VERSION == plugin["version"]


def test_capture_contract() -> None:
    init = load_init()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    code = "import sys; sys.stdout.buffer.write('é✓'.encode('utf-8'))"
    captured = init.run([sys.executable, "-c", code], env=env)
    assert captured.stdout == "é✓"
    inherited = init.run([sys.executable, "-c", "pass"], capture=False)
    assert inherited.stdout is None and inherited.stderr is None


@pytest.mark.parametrize(
    ("stdout", "stderr", "present", "absent"),
    [
        (None, None, "output not captured", None),
        (None, "boom", "boom", "not captured"),
        ("out", None, "out", "not captured"),
        ("", "", "exited 1", "not captured"),
    ],
)
def test_failure_keeps_absent_streams_visible(
    tmp_path: Path, stdout: str | None, stderr: str | None, present: str, absent: str | None
) -> None:
    """An uncaptured stream is not captured empty output: the diagnostic says which it was."""
    init = load_init()
    ctx = init.Context(
        root=tmp_path,
        home=tmp_path,
        platform=HOST,
        runner=lambda cmd, **_: subprocess.CompletedProcess(cmd, 1, stdout, stderr),
        which=lambda name: name,
        repository="",
        version="",
    )
    with pytest.raises(init.InstallError) as raised:
        ctx.call("tool", "arg")
    assert present in str(raised.value)
    if absent:
        assert absent not in str(raised.value)


@pytest.mark.parametrize(("stdout", "present"), [(None, "not captured"), ("", "no JSON")])
def test_gh_read_keeps_absent_stdout_visible(
    tmp_path: Path, stdout: str | None, present: str
) -> None:
    """A read whose stdout was not captured says so, not that `gh` printed nothing (PR 160)."""
    init = load_init()
    ctx = init.Context(
        root=tmp_path,
        home=tmp_path,
        platform=HOST,
        runner=lambda cmd, **_: subprocess.CompletedProcess(cmd, 0, stdout, None),
        which=lambda name: name,
        repository="",
        version="",
    )
    with pytest.raises(init.InstallError) as raised:
        init._gh_json(ctx, "repo", "view", "--json", "owner,name,projectsV2")
    assert present in str(raised.value)
