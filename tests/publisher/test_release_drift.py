"""Release drift of the delivery entry scripts (change release-drift-check, #190).

Kept apart from ``test_delivery_scripts`` for its module size; the change fixture is shared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import Gh, load_script
from tests.publisher.test_delivery_scripts import _CHANGE, _GROUP0, _START, _change


def _release_config(recorded: str | None) -> bytes:
    """A config block recording `recorded`; `None` drops the release line."""
    lines = load_script("init").render_config_block("t").splitlines()
    kept = [line for line in lines if not line.startswith("# agent-process release: ")]
    assert len(kept) == len(lines) - 1, "the rendered block records no release"
    if recorded is not None:
        kept.insert(1, f"# agent-process release: {recorded}")
    return ("\n".join(kept) + "\n").encode("utf-8")


def _mixed_line_endings() -> bytes:
    """The skill's own release in a file `init` refuses to read: CRLF and LF mixed."""
    return b"schema: spec-driven\r\n" + _release_config(load_script("init").VERSION)


_SCRIPTS = {"start_change": _START, "create_tracking_issue": [_CHANGE]}
_INSTALL_FIX = "re-run Install"
_SKILL_FIX = "/plugin marketplace update"
# case -> (config: a release to record, `None` for no release line, or a bytes factory;
#          the release the message names for the project; the fix it names)
_DRIFT: dict[str, tuple[Any, str, str]] = {
    "no-block": (lambda: b"schema: spec-driven\n", "none", _INSTALL_FIX),
    "no-line": (None, "none", _INSTALL_FIX),
    "unparsable": ("abc", "abc", _INSTALL_FIX),
    "older": ("0.0.1", "0.0.1", _INSTALL_FIX),
    "newer": ("99.0.0", "99.0.0", _SKILL_FIX),
    "mixed-line-endings": (_mixed_line_endings, "none", _INSTALL_FIX),
}


@pytest.mark.parametrize("script", sorted(_SCRIPTS))
@pytest.mark.parametrize("case", sorted(_DRIFT))
def test_release_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], script: str, case: str
) -> None:
    """Scenario: Release drift — exit 2 before any GitHub call, naming both releases and the
    fix for that direction; the drift wins over a rework verdict (design: Placement)."""
    config, recorded, fix = _DRIFT[case]
    module = load_script(script)
    version = load_script("init").VERSION
    text = config() if callable(config) else _release_config(config)
    for verdict in ("approve", "rework"):
        root = _change(
            tmp_path / verdict,
            verdict=verdict,
            tasks=_GROUP0.format(token="tracking issue 7"),
            config=text,
        )
        gh = Gh(status="Planned")
        with pytest.raises(SystemExit) as exc:
            module.main(_SCRIPTS[script], gh=gh, root=root)
        err = capsys.readouterr().err
        assert exc.value.code == 2, err
        assert gh.calls == []
        assert "release drift" in err and "verdict" not in err
        assert f"project records {recorded}" in err and f"skill is {version}" in err
        assert fix in err


def test_publisher_checkout_is_exempt(tmp_path: Path) -> None:
    """Scenario: Publisher checkout — the scripts of `<root>/skills/agent-process/scripts` skip
    the comparison; a copy anywhere else under the root is compared."""
    init = load_script("init")
    (tmp_path / "openspec").mkdir()
    (tmp_path / "openspec" / "config.yaml").write_bytes(b"schema: spec-driven\n")
    publisher = tmp_path / "skills" / "agent-process" / "scripts"
    scratch = tmp_path / "scratch" / "skills" / "agent-process" / "scripts"
    for path in (publisher, scratch):
        path.mkdir(parents=True)

    assert init.release_drift(tmp_path, publisher) is None
    message = init.release_drift(tmp_path, scratch)
    assert message is not None and "project records none" in message
