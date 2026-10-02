"""The installer's rendering of owned content: the config block and its release line,
consumer bytes around it, and the SessionStart hook (change v2-2g-b-local-installer-lifecycle).

The module is imported inside the tests so that a missing symbol fails its own test
body. The fixture repository and the runner are described in `test_init.py`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.publisher.init_harness import (
    CHECK_COMMAND,
    CHECK_GROUP,
    CONSUMER_FILES,
    CURRENT,
    HOST,
    MARKETPLACE,
    PLUGIN,
    Runner,
    Sandbox,
    _installed,
    commit_seed,
    git,
    install,
    load_init,
    pins,
    relative,
    snapshot,
    transitions,
)

ROOT = Path(__file__).resolve().parents[2]


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
    pre_commit = root / ".pre-commit-config.yaml"
    pre_commit.write_text(
        "default_install_hook_types: [pre-push]\nrepos:\n  - repo: local\n    hooks:\n"
        "      - id: mine\n        name: mine\n        entry: mine\n        language: system\n"
        "  # agent-process:begin\n  - old\n  # agent-process:end\n",
        encoding="utf-8",
    )
    settings = root / ".claude" / "settings.json"
    consumer_settings: dict[str, Any] = {
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
        "enabledPlugins": {"mine@mine": True, PLUGIN: True},
        "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "mine"}]}],
            "SessionStart": [
                {"hooks": [{"type": "command", "command": "mine-start"}]},
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": CHECK_COMMAND.replace(f"v{CURRENT}", "v1.9.0"),
                        }
                    ]
                },
            ],
        },
    }
    # The form `init` writes: an update re-serialises losslessly only from it (design D4).
    settings.write_text(json.dumps(consumer_settings, indent=2) + "\n", encoding="utf-8")
    commit_seed(sandbox)
    before = {path: path.read_text(encoding="utf-8") for path in (config, dependabot, pre_commit)}
    untouched = {
        rel: data
        for rel, data in relative(snapshot(root), root).items()
        if Path(rel).as_posix() not in {"openspec/config.yaml", *CONSUMER_FILES}
    }
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0, capfd.readouterr().out

    assert sum(Path(cmd[0]).name.lower().startswith("npx") for cmd in runner.log) == 1
    for path in (config, dependabot, pre_commit):
        text = path.read_text(encoding="utf-8")
        assert _block(text) == _block(before[path])
        assert "# agent-process:begin" in text and "old" not in _only_block(text)
    assert "# openspec: 1.13.0" in config.read_text(encoding="utf-8")
    assert workflow.read_text(encoding="utf-8") == init.render_workflow(CURRENT)
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["permissions"] == consumer_settings["permissions"]
    assert (
        data["extraKnownMarketplaces"]["mine"]
        == consumer_settings["extraKnownMarketplaces"]["mine"]
    )
    assert data["extraKnownMarketplaces"][MARKETPLACE]["source"]["ref"] == "stable"
    assert data["extraKnownMarketplaces"][MARKETPLACE]["autoUpdate"] is True
    assert data["enabledPlugins"] == {"mine@mine": True}
    assert data["hooks"] == {
        "PreToolUse": consumer_settings["hooks"]["PreToolUse"],
        "SessionStart": [consumer_settings["hooks"]["SessionStart"][0], CHECK_GROUP],
    }
    after = relative(snapshot(root), root)
    assert {rel: after[rel] for rel in untouched} == untouched


def test_config_block_records_release(sandbox: Sandbox) -> None:
    """Scenario: Release recorded — install and rerender record the installed release (#190)."""
    init = load_init()
    line, old = f"# agent-process release: {init.VERSION}", "# agent-process release: 1.9.0"
    config = sandbox.root / "openspec" / "config.yaml"
    _installed(init, sandbox)
    assert line in _only_block(config.read_text(encoding="utf-8")).splitlines()
    config.write_text(config.read_text(encoding="utf-8").replace(line, old), encoding="utf-8")
    _installed(init, sandbox)
    block = _only_block(config.read_text(encoding="utf-8")).splitlines()
    assert line in block and old not in block


def test_dependabot_leaves_process_refs_to_install(sandbox: Sandbox) -> None:
    """Scenario: Dependabot render — the process refs are ignored; Install moves them (#199)."""
    init = load_init()
    _installed(init, sandbox)
    dependabot = yaml.safe_load(
        (sandbox.root / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    )
    [entry] = [e for e in dependabot["updates"] if e["package-ecosystem"] == "github-actions"]
    assert entry.get("ignore") == [{"dependency-name": "ekolvah/agent-process-distribution*"}]


def test_pre_commit_block_references_the_hook(sandbox: Sandbox) -> None:
    """Scenario: Consumer render — the block pins this repository's `quality` hook at the
    installed release, and pre-commit installs it at `pre-push` (#188)."""
    init = load_init()
    _installed(init, sandbox)
    config = yaml.safe_load((sandbox.root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert config["default_install_hook_types"] == ["pre-push"]
    assert {
        "repo": "https://github.com/ekolvah/agent-process-distribution",
        "rev": f"v{CURRENT}",
        "hooks": [{"id": "quality"}],
    } in config["repos"]
    hooks = yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8"))
    [quality] = [hook for hook in hooks if hook["id"] == "quality"]
    assert quality["stages"] == ["pre-push"]


EDIT_AND_GATE = ["pre-commit", "manual"]


def _baseline() -> list[dict[str, Any]]:
    """The baseline repositories of design D2 at the pins of design D3."""
    own = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    [ruff] = [r["rev"] for r in own["repos"] if r["repo"].endswith("/ruff-pre-commit")]
    pin = pins()

    def audit(lockfile: str) -> dict[str, Any]:
        return {
            "id": "pip-audit",
            "name": f"pip-audit {lockfile}",
            "args": ["-r", lockfile],
            "files": "^" + re.escape(lockfile) + "$",
            "stages": ["manual"],
        }

    return [
        {
            "repo": "https://github.com/astral-sh/ruff-pre-commit",
            "rev": ruff,
            "hooks": [
                {
                    "id": "ruff-check",
                    "args": ["--extend-select=C901,PLR0911,PLR0912,PLR0913,PLR0915"],
                    "stages": EDIT_AND_GATE,
                },
                {"id": "ruff-format", "stages": EDIT_AND_GATE},
            ],
        },
        {
            "repo": "https://github.com/pre-commit/mirrors-mypy",
            "rev": f"v{pin['mypy']}",
            "hooks": [{"id": "mypy", "args": [], "stages": EDIT_AND_GATE}],
        },
        {
            "repo": "https://github.com/pylint-dev/pylint",
            "rev": f"v{pin['pylint']}",
            "hooks": [
                {
                    "id": "pylint",
                    "args": ["--disable=all", "--enable=too-many-lines", "--max-module-lines=1000"],
                    "stages": EDIT_AND_GATE,
                }
            ],
        },
        {
            "repo": "https://github.com/Yelp/detect-secrets",
            "rev": f"v{pin['detect-secrets']}",
            "hooks": [{"id": "detect-secrets", "stages": EDIT_AND_GATE}],
        },
        {
            "repo": "https://github.com/pypa/pip-audit",
            "rev": f"v{pin['pip-audit']}",
            "hooks": [audit("requirements.txt"), audit("requirements-dev.txt")],
        },
        {
            "repo": "local",
            "hooks": [
                {
                    "id": "pytest",
                    "name": "pytest",
                    "entry": "python -m pytest",
                    "language": "unsupported",
                    "pass_filenames": False,
                    "files": r"(^|/)(test_[^/]*|[^/]*_test)\.py$",
                    "stages": ["manual"],
                }
            ],
        },
    ]


def test_created_config_carries_the_baseline(sandbox: Sandbox) -> None:
    """Scenario: Created config — the baseline hooks at their stages, each `rev` this
    repository's pin of its tool (design D2, D3)."""
    init = load_init()
    _installed(init, sandbox)
    config = yaml.safe_load((sandbox.root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    assert config["minimum_pre_commit_version"] == "4.4.0"
    block = {
        "repo": "https://github.com/ekolvah/agent-process-distribution",
        "rev": f"v{CURRENT}",
        "hooks": [{"id": "quality"}],
    }
    assert config["repos"] == [block, *_baseline()]


def test_existing_config_keeps_its_hooks(sandbox: Sandbox) -> None:
    """Scenario: Existing config keeps its hooks — only the block changes (design D1)."""
    init = load_init()
    pre_commit = sandbox.root / ".pre-commit-config.yaml"
    pre_commit.write_text(
        "default_install_hook_types: [pre-push]\nrepos:\n  - repo: local\n    hooks:\n"
        "      - id: mine\n        name: mine\n        entry: mine\n        language: system\n"
        "  # agent-process:begin\n"
        "  - repo: https://github.com/ekolvah/agent-process-distribution\n"
        "    rev: v1.9.0\n    hooks:\n      - id: quality\n  # agent-process:end\n",
        encoding="utf-8",
    )
    commit_seed(sandbox)
    before = pre_commit.read_text(encoding="utf-8")
    _installed(init, sandbox)
    after = pre_commit.read_text(encoding="utf-8")
    assert _block(after) == _block(before)
    assert f"rev: v{CURRENT}" in _only_block(after)
    ids = {hook["id"] for repo in yaml.safe_load(after)["repos"] for hook in repo["hooks"]}
    assert ids == {"mine", "quality"}


def test_baseline_runs_tests_once_they_exist(sandbox: Sandbox, tmp_path: Path) -> None:
    """Scenario: Tests run once they exist — the created config's `pytest` hook is skipped
    with no tracked test file and runs a tracked failing test (design D2)."""
    init = load_init()
    _installed(init, sandbox)
    config = yaml.safe_load((sandbox.root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    [local] = [repo for repo in config["repos"] if repo["repo"] == "local"]
    work = tmp_path / "work"
    work.mkdir()
    git("init", "-q", str(work))
    (work / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump({"repos": [local]}), encoding="utf-8"
    )
    (work / "a.py").write_text("A = 1\n", encoding="utf-8")
    env = {
        **os.environ,
        "PATH": os.pathsep.join([str(Path(sys.executable).parent), os.environ["PATH"]]),
    }
    env.pop("PYTEST_ADDOPTS", None)

    def run() -> subprocess.CompletedProcess[str]:
        git("add", "-A", cwd=work)
        git("commit", "-q", "-m", "x", cwd=work)
        return subprocess.run(
            [sys.executable, "-m", "pre_commit", "run", "--hook-stage", "manual", "--all-files"],
            cwd=work,
            env=env,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    skipped = run()
    assert skipped.returncode == 0, (skipped.stdout, skipped.stderr)
    [line] = [ln for ln in skipped.stdout.splitlines() if ln.startswith("pytest")]
    assert line.endswith("Skipped"), skipped.stdout
    (work / "tests").mkdir()
    (work / "tests" / "test_a.py").write_text(
        "def test_fails_on_purpose():\n    assert False\n", encoding="utf-8"
    )
    failed = run()
    assert failed.returncode != 0, failed.stdout
    assert "test_fails_on_purpose" in failed.stdout, failed.stdout


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


def test_installed_consumer_gains_the_hook(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """A consumer installed before the check holds both owned keys: the next run adds the
    hook, and a hand-formatted file gets the conflict that names it."""
    init = load_init()
    _installed(init, sandbox)
    settings = sandbox.root / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    del data["hooks"]
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    assert install(init, sandbox, "--confirm") == 0
    assert json.loads(settings.read_text(encoding="utf-8"))["hooks"] == {
        "SessionStart": [CHECK_GROUP]
    }

    settings.write_text(json.dumps(data, indent=4), encoding="utf-8")
    capfd.readouterr()
    assert install(init, sandbox, "--confirm") == 2
    out = capfd.readouterr().out
    assert transitions(out)["settings"] == "conflict", out
    assert "SessionStart" in out


@pytest.mark.parametrize(
    "command",
    [
        "echo agent-process-check.py",
        'python "$CLAUDE_PROJECT_DIR/tools/agent-process-check.py" x',
        CHECK_COMMAND + " --verbose",
        "prefix " + CHECK_COMMAND,
    ],
    ids=["mention", "other-path", "extra-argument", "wrapped"],
)
def test_consumer_session_start_is_not_owned(sandbox: Sandbox, command: str) -> None:
    """Only the exact group `init` writes, for any release, is owned: a consumer group that
    merely names the check file, or adds a hook beside it, keeps its content."""
    init = load_init()
    _installed(init, sandbox)
    settings = sandbox.root / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    consumer = [
        {"hooks": [{"type": "command", "command": command}]},
        {
            "hooks": [
                {"type": "command", "command": CHECK_COMMAND},
                {"type": "command", "command": "mine"},
            ]
        },
    ]
    data["hooks"] = {"SessionStart": consumer}
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    assert install(init, sandbox, "--confirm") == 0
    assert json.loads(settings.read_text(encoding="utf-8"))["hooks"] == {
        "SessionStart": [*consumer, CHECK_GROUP]
    }


def _only_block(text: str) -> str:
    match = re.search(r"# agent-process:begin\n(.*?)# agent-process:end", text, flags=re.DOTALL)
    assert match
    return match.group(1)
