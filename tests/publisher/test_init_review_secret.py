"""Requirement *The review secret is set from the machine's token* (change
init-sets-review-secret): `init` sets `CLAUDE_CODE_OAUTH_TOKEN` from
`~/.claude/agent-process-review-token` before the installation branch is pushed, keeping the
token out of command lines and the output."""

from __future__ import annotations

import pytest

from tests.publisher.init_harness import (
    HOST,
    LINE,
    REVIEW_TOKEN,
    Runner,
    Sandbox,
    install,
    load_init,
    no_token,
    review_token_file,
    transitions,
)
from tests.publisher.init_reads import _manual_rows, _pushes

SECRET = "CLAUDE_CODE_OAUTH_TOKEN"
ROW = "manual review-secret: "


def _rows(out: str) -> list[str]:
    return [row for row in _manual_rows(out) if row.startswith(ROW)]


def test_secret_set_from_token_file(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Secret set from the token file."""
    review_token_file(sandbox.home, "token")
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out, err = capfd.readouterr()
    written = [label for status, label in LINE.findall(out) if status == "written"]
    assert "review-secret" in written, out
    assert written.index("review-secret") < written.index("onboarding-push"), written
    assert sandbox.github.secret_values == {SECRET: REVIEW_TOKEN}
    assert _rows(out) == [], out
    no_token(runner, REVIEW_TOKEN, out, err)


def test_secret_planned(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Secret planned."""
    review_token_file(sandbox.home, "token")
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    out, err = capfd.readouterr()
    assert transitions(out).get("review-secret") == "planned", out
    assert runner.gh("secret", "set") == []
    assert _rows(out) == [], out
    no_token(runner, REVIEW_TOKEN, out, err)


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
    review_token_file(sandbox.home, "token")
    sandbox.github.faults["secret-set"] = "fail"
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 1
    out, err = capfd.readouterr()
    (error,) = [ln for ln in err.splitlines() if ln.startswith("error: ")]
    assert "review-secret" in error, err
    assert _pushes(runner) == [], runner.log
    no_token(runner, REVIEW_TOKEN, out, err)
