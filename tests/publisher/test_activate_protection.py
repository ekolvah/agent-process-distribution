"""`activate_protection.py` (change v2-2i-protection-activation, design D2–D4).

One test per scenario of the `distribution` delta; the scenario name is the test name.
The script is loaded inside each test, so that a missing script fails its own scenario.
`gh` is a fake that answers by command shape and records every call.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import load_script

REPO = "owner/repo"
HEAD = "f" * 40
CONTEXT = "agent-process / quality"
NAME = "agent-process default branch"
LIVE_ID = 23732345
NEW_ID = 99
WRITES = ("POST", "PUT", "PATCH", "DELETE")


def _rules(context: str, integration: int = 15368) -> list[dict[str, Any]]:
    return [
        {"type": "deletion"},
        {"type": "non_fast_forward"},
        {
            "type": "pull_request",
            "parameters": {
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_approving_review_count": 0,
                "required_review_thread_resolution": False,
            },
        },
        {
            "type": "required_status_checks",
            "parameters": {
                "strict_required_status_checks_policy": True,
                "do_not_enforce_on_create": False,
                "required_status_checks": [{"context": context, "integration_id": integration}],
            },
        },
    ]


def _served(ruleset_id: int, context: str) -> dict[str, Any]:
    """A ruleset as the server returns it: owned fields plus the keys the server adds."""
    rules = _rules(context)
    rules[2]["parameters"] |= {
        "require_extra_approval_for_unattributed_changes": True,
        "allowed_merge_methods": ["merge", "squash", "rebase"],
    }
    return {
        "id": ruleset_id,
        "name": NAME,
        "target": "branch",
        "source_type": "Repository",
        "source": REPO,
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "bypass_actors": [],
        "rules": rules,
        "current_user_can_bypass": "never",
    }


def _run(conclusion: str = "success", slug: str = "github-actions") -> dict[str, Any]:
    return {
        "name": CONTEXT,
        "conclusion": conclusion,
        "app": {"slug": slug, "id": 15368 if slug == "github-actions" else 777},
    }


class FakeGh:
    """Fake `gh` over one repository with the live shapes of design Observations."""

    def __init__(
        self,
        *,
        caller: bool = True,
        base: str = "main",
        runs: list[dict[str, Any]] | None = None,
        rulesets: list[dict[str, Any]] | None = None,
        classic: list[str] | None = ("quality / quality", "agent-review / agent-review"),
    ) -> None:
        self.calls: list[list[str]] = []
        self.caller = caller
        self.base = base
        self.runs = [_run()] if runs is None else runs
        self.rulesets = (
            {LIVE_ID: _served(LIVE_ID, "quality / quality")}
            if rulesets is None
            else {r["id"]: r for r in rulesets}
        )
        self.classic = classic
        self.read_back: Any = None  # mutates the ruleset the next GET returns after a write
        self.inputs: list[dict[str, Any]] = []

    def writes(self) -> list[list[str]]:
        return [c for c in self.calls if "-X" in c and c[c.index("-X") + 1] in WRITES]

    def _written(self, cmd: list[str], ruleset_id: int) -> str:
        body = json.loads(Path(cmd[cmd.index("--input") + 1]).read_text(encoding="utf-8"))
        self.inputs.append(body)
        served = copy.deepcopy(body) | {"id": ruleset_id, "source_type": "Repository"}
        self.rulesets[ruleset_id] = served if self.read_back is None else self.read_back(served)
        return json.dumps(served)

    def __call__(self, cmd: list[str]) -> str:
        self.calls.append(cmd)
        if cmd[:3] == ["gh", "api", "graphql"]:
            obj = {"__typename": "Blob"} if self.caller else None
            repo = {"nameWithOwner": REPO, "defaultBranchRef": {"name": "main"}, "object": obj}
            return json.dumps({"data": {"repository": repo}})
        if cmd[:3] == ["gh", "pr", "view"]:
            return json.dumps({"headRefOid": HEAD, "baseRefName": self.base})
        if "-X" in cmd:
            return self._write(cmd)
        return self._read(cmd)

    def _write(self, cmd: list[str]) -> str:
        method, endpoint = cmd[cmd.index("-X") + 1 : cmd.index("-X") + 3]
        if method == "POST" and endpoint == f"repos/{REPO}/rulesets":
            return self._written(cmd, NEW_ID)
        if method == "PUT":
            return self._written(cmd, int(endpoint.rsplit("/", 1)[1]))
        raise AssertionError(f"unexpected write: {cmd}")

    def _read(self, cmd: list[str]) -> str:
        endpoint = cmd[2]
        if (
            endpoint
            == f"repos/{REPO}/commits/{HEAD}/check-runs?check_name=agent-process%20/%20quality"
        ):
            return json.dumps({"total_count": len(self.runs), "check_runs": self.runs})
        if endpoint == f"repos/{REPO}/rulesets":
            return json.dumps(
                [
                    {"id": r["id"], "name": r["name"], "source_type": r["source_type"]}
                    for r in self.rulesets.values()
                ]
            )
        if endpoint.startswith(f"repos/{REPO}/rulesets/"):
            return json.dumps(self.rulesets[int(endpoint.rsplit("/", 1)[1])])
        if endpoint == f"repos/{REPO}/branches/main/protection":
            if self.classic is None:
                raise RuntimeError(
                    f"`{' '.join(cmd)}` failed (rc=1): gh: Branch not protected (HTTP 404)"
                )
            checks = [{"context": c, "app_id": 15368} for c in self.classic]
            return json.dumps({"required_status_checks": {"strict": True, "checks": checks}})
        raise AssertionError(f"unexpected gh call: {cmd}")


def _activate(gh: FakeGh, mode: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    module = load_script("activate_protection")
    with pytest.raises(SystemExit) as exc:
        module.main(["--pr", "165", mode], gh=gh)
    captured = capsys.readouterr()
    return int(exc.value.code or 0), captured.out + captured.err


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_caller_absent(mode: str, capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh(caller=False)
    code, out = _activate(gh, mode, capsys)
    assert code == 2
    assert "caller absent on main: .github/workflows/agent-process.yml" in out
    assert gh.writes() == []


@pytest.mark.parametrize(
    ("gh", "observed"),
    [
        (FakeGh(base="develop"), "base develop, not the default branch main"),
        (FakeGh(runs=[]), "none"),
        (FakeGh(runs=[_run(conclusion="failure")]), f"{CONTEXT} github-actions failure"),
        (FakeGh(runs=[_run(slug="other-app")]), f"{CONTEXT} other-app success"),
    ],
    ids=["other-base", "no-run", "not-success", "other-app"],
)
def test_context_not_observed(
    gh: FakeGh, observed: str, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 2
    assert observed in out
    assert gh.writes() == []


def test_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh()
    code, out = _activate(gh, "--dry-run", capsys)
    assert code == 0
    lines = out.splitlines()
    planned = lines.index(f"planned update {LIVE_ID}")
    assert any(
        "required_status_checks" in line and "quality / quality" in line and CONTEXT in line
        for line in lines[planned + 1 :]
    )
    rollback = next(line for line in lines[planned + 1 :] if line.startswith("rollback: "))
    assert f"gh api -X PUT repos/{REPO}/rulesets/{LIVE_ID} --input -" in rollback
    assert '"quality / quality"' in rollback
    assert "classic: quality / quality, agent-review / agent-review (not written)" in lines
    assert gh.writes() == []


def test_no_ruleset_yet(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh(rulesets=[], classic=None)
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 0, out
    assert f'planned create "{NAME}"' in out
    assert f"rollback: gh api -X DELETE repos/{REPO}/rulesets/<id printed by the write>" in out
    assert "classic: none (not written)" in out
    assert f"written: ruleset {NEW_ID}" in out
    assert [c[:5] for c in gh.writes()] == [["gh", "api", "-X", "POST", f"repos/{REPO}/rulesets"]]
    (body,) = gh.inputs
    assert body["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    assert body["rules"] == _rules(CONTEXT)


def test_live_ruleset_differs(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh()
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 0, out
    assert f"written: ruleset {LIVE_ID}" in out
    assert [c[:5] for c in gh.writes()] == [
        ["gh", "api", "-X", "PUT", f"repos/{REPO}/rulesets/{LIVE_ID}"]
    ]
    assert gh.inputs[0]["rules"] == _rules(CONTEXT)


def test_rerun(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh(rulesets=[_served(LIVE_ID, CONTEXT)])
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 0, out
    assert f"unchanged {LIVE_ID}" in out.splitlines()
    assert "planned" not in out
    assert gh.writes() == []


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
@pytest.mark.parametrize(
    ("rulesets", "named"),
    [
        ([_served(LIVE_ID, CONTEXT), _served(7, CONTEXT)], [f"{LIVE_ID}", "7"]),
        (
            [_served(LIVE_ID, CONTEXT) | {"source_type": "Organization"}],
            [f"{LIVE_ID} Organization"],
        ),
    ],
    ids=["two-rulesets", "not-repository"],
)
def test_ambiguous_rulesets(
    rulesets: list[dict[str, Any]], named: list[str], mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGh(rulesets=rulesets)
    code, out = _activate(gh, mode, capsys)
    assert code == 2
    (line,) = [line for line in out.splitlines() if line.startswith("conflict")]
    assert all(token in line for token in named)
    assert gh.writes() == []


def _drop_rule(kind: str):
    def mutate(body: dict[str, Any]) -> dict[str, Any]:
        body["rules"] = [r for r in body["rules"] if r["type"] != kind]
        return body

    return mutate


def _check(key: str, value: Any):
    def mutate(body: dict[str, Any]) -> dict[str, Any]:
        rule = next(r for r in body["rules"] if r["type"] == "required_status_checks")
        if key == "strict_required_status_checks_policy":
            rule["parameters"][key] = value
        else:
            rule["parameters"]["required_status_checks"][0][key] = value
        return body

    return mutate


def _set(path: tuple[str, ...], value: Any):
    def mutate(body: dict[str, Any]) -> dict[str, Any]:
        node = body
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return body

    return mutate


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (_set(("enforcement",), "evaluate"), "enforcement"),
        (
            _set(("conditions", "ref_name", "include"), ["refs/heads/x"]),
            "conditions.ref_name.include",
        ),
        (
            _set(("conditions", "ref_name", "exclude"), ["refs/heads/x"]),
            "conditions.ref_name.exclude",
        ),
        (
            _set(("bypass_actors",), [{"actor_id": 5, "actor_type": "RepositoryRole"}]),
            "bypass_actors",
        ),
        (_drop_rule("pull_request"), "rules.pull_request"),
        (_drop_rule("deletion"), "rules.deletion"),
        (_drop_rule("non_fast_forward"), "rules.non_fast_forward"),
        (_drop_rule("required_status_checks"), "rules.required_status_checks"),
        (
            _check("strict_required_status_checks_policy", False),
            "strict_required_status_checks_policy",
        ),
        (_check("context", "quality / quality"), "required_status_checks.context"),
        (_check("integration_id", 1), "required_status_checks.integration_id"),
    ],
    ids=[
        "enforcement",
        "ref-include",
        "ref-exclude",
        "bypass",
        "pull-request",
        "deletion",
        "non-fast-forward",
        "status-checks",
        "strict",
        "context",
        "integration",
    ],
)
def test_read_back_mismatch(mutate, field: str, capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh()
    gh.read_back = mutate
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 1
    assert f"read-back: {field} is " in out
    assert "written:" not in out
