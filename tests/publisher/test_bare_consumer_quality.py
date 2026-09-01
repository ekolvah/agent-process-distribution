"""A bare third-party consumer must pass its own rendered quality gate end-to-end.

Every other publisher test asserts static properties of the render. Both
#57 findings were only visible once the rendered payload actually ran as an
unrestricted consumer would run it: the product-scoped `pytest`/`ruff`
passes re-collected/re-linted `tests/agent_process` and `.agent-process`
under a root config with none of the process's own settings, and product
dependencies were never installed before product checks ran. This exercises
`ci_check.py` — the same driver `reusable-quality.yml` invokes — against a
synthetic bare consumer layered on the real Copier render, so a regression
in either behaviour fails here before it ever reaches review.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _bare_consumer(rendered_default: Path, tmp_path: Path) -> Path:
    consumer = tmp_path / "consumer"
    shutil.copytree(rendered_default, consumer)
    # A bare consumer's own layer: a product dependency (gives it product
    # scope) and a product test module, with no pytest config of its own —
    # default discovery, so nothing here restricts `testpaths`.
    (consumer / "requirements.txt").write_text("tomli==2.0.1\n", encoding="utf-8")
    product_tests = consumer / "tests"
    product_tests.mkdir(exist_ok=True)
    (product_tests / "test_product.py").write_text(
        "def test_product_passes() -> None:\n    assert True\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "--quiet"], cwd=consumer, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=consumer, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=consumer, check=True)
    subprocess.run(["git", "add", "."], cwd=consumer, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "bare consumer"], cwd=consumer, check=True)
    return consumer


def test_bare_consumer_pytest_pass_does_not_re_collect_the_process_suite(
    rendered_default: Path, tmp_path: Path
) -> None:
    consumer = _bare_consumer(rendered_default, tmp_path)

    completed = subprocess.run(
        [sys.executable, ".agent-process/scripts/ci_check.py", "--only", "pytest"],
        cwd=consumer,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "test_product_passes" in completed.stdout or "1 passed" in completed.stdout


def test_bare_consumer_lint_and_format_pass_do_not_touch_process_paths(
    rendered_default: Path, tmp_path: Path
) -> None:
    consumer = _bare_consumer(rendered_default, tmp_path)

    for check in ("format", "lint"):
        completed = subprocess.run(
            [sys.executable, ".agent-process/scripts/ci_check.py", "--only", check],
            cwd=consumer,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
