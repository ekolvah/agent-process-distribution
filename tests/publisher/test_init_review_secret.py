"""Requirement *The review secret is set from the machine's token* (change
init-sets-review-secret): `init` sets `CLAUDE_CODE_OAUTH_TOKEN` from
`~/.claude/agent-process-review-token` before the installation branch is pushed, keeping the
token out of command lines and the output."""

from __future__ import annotations

import pytest

from tests.publisher.init_harness import (
    HOST,
    Runner,
    Sandbox,
    install,
    load_init,
    no_token,
    transitions,
)
from tests.publisher.init_reads import _pushes

TOKEN = "sk-ant-oat01-review-token-0123"  # pragma: allowlist secret
SECRET = "CLAUDE_CODE_OAUTH_TOKEN"
ROW = "manual review-secret: "


def _token_file(sb: Sandbox) -> None:
    path = sb.home / ".claude" / "agent-process-review-token"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TOKEN + "\n", encoding="utf-8")


def _rows(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith(ROW)]


def _labels(out: str) -> list[str]:
    return [ln.split(":")[0].split(" ")[-1] for ln in out.splitlines() if ln.startswith("written ")]


def test_secret_set_from_token_file(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Secret set from the token file."""
    _token_file(sandbox)
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out, err = capfd.readouterr()
    written = _labels(out)
    assert "review-secret" in written, out
    assert written.index("review-secret") < written.index("onboarding-push"), written
    assert sandbox.github.secret_values == {SECRET: TOKEN}
    assert _rows(out) == [], out
    no_token(runner, TOKEN, out, err)


def test_secret_planned(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Secret planned."""
    _token_file(sandbox)
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    out, err = capfd.readouterr()
    assert transitions(out).get("review-secret") == "planned", out
    assert runner.gh("secret", "set") == []
    assert _rows(out) == [], out
    no_token(runner, TOKEN, out, err)


def test_secret_already_set(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Secret already set."""
    sandbox.github.secrets.add(SECRET)
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    assert transitions(out).get("review-secret") == "unchanged", out
    assert runner.gh("secret", "set") == []
    assert _rows(out) == [], out


def test_secret_write_fails(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Secret write fails."""
    _token_file(sandbox)
    sandbox.github.faults["secret-set"] = "fail"
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 1
    out, err = capfd.readouterr()
    (error,) = [ln for ln in err.splitlines() if ln.startswith("error: ")]
    assert "review-secret" in error, err
    assert _pushes(runner) == [], runner.log
    no_token(runner, TOKEN, out, err)
