"""Planning and delivery procedure contracts owned by the shared skill."""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.publisher.test_openspec_valid import OPENSPEC, _openspec

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "openspec" / "config.yaml"
SKILL = ROOT / "skills" / "agent-process" / "SKILL.md"
REVIEWER = ROOT / "agents" / "architect-reviewer.md"
ARCHIVE = ROOT / "skills" / "agent-process" / "scripts" / "archive_change.py"


def _skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_roles_and_carriers() -> None:
    assert not (ROOT / "openspec" / "schemas").exists()
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema"] == "spec-driven"
    for heading in ("## Proposal", "## Tasks", "## Architect review"):
        assert heading in _skill()


def test_review_finding() -> None:
    for part in ("Verdict", "Findings", "Scenario coverage", "§I–VII", "no RED"):
        assert part in _skill(), part


def test_rework_verdict() -> None:
    text = _skill()
    assert "review again" in text and "approve" in text
    assert "start_change.py" in text
    assert "apply" not in yaml.safe_load(CONFIG.read_text(encoding="utf-8")).get("operations", {})


def test_review_archives_with_the_change(tmp_path: Path) -> None:
    change = tmp_path / "openspec" / "changes" / "fixture"
    (tmp_path / "openspec" / "specs").mkdir(parents=True)
    (change / "specs" / "fixture").mkdir(parents=True)
    files = {
        ".openspec.yaml": "schema: spec-driven\n",
        "proposal.md": "## Why\n\nA fixture.\n",
        "specs/fixture/spec.md": "## ADDED Requirements\n\n### Requirement: Fixture\nThe fixture SHALL exist.\n\n#### Scenario: Exists\n- **WHEN** archived\n- **THEN** it exists\n",
        "tasks.md": "## 1. Done\n\n- [x] 1.1 Nothing\n",
        "architect-review.md": "## Verdict\n\napprove\n",
    }
    for name, text in files.items():
        (change / name).write_text(text, encoding="utf-8")
    completed = _openspec("archive", "fixture", "-y", cwd=tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert list(
        (tmp_path / "openspec" / "changes" / "archive").glob("*-fixture/architect-review.md")
    )


def test_tasks_of_a_new_change() -> None:
    text = _skill()
    assert (
        text.index("start_change.py")
        < text.index("check_red.py")
        < text.index("archive_change.py")
        < text.index("gh pr create")
        < text.index("wait_for_pr.py")
    )
    assert "tracking issue <N>" in text
    assert "automatic Codex" in text
    assert "@codex review" not in text
    assert "no tick" in text
    assert "three rounds" in text
    assert "never a direct edit of `openspec/specs/`" in text


def test_plan_approved() -> None:
    text = _skill()
    assert text.index("Architect review") < text.index("create_tracking_issue.py")
    assert "Planned" in text and "priority" in text


def test_design_on_a_platform_behaviour() -> None:
    for part in (
        "platform behaviour",
        "observation, not the inference",
        "reference page",
        "run id",
    ):
        assert part in _skill()


def test_asserted_platform_fact() -> None:
    assert "asserted, not observed" in _skill()


def test_replaced_input_designed() -> None:
    for part in (
        "replaces a project-declared input",
        "failure modes",
        "stops proving",
        "which script, which run, on which head",
    ):
        assert part in _skill()


def test_untraceable_catcher() -> None:
    assert "cannot trace" in _skill()


def test_design_decision_changed_at_review() -> None:
    assert "amends the archived `design.md`" in _skill()


def test_finding_closed_by_its_class() -> None:
    for part in ("closed by its class", "invariant", "not the reviewer's example"):
        assert part in _skill()


def test_pinned_openspec() -> None:
    for path in (SKILL, ARCHIVE):
        text = path.read_text(encoding="utf-8")
        assert "openspec@latest" not in text
        assert OPENSPEC in text


def test_one_planning_home() -> None:
    context = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["context"]
    assert "registered store" in context
    for path in (CONFIG, REVIEWER, SKILL):
        assert "--store" not in path.read_text(encoding="utf-8")


def test_label_change() -> None:
    for path in (
        "commands/plan.md",
        "commands/implement.md",
        "agents/discovery.md",
        ".agents/skills/plan-issue",
        ".agents/skills/implement-issue",
    ):
        assert not (ROOT / path).exists()
