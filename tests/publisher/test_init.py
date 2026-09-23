"""The local installer lifecycle (change v2-2g-b-local-installer-lifecycle, design D6).

Tests drive the transitions — preview, release selection, write, interruption, retry,
conflict — against real `git` and a local bare repository whose tag `v2.0.0` carries this
tree's `skills/agent-process/` and whose tag `v2.1.0` carries a recording stub `init.py`.
The runner is the process boundary: it logs every command, emulates `npx` (writing the
observed OpenSpec file set) and, for rows of the other platform, the link command, and
runs everything else for real. `test_installed_footprint_is_closed` runs the real pinned
OpenSpec. The module is imported inside the tests so that a missing symbol fails its own
test body.

`gh` never reaches GitHub: the runner hands it to `FakeGitHub` (change
v2-2g-c-project-provisioning, design D6), which answers the two reads in their observed
shapes and applies `project copy` and `project link` to its own Projects.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import pytest
import yaml

from tests.publisher.init_harness import (
    HOST,
    OWNER,
    REPO_NAME,
    ROOT,
    TITLE,
    FakeGitHub,
    Runner,
    Sandbox,
    git,
    head_commit,
    host_link,
    install,
    is_link,
    link_command,
    load_init,
    relative,
    snapshot,
    tag_commit,
    transitions,
)

LABELS = [
    "checkout",
    "link",
    "openspec",
    "config",
    "workflow",
    "dependabot",
    "settings",
    "project-copy",
    "project-link",
]
CONSUMER_FILES = {
    ".github/workflows/agent-process.yml",
    ".github/dependabot.yml",
    ".claude/settings.json",
}
MARKETPLACE = "agent-process-marketplace"
PLUGIN = "agent-process@agent-process-marketplace"


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


def _block(text: str) -> str:
    """The text with the marker block removed."""
    return re.sub(
        r"^[ \t]*# agent-process:begin$.*?^[ \t]*# agent-process:end\n",
        "",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )


def test_rerender_replaces_only_owned_content(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    init = load_init()
    root = sandbox.root
    for rel in init.OPENSPEC_OUTPUT:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("consumer\n", encoding="utf-8")
    config = root / "openspec" / "config.yaml"
    config.write_text(
        "schema: spec-driven\ncontext: mine\n"
        "# agent-process:begin\n# openspec: 1.12.0\nrules:\n  proposal:\n    - old\n"
        "# agent-process:end\n# tail\n",
        encoding="utf-8",
    )
    workflow = root / ".github" / "workflows" / "agent-process.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("# agent-process:managed\nold: v1.9.0\n", encoding="utf-8")
    (root / ".github" / "workflows" / "mine.yml").write_text("name: mine\n", encoding="utf-8")
    dependabot = root / ".github" / "dependabot.yml"
    dependabot.write_text(
        "version: 2\nupdates:\n  - package-ecosystem: npm\n    directory: /\n"
        "  # agent-process:begin\n  - old\n  # agent-process:end\n",
        encoding="utf-8",
    )
    settings = root / ".claude" / "settings.json"
    consumer_settings = {
        "permissions": {"allow": ["Bash(ls)"]},
        "extraKnownMarketplaces": {
            "mine": {"source": {"source": "github", "repo": "me/mine"}},
            MARKETPLACE: {
                "source": {
                    "source": "github",
                    "repo": "ekolvah/agent-process-distribution",
                    "ref": "v1.9.0",
                }
            },
        },
        "enabledPlugins": {"mine@mine": True},
    }
    # The form `init` writes: an update re-serialises losslessly only from it (design D4).
    settings.write_text(json.dumps(consumer_settings, indent=2) + "\n", encoding="utf-8")
    before = {path: path.read_text(encoding="utf-8") for path in (config, dependabot)}
    untouched = {
        rel: data
        for rel, data in relative(snapshot(root), root).items()
        if Path(rel).as_posix() not in {"openspec/config.yaml", *CONSUMER_FILES}
    }
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0, capfd.readouterr().out

    assert sum(Path(cmd[0]).name.lower().startswith("npx") for cmd in runner.log) == 1
    for path in (config, dependabot):
        text = path.read_text(encoding="utf-8")
        assert _block(text) == _block(before[path])
        assert "# agent-process:begin" in text and "old" not in _only_block(text)
    assert "# openspec: 1.13.0" in config.read_text(encoding="utf-8")
    assert workflow.read_text(encoding="utf-8") == init.render_workflow("2.0.0", "", "pytest -q")
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["permissions"] == consumer_settings["permissions"]
    assert (
        data["extraKnownMarketplaces"]["mine"]
        == consumer_settings["extraKnownMarketplaces"]["mine"]
    )
    assert data["extraKnownMarketplaces"][MARKETPLACE]["source"]["ref"] == "v2.0.0"
    assert data["enabledPlugins"] == {"mine@mine": True, PLUGIN: True}
    after = relative(snapshot(root), root)
    assert {rel: after[rel] for rel in untouched} == untouched


def test_update_keeps_consumer_bytes(sandbox: Sandbox) -> None:
    """CRLF stays CRLF, a missing final newline stays missing, and a settings file in another
    form that already holds both keys is not rewritten."""
    init = load_init()
    _installed(init, sandbox)
    config = sandbox.root / "openspec" / "config.yaml"
    body = config.read_bytes().replace(b"\r\n", b"\n")
    head, block = body.split(b"# agent-process:begin", 1)
    config.write_bytes(
        (head + b"# agent-process:begin\n# stale" + block).replace(b"\n", b"\r\n")
        + b"# tail without newline"
    )
    settings = sandbox.root / ".claude" / "settings.json"
    four_spaces = json.dumps(json.loads(settings.read_text(encoding="utf-8")), indent=4)
    settings.write_text(four_spaces, encoding="utf-8")
    assert install(init, sandbox, "--confirm") == 0

    after = config.read_bytes()
    assert b"# stale" not in after and after.startswith(head.replace(b"\n", b"\r\n"))
    assert after.count(b"\n") == after.count(b"\r\n")
    assert after.endswith(b"\r\n# tail without newline")
    assert settings.read_text(encoding="utf-8") == four_spaces


def _only_block(text: str) -> str:
    match = re.search(r"# agent-process:begin\n(.*?)# agent-process:end", text, flags=re.DOTALL)
    assert match
    return match.group(1)


# --- conflicts --------------------------------------------------------------------------


def _write(sb: Sandbox, rel: str, text: str) -> None:
    path = sb.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_bytes(sb: Sandbox, rel: str, data: bytes) -> None:
    path = sb.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _home_file(sb: Sandbox, rel: str) -> None:
    sb.home.mkdir(parents=True, exist_ok=True)
    (sb.home / rel).write_bytes(b"")


def _settings(repo: str = "ekolvah/agent-process-distribution", enabled: Any = True) -> str:
    return json.dumps(
        {
            "extraKnownMarketplaces": {MARKETPLACE: {"source": {"source": "github", "repo": repo}}},
            "enabledPlugins": {PLUGIN: enabled},
        }
    )


def _installed(init: ModuleType, sb: Sandbox) -> None:
    assert install(init, sb, "--confirm") == 0


def _checkout_dirty(init: ModuleType, sb: Sandbox) -> None:
    _installed(init, sb)
    skill = sb.checkout / "skills" / "agent-process" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "local\n", encoding="utf-8")


def _checkout_other_origin(init: ModuleType, sb: Sandbox) -> None:
    _installed(init, sb)
    git("remote", "set-url", "origin", "https://example.invalid/other.git", cwd=sb.checkout)


def _checkout_not_repository(init: ModuleType, sb: Sandbox) -> None:
    sb.checkout.mkdir(parents=True)
    (sb.checkout / "file").write_text("mine\n", encoding="utf-8")


def _link_real_directory(init: ModuleType, sb: Sandbox) -> None:
    sb.link.mkdir(parents=True)


def _link_elsewhere(init: ModuleType, sb: Sandbox) -> None:
    host_link(sb.other, sb.link)


CONFLICTS: dict[str, tuple[str, Callable[[ModuleType, Sandbox], None]]] = {
    "config-several-markers": (
        "config",
        lambda init, sb: _write(
            sb,
            "openspec/config.yaml",
            "# agent-process:begin\n# agent-process:end\n" * 2,
        ),
    ),
    "config-unordered-markers": (
        "config",
        lambda init, sb: _write(
            sb, "openspec/config.yaml", "# agent-process:end\n# agent-process:begin\n"
        ),
    ),
    "config-unmarked-rules": (
        "config",
        lambda init, sb: _write(sb, "openspec/config.yaml", "rules:\n  proposal:\n    - mine\n"),
    ),
    "workflow-unmanaged": (
        "workflow",
        lambda init, sb: _write(sb, ".github/workflows/agent-process.yml", "name: mine\n"),
    ),
    "dependabot-without-block": (
        "dependabot",
        lambda init, sb: _write(sb, ".github/dependabot.yml", "version: 2\nupdates: []\n"),
    ),
    "settings-invalid-json": (
        "settings",
        lambda init, sb: _write(sb, ".claude/settings.json", "{"),
    ),
    "settings-non-object": (
        "settings",
        lambda init, sb: _write(sb, ".claude/settings.json", "[]"),
    ),
    "settings-other-repository": (
        "settings",
        lambda init, sb: _write(sb, ".claude/settings.json", _settings(repo="someone/else")),
    ),
    "settings-plugin-disabled": (
        "settings",
        lambda init, sb: _write(sb, ".claude/settings.json", _settings(enabled=False)),
    ),
    # YAML spellings of the same top-level key (review of PR 159).
    **{
        f"config-rules-{name}": (
            "config",
            lambda init, sb, text=text: _write(sb, "openspec/config.yaml", text),
        )
        for name, text in {
            "double-quoted": '"rules":\n  proposal: []\n',
            "single-quoted": "'rules':\n  proposal: []\n",
            "explicit-key": "? rules\n: {}\n",
            "tagged": "!!str rules:\n  proposal: []\n",
            "flow-mapping": "{rules: {}}\n",
            "indented": "  rules:\n    proposal: []\n",
        }.items()
    },
    # Only a single document whose root starts at column 0 makes a column-0 `rules` key the
    # whole top-level check, and only there does the appended block stay valid YAML.
    "config-indented-root": (
        "config",
        lambda init, sb: _write(sb, "openspec/config.yaml", "  schema: spec-driven\n"),
    ),
    "config-several-documents": (
        "config",
        lambda init, sb: _write(sb, "openspec/config.yaml", "schema: a\n---\nschema: b\n"),
    ),
    **{
        f"{label}-not-utf8": (
            label,
            lambda init, sb, rel=rel: _write_bytes(sb, rel, b"\xff\xfe\x00"),
        )
        for label, rel in {
            "config": "openspec/config.yaml",
            "workflow": ".github/workflows/agent-process.yml",
            "dependabot": ".github/dependabot.yml",
            "settings": ".claude/settings.json",
        }.items()
    },
    # A managed path that is not a regular file, or a parent that is not a directory, is
    # the person's: a write would replace a link or fail after earlier writes.
    **{
        f"{label}-directory": (label, lambda init, sb, rel=rel: (sb.root / rel).mkdir(parents=True))
        for label, rel in {
            "config": "openspec/config.yaml",
            "workflow": ".github/workflows/agent-process.yml",
            "dependabot": ".github/dependabot.yml",
            "settings": ".claude/settings.json",
        }.items()
    },
    "settings-dangling-link": (
        "settings",
        lambda init, sb: host_link(sb.home / "missing", sb.root / ".claude" / "settings.json"),
    ),
    "workflow-parent-file": ("workflow", lambda init, sb: _write(sb, ".github/workflows", "")),
    # The user-profile targets have parents too (review of PR 159, round 3).
    "checkout-parent-file": ("checkout", lambda init, sb: _home_file(sb, ".agent-process")),
    "link-parent-file": ("link", lambda init, sb: _home_file(sb, ".agents")),
    "config-rules-escaped": (
        "config",
        lambda init, sb: _write(sb, "openspec/config.yaml", '"r\\u0075les":\n  proposal: []\n'),
    ),
    # A write that cannot keep every consumer byte is refused (design D4).
    "config-mixed-line-endings": (
        "config",
        lambda init, sb: _write_bytes(sb, "openspec/config.yaml", b"schema: a\r\ncontext: b\n"),
    ),
    "settings-mixed-line-endings": (
        "settings",
        lambda init, sb: _write_bytes(sb, ".claude/settings.json", b"{\r\n}\n"),
    ),
    "settings-other-form": (
        "settings",
        lambda init, sb: _write(sb, ".claude/settings.json", '{\n    "model": "opus"\n}\n'),
    ),
    "settings-repeated-key": (
        "settings",
        lambda init, sb: _write(sb, ".claude/settings.json", '{\n  "a": 1,\n  "a": 2\n}\n'),
    ),
    "settings-null-marketplace": (
        "settings",
        lambda init, sb: _write(
            sb,
            ".claude/settings.json",
            json.dumps({"extraKnownMarketplaces": {MARKETPLACE: None}}, indent=2) + "\n",
        ),
    ),
    "checkout-dirty": ("checkout", _checkout_dirty),
    "checkout-other-origin": ("checkout", _checkout_other_origin),
    "checkout-not-repository": ("checkout", _checkout_not_repository),
    "link-real-directory": ("link", _link_real_directory),
    "link-elsewhere": ("link", _link_elsewhere),
}


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
@pytest.mark.parametrize("case", sorted(CONFLICTS))
def test_conflict_fails_closed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str, mode: str
) -> None:
    init = load_init()
    label, arrange = CONFLICTS[case]
    arrange(init, sandbox)
    capfd.readouterr()
    before = snapshot(sandbox.root, sandbox.home)
    code = install(init, sandbox, mode)
    out = capfd.readouterr().out
    assert code == 2, out
    assert transitions(out)[label] == "conflict", out
    assert "written" not in transitions(out).values()
    assert snapshot(sandbox.root, sandbox.home) == before


# --- footprint and remote writes --------------------------------------------------------


def _consumer_repo(sb: Sandbox) -> None:
    (sb.root / "README.md").write_text("consumer\n", encoding="utf-8")
    git("init", "-q", cwd=sb.root)
    git("add", "-A", cwd=sb.root)
    git("commit", "-q", "-m", "initial", cwd=sb.root)


def test_installed_footprint_is_closed(sandbox: Sandbox) -> None:
    init = load_init()
    _consumer_repo(sandbox)
    runner = Runner(init, HOST, sandbox.github, real_npx=True)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    status = git("status", "--porcelain", "--untracked-files=all", cwd=sandbox.root)
    changed = {line[3:] for line in status.splitlines()}
    assert changed == set(init.OPENSPEC_OUTPUT) | CONSUMER_FILES
    settings = json.loads((sandbox.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {
        "extraKnownMarketplaces": {
            MARKETPLACE: {
                "source": {
                    "source": "github",
                    "repo": "ekolvah/agent-process-distribution",
                    "ref": "v2.0.0",
                }
            }
        },
        "enabledPlugins": {PLUGIN: True},
    }


def _gh_kind(args: list[str]) -> str:
    """`read`, `copy`, or `link`; any other `gh` command fails the test."""
    if args[:2] == ["repo", "view"]:
        return "read"
    if args[:2] == ["api", "graphql"] and not any("mutation" in part for part in args):
        return "read"
    if args[:2] == ["project", "copy"]:
        return "copy"
    if args[:2] == ["project", "link"]:
        return "link"
    raise AssertionError(f"gh command that is not a read, the copy, or the link: {args}")


def test_only_project_writes_remote(sandbox: Sandbox) -> None:
    init = load_init()
    _consumer_repo(sandbox)
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    kinds = [_gh_kind(args) for args in runner.gh()]
    assert (kinds.count("copy"), kinds.count("link")) == (1, 1), kinds
    for cmd in runner.log:
        assert not any("api.github.com" in part for part in cmd), cmd
        if Path(cmd[0]).name.lower().startswith("git"):
            assert not {"commit", "push"} & set(cmd), cmd
    assert git("rev-list", "--count", "HEAD", cwd=sandbox.root) == "1"
    assert git("status", "--porcelain", cwd=sandbox.root)


def test_dry_run_writes_nothing_remote(sandbox: Sandbox) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state()
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    assert runner.gh("repo", "view") and runner.gh("api", "graphql")
    assert {_gh_kind(args) for args in runner.gh()} == {"read"}
    assert sandbox.github.state() == before


# --- the Project phase ------------------------------------------------------------------

CONSUMER = f"{OWNER}/{REPO_NAME}"
# Each row: arrange the fake, then (project-copy, project-link) of the plan, or the exit code
# alone when the read itself refuses (design D2 and the truncated list of D1).
PROJECT_STATES: dict[str, tuple[Callable[[FakeGitHub], Any], tuple[str, str] | int]] = {
    "linked-one": (lambda gh: gh.add("anything", linked=CONSUMER), ("unchanged", "unchanged")),
    "linked-several": (
        lambda gh: (gh.add(linked=CONSUMER), gh.add("other", linked=CONSUMER)),
        ("conflict", "conflict"),
    ),
    "none": (lambda gh: gh.add("another title"), ("planned", "planned")),
    "one-reusable": (
        lambda gh: (gh.add(), gh.add(closed=True)),
        ("unchanged", "planned"),
    ),
    "several-reusable": (lambda gh: (gh.add(), gh.add()), ("conflict", "conflict")),
    "only-closed": (lambda gh: gh.add(closed=True), ("conflict", "conflict")),
    "only-linked-elsewhere": (
        lambda gh: gh.add(linked=f"{OWNER}/elsewhere"),
        ("conflict", "conflict"),
    ),
    "truncated-list": (lambda gh: setattr(gh, "hidden", 1), 1),
}


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
@pytest.mark.parametrize("case", list(PROJECT_STATES))
def test_project_states(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str, mode: str
) -> None:
    init = load_init()
    arrange, expected = PROJECT_STATES[case]
    arrange(sandbox.github)
    runner = Runner(init, HOST, sandbox.github)
    before = (snapshot(sandbox.root, sandbox.home), sandbox.github.state())
    code = install(init, sandbox, mode, runner=runner)
    out = capfd.readouterr().out
    seen = transitions(out)
    if isinstance(expected, int):
        assert code == expected, out
        assert "project-copy" not in seen
        assert (snapshot(sandbox.root, sandbox.home), sandbox.github.state()) == before
        return
    plan = dict(zip(("project-copy", "project-link"), expected))
    for label, status in plan.items():
        assert f"{status} {label}:" in out, out
    if "conflict" in expected:
        assert code == 2, out
        assert "written" not in seen.values()
        assert (snapshot(sandbox.root, sandbox.home), sandbox.github.state()) == before
        return
    assert code == 0, out
    if case == "linked-one":
        assert not runner.gh("api", "graphql")
    if mode == "--confirm":
        assert seen == dict.fromkeys(LABELS, "written") | {
            label: "written" if status == "planned" else status for label, status in plan.items()
        }, out
        linked = [p for p in sandbox.github.projects if CONSUMER in p.repositories]
        assert len(linked) == 1


@pytest.mark.parametrize("fault", ["fail-before", "fail-after"])
@pytest.mark.parametrize("command", ["copy", "link"])
def test_project_command_faults(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], command: str, fault: str
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    sandbox.github.faults[command] = fault
    assert install(init, sandbox, "--confirm", runner=runner) == 1
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    copies, links = len(runner.gh("project", "copy")), len(runner.gh("project", "link"))
    expected = {
        ("copy", "fail-before"): (2, 1),
        ("copy", "fail-after"): (1, 1),
        ("link", "fail-before"): (1, 2),
        ("link", "fail-after"): (1, 1),
    }[command, fault]
    assert (copies, links) == expected
    if (command, fault) == ("link", "fail-after"):
        assert transitions(out)["project-copy"] == "unchanged"
        assert transitions(out)["project-link"] == "unchanged"
    titled = [p for p in sandbox.github.projects if p.title == TITLE]
    assert len(titled) == 1 and titled[0].repositories == {CONSUMER}


WORKFLOWS = [
    "Auto-add to project",
    "Item added",
    "Item reopened",
    "Item closed",
    "Pull request merged",
]


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_manual_actions_are_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, mode, runner=runner) == 0
    lines = capfd.readouterr().out.splitlines()
    visibility = [ln for ln in lines if ln.startswith("manual project-visibility: ")]
    workflows = [ln for ln in lines if ln.startswith("manual project-workflows: ")]
    assert len(visibility) == 1 and "visibility" in visibility[0]
    assert len(workflows) == 1 and all(name in workflows[0] for name in WORKFLOWS)
    for args in runner.gh():
        _gh_kind(args)


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
    (job,) = workflow["jobs"].values()
    assert job["uses"] == (
        "ekolvah/agent-process-distribution/.github/workflows/reusable-quality.yml@v2.0.0"
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
