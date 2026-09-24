"""`activate_protection.py` (changes v2-2i-protection-activation, design D2–D4, and
v2-4a-review-protection, design D3).

One test per scenario of the `distribution` delta; the scenario name is the test name.
The script is loaded inside each test, so that a missing script fails its own scenario.
`gh` is a fake that answers by command shape and records every call.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import pytest

from tests.publisher.delivery_fakes import load_script

REPO = "owner/repo"
HEAD = "f" * 40
CONTEXT = "agent-process / quality"
REVIEW = "agent-review / agent-review"
REVIEW_APP = 15369  # distinct from quality's app id, so each context's binding is observable
NAME = "agent-process default branch"
LIVE_ID = 23732345
NEW_ID = 99
WRITES = ("POST", "PUT", "PATCH", "DELETE")
PAGE = 30  # the REST default page size of the ruleset list


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


def _run(
    conclusion: str = "success",
    slug: str = "github-actions",
    name: str = CONTEXT,
    app_id: int = 15368,
) -> dict[str, Any]:
    return {
        "name": name,
        "conclusion": conclusion,
        "app": {"slug": slug, "id": app_id if slug == "github-actions" else 777},
    }


def _review_run(conclusion: str = "success", slug: str = "github-actions") -> dict[str, Any]:
    return _run(conclusion, slug, name=REVIEW, app_id=REVIEW_APP)


def _pair(context: str, integration: int) -> dict[str, Any]:
    return {"context": context, "integration_id": integration}


class FakeGh:
    """Fake `gh` over one repository with the live shapes of design Observations."""

    def __init__(
        self,
        *,
        callers: tuple[str, ...] = ("agent-process",),
        base: str = "main",
        runs: list[dict[str, Any]] | None = None,
        rulesets: list[dict[str, Any]] | None = None,
        classic: list[str] | None = ("quality / quality", "agent-review / agent-review"),
    ) -> None:
        self.calls: list[list[str]] = []
        self.callers = callers  # the `.github/workflows/<name>.yml` on the default branch
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
            blob = {"__typename": "Blob"}
            repo = {
                "nameWithOwner": REPO,
                "defaultBranchRef": {"name": "main"},
                "object": blob if "agent-process" in self.callers else None,
                "review": blob if "agent-review" in self.callers else None,
            }
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
        endpoint = next(arg for arg in cmd[2:] if not arg.startswith("-"))
        prefix = f"repos/{REPO}/commits/{HEAD}/check-runs?check_name="
        if endpoint.startswith(prefix):
            name = unquote(endpoint.removeprefix(prefix))
            runs = [run for run in self.runs if run["name"] == name]
            return json.dumps({"total_count": len(runs), "check_runs": runs})
        if endpoint == f"repos/{REPO}/rulesets":
            listed = [
                {"id": r["id"], "name": r["name"], "source_type": r["source_type"]}
                for r in self.rulesets.values()
            ]
            pages = [listed[i : i + PAGE] for i in range(0, len(listed), PAGE)] or [[]]
            # `--paginate --slurp` prints every page wrapped in one array; without it, page 1.
            return json.dumps(pages if "--slurp" in cmd else pages[0])
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
    gh = FakeGh(callers=())
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


def test_review_caller_present(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh(
        callers=("agent-process", "agent-review"),
        runs=[_run(), _review_run()],
        rulesets=[],
        classic=None,
    )
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 0, out
    assert f"written: ruleset {NEW_ID}" in out
    (body,) = gh.inputs
    rule = next(r for r in body["rules"] if r["type"] == "required_status_checks")
    assert rule["parameters"]["required_status_checks"] == [
        _pair(CONTEXT, 15368),
        _pair(REVIEW, REVIEW_APP),
    ]


@pytest.mark.parametrize(
    ("review_runs", "observed"),
    [
        ([], "none"),
        ([_review_run(conclusion="failure")], f"{REVIEW} github-actions failure"),
        ([_review_run(slug="other-app")], f"{REVIEW} other-app success"),
    ],
    ids=["no-run", "not-success", "other-app"],
)
@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_review_context_not_observed(
    review_runs: list[dict[str, Any]],
    observed: str,
    mode: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    gh = FakeGh(callers=("agent-process", "agent-review"), runs=[_run(), *review_runs])
    code, out = _activate(gh, mode, capsys)
    assert code == 2
    (line,) = [line for line in out.splitlines() if line.startswith("refused:")]
    assert f"no successful {REVIEW} from github-actions" in line
    assert line.endswith(observed)
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


def _other(ruleset_id: int) -> dict[str, Any]:
    return {"id": ruleset_id, "name": f"other {ruleset_id}", "source_type": "Repository"}


@pytest.mark.parametrize("before", [0, PAGE], ids=["first-page", "later-page"])
def test_live_ruleset_differs(before: int, capsys: pytest.CaptureFixture[str]) -> None:
    others = [_other(i) for i in range(1, before + 1)]
    gh = FakeGh(rulesets=[*others, _served(LIVE_ID, "quality / quality")])
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


def _contexts(change):
    def mutate(body: dict[str, Any]) -> dict[str, Any]:
        rule = next(r for r in body["rules"] if r["type"] == "required_status_checks")
        checks = rule["parameters"]["required_status_checks"]
        rule["parameters"]["required_status_checks"] = change(checks)
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
        (_check("context", "quality / quality"), "required_status_checks"),
        (_check("integration_id", 1), "required_status_checks"),
        (_contexts(lambda checks: checks[:-1]), "required_status_checks"),
        (
            _contexts(lambda checks: [*checks, _pair("other / other", 15368)]),
            "required_status_checks",
        ),
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
        "lacks-context",
        "adds-context",
    ],
)
@pytest.mark.parametrize(
    ("rulesets", "written"), [(None, LIVE_ID), ([], NEW_ID)], ids=["update", "create"]
)
def test_read_back_mismatch(
    mutate, field: str, rulesets: list | None, written: int, capsys: pytest.CaptureFixture[str]
) -> None:
    gh = FakeGh(
        callers=("agent-process", "agent-review"), runs=[_run(), _review_run()], rulesets=rulesets
    )
    gh.read_back = mutate
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 1
    # The id is printed before the read-back, so a created ruleset can be rolled back.
    lines = out.splitlines()
    wrote = lines.index(f"wrote ruleset {written}; reading it back")
    assert any(line.startswith(f"error: read-back: {field} is ") for line in lines[wrote:])
    assert "written:" not in out


def test_read_back_reordered(capsys: pytest.CaptureFixture[str]) -> None:
    gh = FakeGh(callers=("agent-process", "agent-review"), runs=[_run(), _review_run()])
    gh.read_back = _contexts(lambda checks: checks[::-1])
    code, out = _activate(gh, "--confirm", capsys)
    assert code == 0, out
    assert f"written: ruleset {LIVE_ID}" in out
    served = gh.rulesets[LIVE_ID]
    rule = next(r for r in served["rules"] if r["type"] == "required_status_checks")
    assert [c["context"] for c in rule["parameters"]["required_status_checks"]] == [
        REVIEW,
        CONTEXT,
    ]
    rerun = FakeGh(
        callers=("agent-process", "agent-review"), runs=[_run(), _review_run()], rulesets=[served]
    )
    code, out = _activate(rerun, "--dry-run", capsys)
    assert code == 0, out
    assert f"unchanged {LIVE_ID}" in out.splitlines()
