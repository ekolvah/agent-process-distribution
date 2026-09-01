"""RED contract: the closed-root collision scanner must not flag managed-fragment targets.

`adopt_agent_process._path_conflicts` already exempts `AGENTS.md` and
`.gitignore` from raw-byte collision because a consumer's own content merges
with the process's delimited fragment instead of colliding with it (ADR-0019).
`find_collisions` scans the same closed root set but never applied that same
exemption, so any consumer with real custom content in either file gets a
false-positive collision report that blocks `copier update`.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts.check_consumer_test_collision import find_collisions


def test_find_collisions_exempts_managed_fragment_targets(
    rendered_default: Path, tmp_path: Path
) -> None:
    consumer = tmp_path / "consumer"
    shutil.copytree(rendered_default, consumer)
    (consumer / "AGENTS.md").write_text("# Product instructions\n", encoding="utf-8")
    (consumer / ".gitignore").write_text("product-cache/\n", encoding="utf-8")

    collisions = find_collisions(consumer, vcs_ref="HEAD")

    assert "AGENTS.md" not in collisions
    assert ".gitignore" not in collisions
