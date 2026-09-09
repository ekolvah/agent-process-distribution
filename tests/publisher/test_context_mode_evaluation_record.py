"""Completeness contract for the Stage A evaluation record of Context Mode (issue #92).

**What is guarded.** A research issue whose only deliverable is a decision record has no
production behaviour to test, so the record itself is the artifact — and an incomplete record
is the failure mode: a verdict recorded for the stop conditions that fired while the ones that
did not are quietly absent, a decision with no rollback, a `retain` outcome with no follow-up.
The issue's own acceptance criteria name every field the record owes; this turns that list into
an exit code rather than a review checklist someone remembers to apply (goal function,
"scripts over instructions").

**Why a labelled block rather than headings.** The repository already validates
`## Evidence` and `## Prior art` as labelled lines in the issue body, so the record reuses that
idiom instead of inventing a second one. A heading can be present and empty; a labelled line
carries its own content on the same line, which makes "present but unfilled" detectable.

**Why the template copy.** `template/.agent-process/docs/adr/` is the source of truth and the
rendered root copy is generated from it. Asserting the contract on the source, and letting
`tests/publisher/test_template_drift.py` prove the root copy matches it, keeps one assertion in
one place; asserting on both would duplicate what the drift gate already owns.

**Why publisher-only.** The assertion names one specific record, not a rendered answer or a
contract depending on a consumer's own files, so §Test suite ownership places it here. Shipped
to consumers it would be actively wrong: a consumer that prunes a record irrelevant to their
repository would inherit a red test about this repository's tool-evaluation history. The
architect review proposed a `tests/agent_process/` node with a `template/` twin to satisfy the
drift gate; the gate is satisfied instead by the explicit `root_only_paths` row in
`template-drift-allowlist.yml`, which records the reason where a reader will look for it.

**Cross-field consistency, not just presence.** Presence alone would admit a record that
contradicts itself — a fired stop condition beside an `adopt` decision. The rules below make
that combination fail, which is the part of this guard that a human reviewer most reliably
misses.

**Guard boundaries, honestly.** Presence and internal consistency are deterministic; truth is
not. Nothing here can tell an honest verdict from a fabricated one, and `metric:` is checked
only for naming both units it must keep apart — a line mentioning bytes and tokens can still
draw the wrong conclusion between them. A person catches that in review. The guard exists so
that a *missing* field cannot pass as a considered one (§IV).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECORD = (
    ROOT
    / "template"
    / ".agent-process"
    / "docs"
    / "adr"
    / "0025-context-mode-token-efficiency-evaluation.md"
)

# The pinned snapshot the issue fixed before any work began. Hard-coded here so that editing
# the record cannot silently re-point the evaluation at a different upstream state.
SNAPSHOT_COMMIT = "95b4e08bf07c5e16690d8669643f9d1b825d51be"  # pragma: allowlist secret
SNAPSHOT_PACKAGE = "context-mode@1.0.169"
SNAPSHOT_DIGEST = "sha512-94JIaFuLjF9SO2BsGTrbGtyT44K95+9OC8BdbaL/UT76xOkanJLfUR5CzmNw+GELXZQqH4nBrKg9wjBnSFkVnQ=="  # pragma: allowlist secret

STOP_LABELS = ("stop-1", "stop-2", "stop-3")
OPEN_LABELS = ("open-a", "open-b")
REQUIRED_LABELS = (
    "snapshot-commit",
    "snapshot-package",
    "snapshot-digest",
    "route",
    "metric",
    *STOP_LABELS,
    "licence",
    "revives-if",
    *OPEN_LABELS,
    "decision",
    "rollback",
    "follow-up",
)

STOP_VERDICTS = ("fired", "not-fired")
OPEN_VERDICTS = ("open", "closed")
DECISIONS = (
    "not planned",
    "retain for future re-evaluation",
    "adopt through a separate narrow issue",
)

_LABEL = re.compile(r"^(?P<label>[a-z][a-z0-9-]*):[ \t]*(?P<value>.*)$")


def fields(text: str) -> dict[str, list[str]]:
    """Every `label: value` line in the record, keyed by label.

    A list rather than a single value: a duplicated label is a defect this guard reports, and
    collapsing duplicates here would hide it.
    """
    found: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _LABEL.match(line.strip())
        if match is None:
            continue
        found.setdefault(match["label"], []).append(match["value"].strip())
    return found


def verdict_of(value: str, allowed: tuple[str, ...]) -> str | None:
    """The verdict word a labelled line opens with, or `None` when it opens with none.

    Longest match first, so `not-fired` is never read as the prefix of a shorter alternative.
    """
    for candidate in sorted(allowed, key=len, reverse=True):
        if value == candidate or value.startswith(f"{candidate} "):
            return candidate
    return None


def value_of(record_fields: dict[str, list[str]], label: str) -> str:
    """The single value recorded for `label`, or `""` when the record omits it.

    Absence returns a value rather than raising so that a missing field surfaces as a failing
    assertion in the test body. A `KeyError` here would be reported against the fixture, and a
    suite that errors before it runs does not count as RED (`testing.md` §1).
    """
    return next(iter(record_fields.get(label, [])), "")


@pytest.fixture(scope="module")
def record_text() -> str:
    """The record's text, or `""` when it does not exist yet — see `value_of`."""
    if not RECORD.is_file():
        return ""
    return RECORD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def record_fields(record_text: str) -> dict[str, list[str]]:
    return fields(record_text)


def test_record_exists() -> None:
    assert RECORD.is_file(), (
        f"missing evaluation record: {RECORD.relative_to(ROOT).as_posix()} — "
        "issue #92 delivers this record as its only artifact"
    )


class TestFieldsArePresentAndFilled:
    @pytest.mark.parametrize("label", REQUIRED_LABELS)
    def test_label_appears_exactly_once(
        self, record_fields: dict[str, list[str]], label: str
    ) -> None:
        occurrences = record_fields.get(label, [])
        assert len(occurrences) == 1, (
            f"`{label}:` appears {len(occurrences)} times; the record owes exactly one"
        )

    @pytest.mark.parametrize("label", REQUIRED_LABELS)
    def test_label_carries_content(self, record_fields: dict[str, list[str]], label: str) -> None:
        assert value_of(record_fields, label), f"`{label}:` is present but empty"


class TestSnapshotIsThePinnedOne:
    def test_commit(self, record_fields: dict[str, list[str]]) -> None:
        assert value_of(record_fields, "snapshot-commit") == SNAPSHOT_COMMIT

    def test_package(self, record_fields: dict[str, list[str]]) -> None:
        assert value_of(record_fields, "snapshot-package") == SNAPSHOT_PACKAGE

    def test_digest(self, record_fields: dict[str, list[str]]) -> None:
        assert value_of(record_fields, "snapshot-digest") == SNAPSHOT_DIGEST


class TestVerdictsComeFromClosedSets:
    @pytest.mark.parametrize("label", STOP_LABELS)
    def test_stop_condition_verdict(self, record_fields: dict[str, list[str]], label: str) -> None:
        value = value_of(record_fields, label)
        assert verdict_of(value, STOP_VERDICTS) is not None, (
            f"`{label}:` must open with one of {STOP_VERDICTS}, not {value!r} — "
            "a condition that did not fire is recorded, not omitted"
        )

    @pytest.mark.parametrize("label", OPEN_LABELS)
    def test_open_condition_verdict(self, record_fields: dict[str, list[str]], label: str) -> None:
        value = value_of(record_fields, label)
        assert verdict_of(value, OPEN_VERDICTS) is not None, (
            f"`{label}:` must open with one of {OPEN_VERDICTS}, not {value!r}"
        )

    @pytest.mark.parametrize("label", (*STOP_LABELS, *OPEN_LABELS))
    def test_verdict_carries_its_evidence(
        self, record_fields: dict[str, list[str]], label: str
    ) -> None:
        allowed = STOP_VERDICTS if label in STOP_LABELS else OPEN_VERDICTS
        value = value_of(record_fields, label)
        verdict = verdict_of(value, allowed)
        assert verdict is not None and value != verdict, (
            f"`{label}:` states a verdict with no evidence after it"
        )

    def test_decision_is_one_of_three(self, record_fields: dict[str, list[str]]) -> None:
        value = value_of(record_fields, "decision")
        assert verdict_of(value, DECISIONS) is not None, (
            f"`decision:` must open with one of {DECISIONS}, not {value!r}"
        )


class TestRecordDoesNotContradictItself:
    def test_a_fired_stop_condition_forces_not_planned(
        self, record_fields: dict[str, list[str]]
    ) -> None:
        fired = [
            label
            for label in STOP_LABELS
            if verdict_of(value_of(record_fields, label), STOP_VERDICTS) == "fired"
        ]
        if not fired:
            pytest.skip("no stop condition fired")
        assert verdict_of(value_of(record_fields, "decision"), DECISIONS) == "not planned", (
            f"{', '.join(fired)} fired, so the decision can only be `not planned`"
        )

    def test_an_open_condition_forbids_adoption(self, record_fields: dict[str, list[str]]) -> None:
        still_open = [
            label
            for label in OPEN_LABELS
            if verdict_of(value_of(record_fields, label), OPEN_VERDICTS) == "open"
        ]
        if not still_open:
            pytest.skip("no condition left open")
        assert (
            verdict_of(value_of(record_fields, "decision"), DECISIONS)
            != "adopt through a separate narrow issue"
        ), (
            f"{', '.join(still_open)} is unresolved, which caps the outcome at "
            "`retain for future re-evaluation`"
        )

    def test_follow_up_matches_the_decision(self, record_fields: dict[str, list[str]]) -> None:
        decision = verdict_of(value_of(record_fields, "decision"), DECISIONS)
        follow_up = value_of(record_fields, "follow-up")
        if decision == "not planned":
            assert follow_up.startswith("none:"), (
                "a `not planned` decision opens no follow-up; record `none: <reason>`"
            )
        else:
            assert re.search(r"#\d+", follow_up), (
                f"a `{decision}` decision owes a tracked follow-up issue reference"
            )


class TestMetricBoundaryIsStated:
    def test_metric_names_both_units_it_separates(
        self, record_fields: dict[str, list[str]]
    ) -> None:
        value = value_of(record_fields, "metric").lower()
        assert "byte" in value and "token" in value, (
            "`metric:` must name both units it keeps apart — the upstream figure is a byte "
            "ratio and may never be reported as a token or cost saving"
        )


class TestLicenceIsRecordedAsAFactWithARevivalTrigger:
    def test_licence_names_the_licence(self, record_fields: dict[str, list[str]]) -> None:
        assert "Elastic-2.0" in value_of(record_fields, "licence")

    def test_revival_trigger_is_not_a_stop_condition(
        self, record_fields: dict[str, list[str]]
    ) -> None:
        """The licence has no `stop-*` label: local development use is unrestricted under it.

        The stop conditions are asserted present first, so an empty record fails here instead of
        passing vacuously — `check_red.py` treats a vacuous pass as a test that never went RED.
        """
        stop_values = [value_of(record_fields, label) for label in STOP_LABELS]
        assert all(stop_values), (
            "every stop condition must be recorded before the licence's place among them "
            "can be judged"
        )
        assert not any(
            "licence" in value.lower() or "elastic" in value.lower() for value in stop_values
        ), "the licence is recorded as a fact with a revival trigger, not gated as a stop condition"
