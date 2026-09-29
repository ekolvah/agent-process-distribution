"""Installer conflicts fail closed (change v2-2g-b-local-installer-lifecycle).

The module is imported inside the tests so that a missing symbol fails its own test
body. The fixture repository and the runner are described in `test_init.py`.
"""

from __future__ import annotations

import json
from types import ModuleType
from typing import Any, Callable

import pytest

from tests.publisher.init_harness import (
    MARKETPLACE,
    PLUGIN,
    Sandbox,
    commit_seed,
    host_link,
    install,
    load_init,
    snapshot,
    transitions,
)

# --- conflicts --------------------------------------------------------------------------


def _write(sb: Sandbox, rel: str, text: str) -> None:
    path = sb.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_bytes(sb: Sandbox, rel: str, data: bytes) -> None:
    path = sb.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _settings(repo: str = "ekolvah/agent-process-distribution", enabled: Any = True) -> str:
    return json.dumps(
        {
            "extraKnownMarketplaces": {MARKETPLACE: {"source": {"source": "github", "repo": repo}}},
            "enabledPlugins": {PLUGIN: enabled},
        }
    )


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
    "review-unmanaged": (
        "review",
        lambda init, sb: _write(sb, ".github/workflows/agent-review.yml", "name: mine\n"),
    ),
    "dependabot-without-block": (
        "dependabot",
        lambda init, sb: _write(sb, ".github/dependabot.yml", "version: 2\nupdates: []\n"),
    ),
    "pre-commit-without-block": (
        "pre-commit",
        lambda init, sb: _write(sb, ".pre-commit-config.yaml", "repos: []\n"),
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
    "settings-hooks-not-object": (
        "settings",
        lambda init, sb: _write(
            sb, ".claude/settings.json", json.dumps({"hooks": []}, indent=2) + "\n"
        ),
    ),
    "settings-session-start-not-list": (
        "settings",
        lambda init, sb: _write(
            sb,
            ".claude/settings.json",
            json.dumps({"hooks": {"SessionStart": {}}}, indent=2) + "\n",
        ),
    ),
    "check-unmanaged": (
        "check",
        lambda init, sb: _write(sb, ".claude/agent-process-check.py", "print('mine')\n"),
    ),
    # A caller of the previous release passes the command this repository ran; the new
    # caller passes none, so the rewrite would drop it silently (declare-quality D5).
    "workflow-passes-test": ("workflow", lambda init, sb: _passed_test(sb)),
}

QUALITY = ".github/agent-process-quality.json"
PASSED_CALLER = """\
# agent-process:managed
# Rendered by the agent-process installer (init.py); rerun it instead of editing this file.
name: agent-process

on:
  pull_request:

permissions:
  contents: read
  pull-requests: read
  issues: read

jobs:
  agent-process:
    uses: ekolvah/agent-process-distribution/.github/workflows/quality.yml@v3.0.2
    with:
      setup: ""
      test: "pytest -q"
"""


def _passed_test(sb: Sandbox) -> None:
    _write(sb, ".github/workflows/agent-process.yml", PASSED_CALLER)


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


@pytest.mark.parametrize("declared", ["absent", "malformed"])
def test_upgrade_over_passed_test_conflicts(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], declared: str
) -> None:
    """Scenario: Upgrade over a passed test command — the conflict quotes the passed command
    and names the declaration that would carry it; once that file declares a `test`, the
    caller is rewritten."""
    init = load_init()
    _passed_test(sandbox)
    if declared == "malformed":
        _write(sandbox, QUALITY, '{"test": ""}')
    capfd.readouterr()
    code = install(init, sandbox, "--dry-run")
    captured = capfd.readouterr()
    assert code == 2, captured.out
    assert "Traceback" not in captured.out + captured.err
    (line,) = [ln for ln in captured.out.splitlines() if ln.startswith("conflict workflow:")]
    assert "pytest -q" in line and QUALITY in line, line

    _write(sandbox, QUALITY, '{"test": "pytest -q"}')
    commit_seed(sandbox)
    assert install(init, sandbox, "--dry-run") == 0
    assert transitions(capfd.readouterr().out)["workflow"] == "planned"
