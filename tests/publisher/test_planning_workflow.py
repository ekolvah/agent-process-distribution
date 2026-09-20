"""Planning runs on the OpenSpec skills with project rules (changes v2-1b, v2-1e,
v2-2f-start-change).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.publisher.test_openspec_valid import OPENSPEC, _openspec

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "openspec" / "config.yaml"
REVIEWER = ROOT / "agents" / "architect-reviewer.md"
ARCHIVE = ROOT / ".agent-process" / "scripts" / "archive_change.py"
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


def test_roles_and_carriers() -> None:
    """Scenario: Procedure changes once — the unmodified spec-driven schema, one config."""
    assert not (ROOT / "openspec" / "schemas").exists()
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema"] == "spec-driven"
    rules = config["rules"]
    assert {"proposal", "tasks"} <= set(rules)
    assert set(rules) <= {"proposal", "specs", "design", "tasks"}
    tasks = " ".join(rules["tasks"])
    for carrier in ("architect-review.md", "architect-reviewer", "self-review", "approve"):
        assert carrier in tasks, carrier


def test_review_finding() -> None:
    """Scenario: Review finding — the contract of the review is the `tasks` rule."""
    tasks = " ".join(yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"])
    for part in ("Verdict", "Findings", "Scenario coverage", "§I–VII", "simpler", "no RED"):
        assert part in tasks, part


def test_rework_verdict() -> None:
    """Scenario: Rework verdict — the propose run reviews again; the apply gate is task 0.1."""
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    tasks = " ".join(config["rules"]["tasks"])
    assert "run the review again" in tasks
    assert "the propose run ends on `approve`" in tasks
    # The gate is `start_change.py` reading the verdict (v2-2f), not a grep in the rule.
    assert "start_change.py" in tasks
    assert 'grep -q "^approve"' not in tasks
    # The gate is stated once: no second copy as apply guidance.
    assert "apply" not in config.get("operations", {})
    # The stock propose skill reports the plan ready once tasks.md exists; the
    # run-level `context` (loaded before the first artifact and returned with every
    # instruction) is what makes the review the end of the run, not the tasks rule alone.
    assert "architect-review.md" in config["context"]
    assert "reported ready" in config["context"]


def test_review_archives_with_the_change(tmp_path: Path) -> None:
    """Scenario: Review archives with the change — an extra file travels with the directory."""
    root = tmp_path
    change = root / "openspec" / "changes" / "fixture"
    (root / "openspec" / "specs").mkdir(parents=True)
    (change / "specs" / "fixture").mkdir(parents=True)
    files = {
        ".openspec.yaml": "schema: spec-driven\n",
        "proposal.md": "## Why\n\nA fixture.\n",
        "specs/fixture/spec.md": (
            "## ADDED Requirements\n\n### Requirement: Fixture\nThe fixture SHALL exist.\n\n"
            "#### Scenario: Exists\n- **WHEN** archived\n- **THEN** it is in the archive\n"
        ),
        "tasks.md": "## 1. Done\n\n- [x] 1.1 Nothing\n",
        "architect-review.md": "## Verdict\n\napprove\n",
    }
    for name, text in files.items():
        (change / name).write_text(text, encoding="utf-8")
    completed = _openspec("archive", "fixture", "-y", cwd=root)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    archived = list(
        (root / "openspec" / "changes" / "archive").glob("*-fixture/architect-review.md")
    )
    assert len(archived) == 1, archived
    assert not change.exists()


def test_tasks_of_a_new_change() -> None:
    """Scenario: Tasks of a new change — priority before the issue, the archive before the PR."""
    rule = " ".join(yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"])
    assert rule.index("priority") < rule.index("create_tracking_issue.py")
    assert rule.index("archive_change.py") < rule.index("gh pr create")
    assert "finish_change" not in rule
    # Group 0 and the propose tail are scripts (v2-2f): the shell steps left the rule.
    for shell in ("gh issue create", "sed -i", "gh issue develop"):
        assert shell not in rule, shell
    # Scenario: Runner given — check_red runs its own pytest; the rule names no runner
    # argument, no runner in AGENTS.md and no report path (v2-2d-check-red-own-runner).
    assert "check_red.py <node ids>" in rule
    assert "--test" not in rule
    assert "AGENTS.md" not in rule
    assert "--report" not in rule
    # No tick after the archive (a pushed tick would move the reviewed head); a run
    # interrupted after it resumes from the PR, not from the apply.
    assert "no tick" in rule
    assert rule.index("archive_change.py") < rule.index("gh pr view <change>")
    # Scenario: Blocking thread addressed — the loop names the resolve of a P0/P1
    # thread after the re-request; CI never classifies a thread (ADR 0022, 0027).
    assert (
        rule.index("wait_for_pr.py")
        < rule.index("re-request")
        < rule.index("resolve_review_thread.py")
        < rule.index("three rounds")
    )
    assert "a `P0`/`P1` thread the push addressed is resolved" in rule
    assert "a `P2`/`P3` thread is answered, never resolved by the process" in rule
    assert "BLOCKING" not in rule
    assert "until v2-4" not in rule
    # The step after the wait is one command — `resolve_review_thread.py --thread
    # --reply-file`: it refuses while the head's `agent-review` run is running (the
    # review of the head is in when it concluded, Codex's or the fallback's), resolves,
    # re-runs that run (a resolve has no event of its own, and the required context is
    # the head's `pull_request` run; #137: `BLOCKED` with the review-event runs green,
    # `CLEAN` after the rerun) and replies. The order lives in the script, so the rule
    # spells no rerun, no window and no reply step of its own.
    assert "reaches its last step" not in rule
    assert "the reply re-runs the check" not in rule
    assert "gh run rerun" not in rule
    assert (
        rule.index("re-request, `wait_for_pr.py <PR>` again")
        < rule.index("or the fallback's")
        < rule.index("resolve_review_thread.py")
        < rule.index("--reply-file")
        < rule.index("three rounds")
    )
    # Scenario: Review fix changes a spec — the archive is what carries a spec, on
    # the first PR and on every fix; a direct edit of `openspec/specs/` bypasses the
    # delta and its validation (#137, Codex on 26bc2da).
    assert (
        rule.index("--reply-file")
        < rule.index("never a direct edit of `openspec/specs/`")
        < rule.index("three rounds")
    )


def test_plan_approved() -> None:
    """Scenario: Plan approved — the review entry ends with the issue in Planned; Group 0 asks nothing."""
    entries = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"]
    review = next(e for e in entries if e.startswith("Architect review"))
    # The tail is one command: `create_tracking_issue.py <change> --priority <answer>`
    # (the issue from proposal.md, Planned with the priority, the number into tasks.md).
    assert review.index("approve") < review.index("create_tracking_issue.py")
    assert review.index("create_tracking_issue.py") < review.index("--priority")
    group0 = next(e for e in entries if "Group 0" in e)
    assert "create_tracking_issue" not in group0 and "priority" not in group0
    # The gate is `start_change.py`: the verdict, the issue's Status and the token of
    # tasks.md are its exit codes — a propose run that stopped before its tail is a
    # visible stop of the apply, not a prompt and not a silent branch on a missing issue.
    assert "start_change.py" in group0
    assert "propose run not finished" in group0
    assert '"Planned"' not in group0 and "gh issue view" not in group0
    # The number reaches the implementer of another session through the token
    # `tracking issue <N>` in Group 0 of tasks.md: the tail replaces it, both scripts read it.
    assert "tracking issue <N>" in group0


def test_design_on_a_platform_behaviour() -> None:
    """Scenario: Design on a platform behaviour — the `proposal` rule names the trigger, the step and what counts."""
    rule = " ".join(yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["proposal"])
    for part in (
        "platform behaviour",
        "before the proposal",
        "the observation, not the inference",
        "reference page",
        "run id",
        "pointed at, not repeated",
    ):
        assert part in rule, part


def test_asserted_platform_fact() -> None:
    """Scenario: Asserted platform fact — the Architect review entry names the finding."""
    entries = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"]
    review = next(e for e in entries if e.startswith("Architect review"))
    assert "asserted, not observed" in review
    assert review.index("is a finding") < review.index("asserted, not observed")


def _deliver_entry() -> str:
    entries = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"]
    return next(e for e in entries if "wait_for_pr" in e and "three rounds" in e)


def test_replaced_input_designed() -> None:
    """Scenario: Replaced input designed — the `design` rule names the trigger, the three lists and the exclusion."""
    rules = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]
    assert "design" in rules
    rule = " ".join(rules["design"])
    for part in (
        "replaces a project-declared input",
        "failure modes",
        "stops proving",
        "which script, which run, on which head",
        "not a role",
    ):
        assert part in rule, part


def test_untraceable_catcher() -> None:
    """Scenario: Untraceable catcher — the Architect review entry names both findings."""
    entries = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rules"]["tasks"]
    review = next(e for e in entries if e.startswith("Architect review"))
    for part in ("without the list", "cannot trace"):
        assert part in review, part
        assert review.index("is a finding") < review.index(part), part


def test_design_decision_changed_at_review() -> None:
    """Scenario: Design decision changed at review — the amendment sits between the spec-changing fix and the round limit."""
    deliver = _deliver_entry()
    amend = deliver.index("amends the archived `design.md`")
    assert deliver.index("never a direct edit of `openspec/specs/`") < amend
    assert amend < deliver.index("three rounds")


def test_finding_closed_by_its_class() -> None:
    """Scenario: Finding closed by its class — the Deliver entry names the trigger and what closes the class."""
    deliver = _deliver_entry()
    start = deliver.index("amends the archived")
    end = deliver.index("three rounds")
    for part in ("closed by its class", "invariant", "takes away", "not the reviewer's example"):
        assert part in deliver, part
        assert start < deliver.index(part) < end, part


def test_pinned_openspec() -> None:
    """The commands the process runs use the version the tests validate against."""
    for path in (CONFIG, ARCHIVE):
        text = path.read_text(encoding="utf-8")
        assert "openspec@latest" not in text, path
        assert OPENSPEC in text, path


def test_one_planning_home() -> None:
    """A change lives in the repository whose PR archives it: no registered store anywhere."""
    context = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["context"]
    assert "registered store" in context
    for path in (CONFIG, REVIEWER):
        assert "--store" not in path.read_text(encoding="utf-8"), path


def test_label_change() -> None:
    """Scenario: Label change — no per-label artifact sets, no discovery role, no v1 planner."""
    present = [p for p in _V1_ENTRY_POINTS if (ROOT / p).exists()]
    assert present == []
