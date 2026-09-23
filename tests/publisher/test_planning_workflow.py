"""Planning and delivery procedure contracts owned by the shared skill."""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from tests.publisher.test_openspec_valid import OPENSPEC, _openspec

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "openspec" / "config.yaml"
SKILL = ROOT / "skills" / "agent-process" / "SKILL.md"
REVIEWER = ROOT / "agents" / "architect-reviewer.md"
SCRIPTS = ROOT / "skills" / "agent-process" / "scripts"
ARCHIVE = SCRIPTS / "archive_change.py"
REVIEW_SCHEMA = ROOT / "skills" / "agent-process" / "architect-review.schema.json"
_CLASSES = ["simpler", "map", "red", "platform", "replaced", "catcher", "length", "bespoke"]


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


def _schema() -> dict:
    """The review contract: one JSON Schema the reviewer, the scripts and these tests read."""
    return json.loads(REVIEW_SCHEMA.read_text(encoding="utf-8"))


def _class_description(name: str) -> str:
    return _schema()["properties"]["classes"]["properties"][name]["description"]


def _valid_review(verdict: str) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "reviewer": "architect-reviewer",
            "reasoning": "the plan holds",
            "classes": {name: {"evidence": "read", "result": "ok"} for name in _CLASSES},
            "scenario_coverage": [],
        }
    )


def _group0() -> str:
    """The Group 0 item of the `## Tasks` section."""
    tasks = _section("Tasks")
    return tasks[tasks.index("Group 0") : tasks.index("Group 1")]


def _script(name: str) -> ModuleType:
    """One moved script, imported from its file so no package layout is assumed."""
    spec = importlib.util.spec_from_file_location(f"agent_process_{name}", SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(SCRIPTS))  # the skill dir resolves its own sibling imports
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPTS))
    return module


def _printed_commands(text: str) -> list[str]:
    """Code spans that invoke a script: what an agent copies and runs, not a bare mention."""
    spans = re.findall(r"`([^`]+)`", " ".join(text.split()))
    return [span for span in spans if ".py" in span and " " in span]


def _argv(command: str) -> list[str]:
    """The arguments of a printed command, placeholders filled so the parser can read them."""
    argv: list[str] = []
    for token in shlex.split(command)[2:]:  # drop `python <script path>`
        if token.startswith("<"):
            argv.append("1" if argv and argv[-1] == "--pr" else "placeholder")
        else:
            argv.append(token)
    return argv


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
    for carrier in (
        "architect-review.json",
        "architect-review.schema.json",
        "architect-reviewer",
        "self-review",
        "approve",
    ):
        assert carrier in _skill(), carrier
    # The file states which carrier wrote it: a self-review stays visible past the gate.
    schema = _schema()
    assert "reviewer" in schema["required"]
    assert schema["properties"]["reviewer"]["enum"] == ["architect-reviewer", "self-review"]


def test_review_finding() -> None:
    """Every class is checked: a class left out is a validation error naming it."""
    schema = _schema()
    assert schema["properties"]["classes"]["required"] == _CLASSES
    for name in _CLASSES:
        assert _class_description(name), name
    entry = schema["$defs"]["class"]
    assert entry["required"] == ["evidence", "result"]
    assert entry["properties"]["evidence"]["minLength"] == 1
    assert entry["properties"]["result"]["enum"] == ["ok", "finding"]
    assert entry["then"]["required"] == ["finding"]
    assert entry["properties"]["finding"]["required"] == ["principle", "artifact", "what", "change"]
    assert "§I–VII" in _section("Architect review")
    assert "no RED" in _class_description("red")


def test_review_sections_carry_their_contents() -> None:
    """A scenario coverage entry carries its reason, not only the scenario."""
    coverage = _schema()["properties"]["scenario_coverage"]
    assert coverage["items"]["required"] == ["capability", "scenario", "reason"]
    assert "the reason tasks.md carries" in coverage["description"]


def test_over_long_rule_or_bespoke_check() -> None:
    """Scenario: Over-long rule or bespoke check — each is a class of its own."""
    assert "words its tests assert" in _class_description("length")
    assert "observed problem" in _class_description("bespoke")


def test_fourth_round_leaves_the_rest_to_the_person() -> None:
    """The three-round limit is only a limit when the procedure says what happens after it."""
    deliver = _section("Delivery")
    assert "three rounds" in deliver
    assert "the fourth leaves the rest to the person" in deliver


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
    assert "architect-review.json" in config["context"]
    assert "reported ready" in config["context"]


def test_verdict_line_the_gate_reads(tmp_path: Path) -> None:
    """The gate reads the verdict of a valid review; a verdict the schema does not permit fails."""
    start_change = _script("start_change")
    change = tmp_path / "openspec" / "changes" / "fixture"
    change.mkdir(parents=True)
    written = change / "architect-review.json"
    written.write_text(_valid_review("approve"), encoding="utf-8")
    assert start_change.verdict(change) == "approve"
    written.write_text(_valid_review("Approved"), encoding="utf-8")
    with pytest.raises(ValueError, match="'Approved' is not one of"):
        start_change.verdict(change)


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
        "architect-review.json": '{"verdict": "approve"}\n',
    }
    for name, text in files.items():
        (change / name).write_text(text, encoding="utf-8")
    completed = _openspec("archive", "fixture", "-y", cwd=tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert list(
        (tmp_path / "openspec" / "changes" / "archive").glob("*-fixture/architect-review.json")
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
    # script, so the procedure spells no rerun and no reply step of its own. The installer's
    # own `--test` lives in `## Install`, outside the delivery procedure.
    procedure = text[: text.index("## Install")]
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
        assert absent not in procedure, absent


def test_documented_resolve_commands_parse() -> None:
    """The fixer copies both steps — find the thread id, then resolve it — so both must parse."""
    module = _script("resolve_review_thread")
    printed = [
        command
        for command in _printed_commands(SKILL.read_text(encoding="utf-8"))
        if "resolve_review_thread.py" in command
    ]
    parsed = [module._parse_options(_argv(command)) for command in printed]
    assert [options for options in parsed if options.list], "no `--list` step prints the ids"
    assert [options for options in parsed if options.thread and options.reply_file]
    for options in parsed:
        assert options.repo and options.pr


def test_printed_commands_run_as_printed() -> None:
    """No script is on `PATH`: a printed command names its interpreter and a file that exists."""
    printed = _printed_commands(SKILL.read_text(encoding="utf-8"))
    assert len(printed) >= 6
    for command in printed:
        assert command.startswith("python "), command
        assert (ROOT / command.split()[1]).is_file(), command


def test_group0_names_what_stops_the_start() -> None:
    """A start that refuses is visible: the procedure names both conditions and the no-op."""
    group0 = _group0()
    assert "propose run not finished" in group0
    assert "Status" in group0, "the issue state the start requires is not named"
    assert "nothing is created" in group0


def test_the_resolve_step_names_every_refusal_the_script_has() -> None:
    """A refusal the procedure omits reads as a step that should have worked."""
    source = (SCRIPTS / "resolve_review_thread.py").read_text(encoding="utf-8")
    refusals = [line for line in source.splitlines() if "refus" in line.lower()]
    assert len(refusals) >= 2, "the script refuses in fewer places than the procedure claims"
    delivery = _section("Delivery")
    assert "against the current head" in delivery
    assert "still running" in delivery


def test_group0_names_each_carrier_and_asks_when_the_planner_is_unknown() -> None:
    """The provenance the issue records is a fact: an unknown planner is asked for, not assumed."""
    group0 = _group0()
    command = next(span for span in _printed_commands(group0) if "start_change.py" in span)
    assert "propose run" in command, "`--planner` does not say whose carrier it names"
    assert "ask" in group0 and "unknown" in group0


def test_the_header_promises_the_resolution_its_commands_use() -> None:
    """Every printed command resolves from the repository root: the header promises no other base."""
    skill = _skill()
    header = skill[: skill.index("## Proposal")]
    printed = _printed_commands(SKILL.read_text(encoding="utf-8"))
    assert printed
    for command in printed:
        path = command.split()[1]
        assert (ROOT / path).is_file(), command
        assert not (SKILL.parent / path).is_file(), command
    assert "repository root" in header
    assert "skill directory" not in header


def test_verify_runs_the_repository_quality_command() -> None:
    """The portable Verify step defers to the repository, which names a command that exists."""
    tasks = _section("Tasks")
    assert "quality command" in tasks and "openspec/config.yaml" in tasks
    context = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["context"]
    printed = _printed_commands(context)
    assert printed
    for command in printed:
        assert command.startswith("python "), command
        assert (ROOT / command.split()[1]).is_file(), command


def test_reviewer_adapter_reads_the_shared_contract() -> None:
    """Every file the reviewer adapter names resolves from the repository it is invoked in."""
    text = REVIEWER.read_text(encoding="utf-8")
    assert "`skills/agent-process/SKILL.md`" in text
    assert "`## Architect review`" in text and "## Architect review" in SKILL.read_text("utf-8")
    named = re.findall(r"`([\w.<>-]+(?:/[\w.<>-]+)+\.(?:md|yaml))(?:#[\w-]+)?`", text)
    paths = [path for path in named if "<" not in path]
    assert paths
    for path in paths:
        assert not path.startswith(".."), path
        assert (ROOT / path).is_file(), path
    # The reviewer reads the shape of its file from the schema, in the skill.
    assert "`skills/agent-process/architect-review.schema.json`" in text
    assert REVIEW_SCHEMA.is_file()


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
        # What does not count is what an agent otherwise records as an observation.
        "a listing, a name or an inference from another behaviour does not",
    ):
        assert part in _skill(), part


def test_spec_correction_has_its_command() -> None:
    """The delta of a spec correction is created by a command, not by describing it."""
    deliver = _section("Delivery")
    assert "new change" in deliver
    assert "never a direct edit of `openspec/specs/`" in deliver


def test_asserted_platform_fact() -> None:
    assert "asserted, not observed" in _class_description("platform")


def test_replaced_input_designed() -> None:
    for part in (
        "replaces a project-declared input",
        "failure modes",
        "stops proving",
        "which script, which run, on which head",
    ):
        assert part in _skill(), part


def test_untraceable_catcher() -> None:
    assert "the Design lists" in _class_description("replaced")
    assert "cannot trace" in _class_description("catcher")


def test_design_decision_changed_at_review() -> None:
    deliver = _section("Delivery")
    amend = deliver.index("amends the archived `design.md`")
    assert deliver.index("never a direct edit of `openspec/specs/`") < amend
    assert "scenario map in the same push" in deliver


def test_finding_closed_by_its_class() -> None:
    deliver = _section("Delivery")
    for part in (
        "closed by its class",
        "invariant",
        "takes away",
        "not the reviewer's example",
        # Where the other inputs come from, so the class is not the fixer's imagination.
        "the tool's own documentation",
    ):
        assert part in deliver, part


def test_bug_reproduction_is_named() -> None:
    """What counts as a reproduction, for the bug whose test the project cannot write."""
    proposal = _section("Proposal")
    assert "reproduction" in proposal
    assert "the failing test, or the exact observation" in proposal


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
