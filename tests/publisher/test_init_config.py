"""The installer's rendering of owned content: the config block and its release line,
consumer bytes around it, and the SessionStart hook (change v2-2g-b-local-installer-lifecycle).

The module is imported inside the tests so that a missing symbol fails its own test
body. The fixture repository and the runner are described in `test_init.py`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

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
    install,
    load_init,
    relative,
    snapshot,
    transitions,
)


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
    assert workflow.read_text(encoding="utf-8") == init.render_workflow(CURRENT, "", "pytest -q")
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["permissions"] == consumer_settings["permissions"]
    assert (
        data["extraKnownMarketplaces"]["mine"]
        == consumer_settings["extraKnownMarketplaces"]["mine"]
    )
    assert data["extraKnownMarketplaces"][MARKETPLACE]["source"]["ref"] == f"v{CURRENT}"
    assert data["enabledPlugins"] == {"mine@mine": True, PLUGIN: True}
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
