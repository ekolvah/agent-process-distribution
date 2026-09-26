"""The local installer lifecycle (change v2-2g-b-local-installer-lifecycle, design D6).

Tests drive the transitions — preview, release selection, write, interruption, retry,
conflict — against real `git` and a local bare repository whose tag `v2.0.0` carries this
tree's `skills/agent-process/` and whose tag `v2.1.0` carries a recording stub `init.py`.
The runner is the process boundary: it logs every command, emulates `npx` (writing the
observed OpenSpec file set) and, for rows of the other platform, the link command, and
runs everything else for real. The module is imported inside the tests so that a missing
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
from types import ModuleType
from typing import Any

import pytest
import yaml

from tests.publisher.init_harness import (
    HOST,
    LABELS,
    ROOT,
    Runner,
    Sandbox,
    git,
    head_commit,
    install,
    is_link,
    link_command,
    load_init,
    relative,
    snapshot,
    tag_commit,
    transitions,
)


def test_fixture_tags_carry_releases(process_repo: Path) -> None:
    released = git("show", "v2.0.0:skills/agent-process/SKILL.md", cwd=process_repo)
    assert released.startswith("---\nname: agent-process")
    stub = git("show", "v2.1.0:skills/agent-process/scripts/init.py", cwd=process_repo)
    assert "stub-release v2.1.0" in stub


# --- the lifecycle table ----------------------------------------------------------------


@pytest.mark.parametrize("platform", ["win32", "linux"])
@pytest.mark.parametrize("mode", ["dry-run", "confirm", "retry"])
@pytest.mark.parametrize("scenario", ["fresh", "same-version", "upgrade"])
def test_lifecycle(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], scenario: str, mode: str, platform: str
) -> None:
    init = load_init()
    if scenario != "fresh":
        assert install(init, sandbox, "--confirm", platform=platform) == 0
    if mode == "retry":
        version = "2.1.0" if scenario == "upgrade" else "2.0.0"
        assert install(init, sandbox, "--confirm", "--version", version, platform=platform) == 0
    capfd.readouterr()
    before = snapshot(sandbox.root, sandbox.home)
    version = ["--version", "2.1.0"] if scenario == "upgrade" else []
    flag = "--dry-run" if mode == "dry-run" else "--confirm"
    code = install(init, sandbox, flag, *version, platform=platform)
    out = capfd.readouterr().out
    after = snapshot(sandbox.root, sandbox.home)
    assert code == 0, out
    assert out.splitlines()[0] == f"repository: {sandbox.repo}"
    seen = transitions(out)
    if scenario == "upgrade":
        assert "stub-release v2.1.0" in out
        argv = json.loads(next(ln for ln in out.splitlines() if ln.startswith("argv "))[5:])
        assert flag in argv and "--selected-release" in argv
        if mode == "dry-run":
            assert seen == {} and after == before
        else:
            assert seen == {
                "checkout": "written" if mode == "confirm" else "unchanged",
                "link": "unchanged",
                "hand-off": "planned",
            }
            assert head_commit(sandbox.checkout) == tag_commit(sandbox, "v2.1.0")
        return
    if scenario == "fresh" and mode != "retry":
        expected = "planned" if mode == "dry-run" else "written"
    else:
        expected = "unchanged"
    assert seen == dict.fromkeys(LABELS, expected), out
    if expected != "written":
        assert after == before
    else:
        assert head_commit(sandbox.checkout) == tag_commit(sandbox, "v2.0.0")


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
    code = install(init, sandbox, "--dry-run", "--version", "2.1.0")
    out = capfd.readouterr().out
    assert code == 3
    assert "stub-release v2.1.0" in out
    lines = out.splitlines()
    argv = json.loads(next(ln for ln in lines if ln.startswith("argv "))[5:])
    assert argv == ["--test", "pytest -q", "--dry-run", "--version", "2.1.0", "--selected-release"]
    assert f"cwd {sandbox.root}" in lines
    assert snapshot(sandbox.root, sandbox.home) == before
    assert list(scratch.iterdir()) == []


def test_confirm_selects_release_before_composing(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    code = install(init, sandbox, "--confirm", "--version", "2.1.0", runner=runner)
    out = capfd.readouterr().out
    assert code == 0, out
    ran = next(line[5:] for line in out.splitlines() if line.startswith("file "))
    selected = sandbox.checkout / "skills" / "agent-process" / "scripts" / "init.py"
    assert os.path.realpath(ran) == os.path.realpath(selected)
    assert head_commit(sandbox.checkout) == tag_commit(sandbox, "v2.1.0")
    handoff = next(i for i, cmd in enumerate(runner.log) if cmd[0] == sys.executable)
    assert any("clone" in cmd for cmd in runner.log[:handoff])
    assert not any(Path(cmd[0]).name.lower().startswith("npx") for cmd in runner.log)
    assert snapshot(sandbox.root) == {}


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_skill_link_resolves_to_selected_release(sandbox: Sandbox, platform: str) -> None:
    init = load_init()
    runner = Runner(init, platform, sandbox.github)
    target = sandbox.checkout / "skills" / "agent-process"
    for version, tag in (("2.0.0", "v2.0.0"), ("2.1.0", "v2.1.0")):
        code = install(
            init, sandbox, "--confirm", "--version", version, platform=platform, runner=runner
        )
        assert code == 0
        assert is_link(sandbox.link)
        assert os.path.realpath(sandbox.link) == os.path.realpath(target)
        assert head_commit(sandbox.checkout) == tag_commit(sandbox, tag)
    links = [cmd for cmd in runner.log if link_command(cmd)]
    assert len(links) == 1
    name = Path(links[0][0]).name.lower()
    assert name.startswith("cmd" if platform == "win32" else "ln")


# --- interruption and retry -------------------------------------------------------------


class Interrupted(Exception):
    pass


def _prepare(init: ModuleType, sb: Sandbox, scenario: str) -> list[str]:
    """Bring the sandbox to the scenario's starting state; return the requested version."""
    if scenario == "upgrade":
        assert install(init, sb, "--confirm") == 0
        return ["--version", "2.1.0"]
    return []


def _final(sb: Sandbox) -> dict[str, Any]:
    return {
        "root": relative(snapshot(sb.root), sb.root),
        "head": head_commit(sb.checkout),
        "link": os.path.relpath(os.path.realpath(sb.link), os.path.realpath(sb.home)),
        "github": sb.github.state(),
    }


@pytest.mark.parametrize("scenario", ["fresh", "upgrade"])
def test_retry_after_each_write(
    tmp_path: Path,
    process_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    scenario: str,
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
        return sb

    reference = fresh_sandbox("reference")
    version = _prepare(init, reference, scenario)
    labels: list[str] = []
    assert install(init, reference, "--confirm", *version, on_write=labels.append) == 0
    expected = _final(reference)
    assert labels, "an uninterrupted run reports its writes"

    for label in labels:
        sb = fresh_sandbox(f"at-{label}")
        _prepare(init, sb, scenario)
        runner = Runner(init, HOST, sb.github)

        def interrupt(seen: str, at: str = label) -> None:
            if seen == at:
                raise Interrupted(at)

        with pytest.raises(Interrupted):
            install(init, sb, "--confirm", *version, runner=runner, on_write=interrupt)
        capfd.readouterr()
        assert install(init, sb, "--confirm", *version, runner=runner) == 0
        out = capfd.readouterr().out
        assert transitions(out)[label] == "unchanged", (label, out)
        assert _final(sb) == expected, label
        keys = runner.state_changing()
        assert len(keys) == len(set(keys)), (label, keys)


# --- rendering and arguments ------------------------------------------------------------

LITERALS = [
    "pytest -q",
    'echo "a: b" # c',
    "it's {x} [y] & *z | %p @q `r`",
    "yes",
    "null",
    "1.0",
    "- dash",
    "a\\b",
    "ünïcødé → ✓",
    "line1\nline2",
]


@pytest.mark.parametrize("literal", LITERALS)
def test_literal_commands_are_yaml_safe(literal: str) -> None:
    init = load_init()
    workflow = yaml.safe_load(init.render_workflow("2.0.0", literal, literal))
    (job,) = workflow["jobs"].values()
    assert job["with"] == {"setup": literal, "test": literal}
    block = yaml.safe_load(init.render_config_block(literal))
    assert any(literal in rule for rule in block["rules"]["tasks"])


def test_caller_inputs() -> None:
    init = load_init()
    text = init.render_workflow("2.0.0", "", "pytest -q")
    assert text.splitlines()[0] == "# agent-process:managed"
    workflow = yaml.safe_load(text)
    assert list(workflow["jobs"]) == ["agent-process"]
    job = workflow["jobs"]["agent-process"]
    assert job["uses"] == (
        "ekolvah/agent-process-distribution/.github/workflows/quality.yml@v2.0.0"
    )
    assert set(job["with"]) == {"setup", "test"}


@pytest.mark.parametrize("test", ["", "   "])
def test_empty_test_command_is_refused(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], test: str
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner, test=test) == 2
    assert runner.log == []
    assert snapshot(sandbox.root, sandbox.home) == {}


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
        setup="",
        test="",
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
        setup="",
        test="",
    )
    with pytest.raises(init.InstallError) as raised:
        init._gh_json(ctx, "repo", "view", "--json", "owner,name,projectsV2")
    assert present in str(raised.value)
