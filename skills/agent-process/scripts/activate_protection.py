#!/usr/bin/env python3
"""Make the process's checks required on the default branch once they have been observed.

Usage: python skills/agent-process/scripts/activate_protection.py --pr <N> (--dry-run | --confirm)

The required contexts follow the callers on the default branch: `agent-process / quality`
always, and `agent-review / agent-review` when `.github/workflows/agent-review.yml` exists.
A required check that never reported blocks every merge (PR 151, run 35523639249), so the
run first reads these facts and refuses (exit 2) without them: the default branch carries
`.github/workflows/agent-process.yml`, and the current head of PR <N> against that branch
has, for each context, a check run that GitHub Actions concluded `success`. That run's app
id becomes the context's `integration_id`.

Then it plans one repository ruleset named `agent-process default branch` from
`templates/ruleset.json`: `planned create`, `planned update <id>` with one line per differing
owned field, or `unchanged <id>`; each `planned` line is followed by its rollback command.
Only the fields the template sets are owned — keys the server adds are neither compared nor
written. Several rulesets of that name, or one the repository does not own, are a
`conflict` (exit 2) before any write. Classic branch protection is read and printed, never
written. `--dry-run` stops there with reads only; `--confirm` writes the one `POST` or
`PUT`, then reads the ruleset back and exits 1 naming the first field that differs. The
required contexts are compared sorted by context, whatever order the server returns. A `gh`
failure is exit 1.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from set_status import Gh, _json, run_gh

CALLER = ".github/workflows/agent-process.yml"
CONTEXT = "agent-process / quality"
REVIEW_CALLER = ".github/workflows/agent-review.yml"
REVIEW_CONTEXT = "agent-review / agent-review"
APP = "github-actions"
NAME = "agent-process default branch"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "ruleset.json"
BARRIERS = ("pull_request", "deletion", "non_fast_forward", "required_status_checks")
QUERY = (
    "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){"
    "nameWithOwner defaultBranchRef{name} "
    f'object(expression:"HEAD:{CALLER}"){{__typename}} '
    f'review:object(expression:"HEAD:{REVIEW_CALLER}"){{__typename}}}}}}'
)
Check = tuple[str, int]  # a required context and the integration id bound to it


class Refusal(Exception):
    """A precondition or a conflict: exit 2, nothing written."""


def contexts(review_caller: bool) -> list[str]:
    """The required contexts, given whether the default branch carries the review caller."""
    return [CONTEXT, REVIEW_CONTEXT] if review_caller else [CONTEXT]


def _observed(gh: Gh, repo: str, pr: int, head: str, context: str) -> Check:
    """The context bound to the app of its successful GitHub Actions run on `head`."""
    runs = _json(
        gh, ["gh", "api", f"repos/{repo}/commits/{head}/check-runs?check_name={quote(context)}"]
    )["check_runs"]
    for run in runs:
        app = run.get("app") or {}
        if (run.get("name"), app.get("slug"), run.get("conclusion")) == (context, APP, "success"):
            return context, int(app["id"])
    seen = "; ".join(
        f"{run.get('name')} {(run.get('app') or {}).get('slug')} {run.get('conclusion')}"
        for run in runs
    )
    raise Refusal(
        f"refused: no successful {context} from {APP} on {head[:8]} of PR {pr}: {seen or 'none'}"
    )


def preflight(gh: Gh, pr: int) -> tuple[str, str, list[Check]]:
    """The repository, its default branch and each required context with its integration id."""
    data = _json(
        gh,
        [
            "gh",
            "api",
            "graphql",
            "-F",
            "owner={owner}",
            "-F",
            "name={repo}",
            "-f",
            f"query={QUERY}",
        ],
    )["data"]["repository"]
    repo, branch = str(data["nameWithOwner"]), str(data["defaultBranchRef"]["name"])
    if data["object"] is None:
        raise Refusal(f"refused: caller absent on {branch}: {CALLER}")
    view = _json(gh, ["gh", "pr", "view", str(pr), "--json", "headRefOid,baseRefName"])
    if view["baseRefName"] != branch:
        raise Refusal(
            f"refused: PR {pr} has base {view['baseRefName']}, not the default branch {branch}"
        )
    head = str(view["headRefOid"])
    wanted = contexts(data["review"] is not None)
    return repo, branch, [_observed(gh, repo, pr, head, context) for context in wanted]


def _fill(node: Any, values: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        return {key: _fill(value, values) for key, value in node.items()}
    if isinstance(node, list):
        return [_fill(item, values) for item in node]
    if isinstance(node, str):
        for placeholder, value in values.items():
            if node == placeholder:
                return value
            if isinstance(value, str):
                node = node.replace(placeholder, value)
    return node


def _required(checks: list[Check]) -> list[dict[str, Any]]:
    return [{"context": context, "integration_id": integration} for context, integration in checks]


def _by_context(required: Any) -> Any:
    """A required-checks list sorted by context: the server's order is not compared."""
    if not isinstance(required, list):
        return required
    return sorted(required, key=lambda check: str((check or {}).get("context")))


def desired(branch: str, checks: list[Check]) -> dict[str, Any]:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    values = {"__DEFAULT_BRANCH__": branch, "__REQUIRED_CHECKS__": _required(checks)}
    return _fill(template, values)


def _parameter_keys(body: dict[str, Any]) -> dict[str, list[str]]:
    """The rule parameters the template sets, per rule type: the owned ones."""
    return {
        rule["type"]: list(rule["parameters"]) for rule in body["rules"] if "parameters" in rule
    }


def owned_fields(body: dict[str, Any], want: dict[str, Any]) -> dict[str, Any]:
    """The fields of `body` that `want` (the template) owns, by a dotted name."""
    fields = {key: body.get(key) for key in ("name", "target", "enforcement", "bypass_actors")}
    fields["conditions.ref_name"] = (body.get("conditions") or {}).get("ref_name")
    rules = {rule.get("type"): rule.get("parameters") or {} for rule in body.get("rules") or []}
    fields["rules"] = sorted(str(kind) for kind in rules)
    for kind, keys in _parameter_keys(want).items():
        for key in keys:
            value = rules.get(kind, {}).get(key)
            if key == "required_status_checks":
                value = _by_context(value)
            fields[f"{kind}.{key}"] = value
    return fields


def owned_body(live: dict[str, Any], want: dict[str, Any]) -> dict[str, Any]:
    """The live ruleset as a `PUT` body restricted to the owned fields: the rollback."""
    keys = _parameter_keys(want)
    rules = []
    for rule in live.get("rules") or []:
        kept = {"type": rule["type"]}
        if "parameters" in rule:
            params = rule["parameters"]
            owned = keys.get(rule["type"])
            kept["parameters"] = params if owned is None else {k: params.get(k) for k in owned}
        rules.append(kept)
    body = {key: live.get(key) for key in ("name", "target", "enforcement", "bypass_actors")}
    return body | {"conditions": {"ref_name": live["conditions"]["ref_name"]}, "rules": rules}


def _compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def plan(gh: Gh, repo: str, want: dict[str, Any]) -> tuple[str, int | None, list[str]]:
    """`create`, `update` or `unchanged`, the ruleset id, and the lines to print."""
    # Every page: a ruleset of that name past the first page must not look absent (create).
    pages = _json(gh, ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/rulesets"])
    named = [r for page in pages for r in page if r.get("name") == NAME]
    if len(named) > 1 or (named and named[0].get("source_type") != "Repository"):
        listed = ", ".join(f"{r.get('id')} {r.get('source_type')}" for r in named)
        raise Refusal(f'conflict: rulesets named "{NAME}": {listed}')
    if not named:
        return (
            "create",
            None,
            [
                f'planned create "{NAME}"',
                f"rollback: gh api -X DELETE repos/{repo}/rulesets/<id printed by the write>",
            ],
        )
    ruleset_id = int(named[0]["id"])
    live = _json(gh, ["gh", "api", f"repos/{repo}/rulesets/{ruleset_id}"])
    have, need = owned_fields(live, want), owned_fields(want, want)
    diffs = [
        f"  {field}: {_compact(have[field])} -> {_compact(need[field])}"
        for field in need
        if have[field] != need[field]
    ]
    if not diffs:
        return "unchanged", ruleset_id, [f"unchanged {ruleset_id}"]
    rollback = (
        f"rollback: echo '{_compact(owned_body(live, want))}' | "
        f"gh api -X PUT repos/{repo}/rulesets/{ruleset_id} --input -"
    )
    return "update", ruleset_id, [f"planned update {ruleset_id}", *diffs, rollback]


def classic(gh: Gh, repo: str, branch: str) -> str:
    """The required contexts of classic protection as read; an unprotected branch is none."""
    try:
        data = _json(gh, ["gh", "api", f"repos/{repo}/branches/{branch}/protection"])
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise
        return "classic: none (not written)"
    checks = data.get("required_status_checks") or {}
    contexts = [c["context"] for c in checks.get("checks") or []] or checks.get("contexts") or []
    return f"classic: {', '.join(contexts) or 'none'} (not written)"


def write(gh: Gh, repo: str, ruleset_id: int | None, body: dict[str, Any]) -> int:
    """One `POST` (no id) or `PUT`; the id the server answers with."""
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(body, handle)
        if ruleset_id is None:
            cmd = ["gh", "api", "-X", "POST", f"repos/{repo}/rulesets", "--input", path]
        else:
            cmd = ["gh", "api", "-X", "PUT", f"repos/{repo}/rulesets/{ruleset_id}", "--input", path]
        return int(_json(gh, cmd)["id"])
    finally:
        os.unlink(path)


def read_back(gh: Gh, repo: str, ruleset_id: int, branch: str, written: list[Check]) -> None:
    """Raise on the first field of the written ruleset that differs, in design D4's order."""
    live = _json(gh, ["gh", "api", f"repos/{repo}/rulesets/{ruleset_id}"])
    ref = (live.get("conditions") or {}).get("ref_name") or {}
    rules = {rule.get("type"): rule.get("parameters") or {} for rule in live.get("rules") or []}
    checks = rules.get("required_status_checks", {})
    required = checks.get("required_status_checks")
    expected: list[tuple[str, Any, bool]] = [
        ("enforcement", live.get("enforcement"), live.get("enforcement") == "active"),
        (
            "conditions.ref_name.include",
            ref.get("include"),
            ref.get("include") == [f"refs/heads/{branch}"],
        ),
        ("conditions.ref_name.exclude", ref.get("exclude"), ref.get("exclude") == []),
        ("bypass_actors", live.get("bypass_actors"), live.get("bypass_actors") == []),
        *((f"rules.{kind}", "absent", kind in rules) for kind in BARRIERS),
        (
            "strict_required_status_checks_policy",
            checks.get("strict_required_status_checks_policy"),
            checks.get("strict_required_status_checks_policy") is True,
        ),
        (
            "required_status_checks",
            required,
            _by_context(required) == _by_context(_required(written)),
        ),
    ]
    for field, observed, ok in expected:
        if not ok:
            raise RuntimeError(f"read-back: {field} is {_compact(observed)}")


def activate(pr: int, *, confirm: bool, gh: Gh) -> None:
    repo, branch, checks = preflight(gh, pr)
    want = desired(branch, checks)
    action, ruleset_id, lines = plan(gh, repo, want)
    lines.append(classic(gh, repo, branch))
    print("\n".join(lines))
    if not confirm or action == "unchanged":
        return
    written = write(gh, repo, ruleset_id, want)
    # Printed before the read-back: a created ruleset's rollback needs this id.
    print(f"wrote ruleset {written}; reading it back", flush=True)
    read_back(gh, repo, written, branch, checks)
    print(f"written: ruleset {written}")


def main(argv: list[str] | None = None, *, gh: Gh = run_gh) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pr", type=int, required=True, help="PR whose head reported the check")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="plan with reads only")
    mode.add_argument("--confirm", action="store_true", help="write the plan, then read it back")
    ns = parser.parse_args(argv)
    try:
        activate(ns.pr, confirm=ns.confirm, gh=gh)
    except Refusal as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
    except (RuntimeError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
