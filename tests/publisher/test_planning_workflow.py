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


_V1_ENTRY_POINTS = (
    "commands/plan.md",
    "commands/implement.md",
    "agents/discovery.md",
    ".agents/skills/plan-issue",
    ".agents/skills/implement-issue",
    ".agents/orchestration/change-classes.yaml",
    ".agent-process/scripts/validate_issue_sections.py",
    ".agent-process/scripts/capture_external_fixture.py",
    ".agent-process/scripts/check_fixture_ratchet.py",
    "tests/agent_process/test_validate_issue_status.py",
)


def _skill() -> str:
    """The shared skill as one line: it is prose, so its line breaks are not the contract."""
    return " ".join(SKILL.read_text(encoding="utf-8").split())


def _section(heading: str) -> str:
    """The body of one `## <heading>` section of the shared skill, as one line."""
    lines = SKILL.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"## {heading}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return " ".join(" ".join(lines[start:end]).split())


def _group0() -> str:
    """The Group 0 item of the `## Tasks` section."""
    tasks = _section("Tasks")
    return tasks[tasks.index("Group 0") : tasks.index("Group 1")]


def test_artifact_rules_point_to_shared_skill() -> None:
    """Scenario: Procedure changes once — config keeps context and points at one source."""
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema"] == "spec-driven"
    assert "This repository publishes" in config["context"]
    assert set(config["rules"]) == {"proposal", "specs", "design", "tasks"}
    anchors = {
        "proposal": "#proposal",
        "specs": "#specifications",
        "design": "#design",
        "tasks": "#tasks",
    }
    for artifact, rules in config["rules"].items():
        joined = " ".join(rules)
        assert "skills/agent-process/SKILL.md" in joined
        assert anchors[artifact] in joined
        assert len(joined) < 180


def test_roles_and_carriers() -> None:
    assert not (ROOT / "openspec" / "schemas").exists()
    assert yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["schema"] == "spec-driven"
    for heading in ("## Proposal", "## Specifications", "## Tasks", "## Architect review"):
        assert heading in _skill()
    # Both carriers reach the same review contract through the shared skill.
    for carrier in ("architect-review.md", "architect-reviewer", "self-review", "approve"):
        assert carrier in _skill(), carrier


def test_review_finding() -> None:
    for part in ("Verdict", "Findings", "Scenario coverage", "§I–VII", "simpler design", "no RED"):
        assert part in _skill(), part


def test_rework_verdict() -> None:
    text = _skill()
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert "review again" in text and "propose run ends on `approve`" in text
    # The gate is `start_change.py` reading the verdict (v2-2f), not a grep in the procedure.
    assert "start_change.py" in text
    assert 'grep -q "^approve"' not in text
    # The gate is stated once: no second copy as apply guidance.
    assert "apply" not in config.get("operations", {})
    # The run-level `context` is what makes the review the end of the propose run.
    assert "architect-review.md" in config["context"]
    assert "reported ready" in config["context"]


def test_review_archives_with_the_change(tmp_path: Path) -> None:
    change = tmp_path / "openspec" / "changes" / "fixture"
    (tmp_path / "openspec" / "specs").mkdir(parents=True)
    (change / "specs" / "fixture").mkdir(parents=True)
    files = {
        ".openspec.yaml": "schema: spec-driven\n",
        "proposal.md": "## Why\n\nA fixture.\n",
        "specs/fixture/spec.md": (
            "## ADDED Requirements\n\n### Requirement: Fixture\nThe fixture SHALL exist.\n\n"
            "#### Scenario: Exists\n- **WHEN** archived\n- **THEN** it exists\n"
        ),
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
        < text.index("request_codex_review.py")
        < text.index("wait_for_pr.py")
    )
    for part in (
        "tracking issue <N>",
        "Claude fallback",
        "three rounds",
        "no tick",
        "never a direct edit of `openspec/specs/`",
        "ready-for-human",
        "A P2/P3 thread is answered, never resolved by the process",
    ):
        assert part in text, part
    # Group 0 and the propose tail are scripts (v2-2f): the shell steps left the procedure.
    # `check_red` owns its runner and report path (v2-2d): the procedure names neither a
    # runner argument nor a declaration in AGENTS.md. The resolve order lives in the
    # script, so the procedure spells no rerun and no reply step of its own.
    for absent in (
        "gh issue create",
        "sed -i",
        "gh issue develop",
        "finish_change",
        "--test",
        "--report",
        "AGENTS.md",
        "BLOCKING",
        "until v2-4",
        "gh run rerun",
        "reaches its last step",
        "the reply re-runs the check",
    ):
        assert absent not in text, absent


def test_plan_approved() -> None:
    text = _skill()
    review = _section("Architect review")
    assert text.index("## Architect review") < text.index("create_tracking_issue.py")
    # The tail is one command: the priority is asked before the issue is created.
    assert review.index("priority") < review.index("create_tracking_issue.py")
    assert review.index("create_tracking_issue.py") < review.index("--priority")
    assert "Planned" in review
    # Group 0 asks nothing and creates nothing: the token is how the number reaches the
    # implementer of another session, and a propose run that stopped short is a visible stop.
    group0 = _group0()
    assert "start_change.py" in group0
    assert "tracking issue <N>" in group0
    assert "propose run not finished" in group0
    for absent in ("create_tracking_issue", "priority", "Planned", "gh issue view"):
        assert absent not in group0, absent


def test_design_on_a_platform_behaviour() -> None:
    for part in (
        "platform behaviour",
        "before the proposal",
        "observation, not the inference",
        "reference page",
        "run id",
        "instead of repeating it",
    ):
        assert part in _skill(), part


def test_asserted_platform_fact() -> None:
    review = _section("Architect review")
    assert "asserted, not observed" in review
    assert review.index("asserted, not observed") < review.index("is a finding")


def test_replaced_input_designed() -> None:
    for part in (
        "replaces a project-declared input",
        "failure modes",
        "stops proving",
        "which script, which run, on which head",
    ):
        assert part in _skill(), part


def test_untraceable_catcher() -> None:
    review = _section("Architect review")
    for part in ("without the Design lists", "cannot trace"):
        assert part in review, part
        assert review.index(part) < review.index("is a finding"), part


def test_design_decision_changed_at_review() -> None:
    deliver = _section("Delivery")
    amend = deliver.index("amends the archived `design.md`")
    assert deliver.index("never a direct edit of `openspec/specs/`") < amend
    assert "scenario map in the same push" in deliver


def test_finding_closed_by_its_class() -> None:
    deliver = _section("Delivery")
    for part in ("closed by its class", "invariant", "takes away", "not the reviewer's example"):
        assert part in deliver, part


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
    """Scenario: Label change — no per-label artifact sets, no discovery role, no v1 planner."""
    assert [path for path in _V1_ENTRY_POINTS if (ROOT / path).exists()] == []
