"""The `manual` rows of `init.py` (change manual-rows-from-state); not a command. Each row is
work only a UI, the machine or the clone can do, printed while its state is not observed done.
Every read is guarded: a state it cannot read keeps its row with `(cannot read: <reason>)`,
and no read writes or fails the run."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# The built-in workflows of the template by API name, with their targets (the `state` spec's
# template requirement); the API exposes only a workflow's name and whether it is enabled.
WORKFLOWS = {
    "Auto-add to project": "Auto-add to project (this repository)",
    "Item added to project": "Item added -> Todo",
    "Item reopened": "Item reopened -> Todo",
    "Item closed": "Item closed -> Done",
    "Pull request merged": "Pull request merged -> Done",
}
AREA = 'field(name:"Area"){... on ProjectV2SingleSelectField{options{name}}}'
# The linked Project's state the rows depend on, and the template's `Area` options.
QUERY = (
    "query($owner:String!,$number:Int!,$template:String!,$source:Int!){"
    "linked:repositoryOwner(login:$owner){... on ProjectV2Owner{projectV2(number:$number){"
    f"public workflows(first:50){{nodes{{name enabled}}}} {AREA}}}}}}}"
    "template:repositoryOwner(login:$template){... on ProjectV2Owner{projectV2(number:$source){"
    f"{AREA}}}}}}}}}"
)
REVIEW_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
# The line pre-commit writes into every hook it installs (observed 2026-09-30).
PRE_COMMIT_ID = "# ID: 138fd403232d2ddd5efb44317e38bf03"

Read = Callable[..., "subprocess.CompletedProcess[str]"]


class Unreadable(Exception):
    """A row's state `init` cannot read; the row is printed with this reason."""


@dataclass
class Target:
    """The consumer `owner/name` and the reads the rows need: `gh` and `git` (in the clone)
    return a completion whatever its exit code. `source` is the process repository whose
    `marketplace` and `plugin` the machine should follow; `template` is the template Project's
    owner and number; `pre_commit` is the `pre-commit` on PATH, if any."""

    repo: str
    root: Path
    home: Path
    gh: Read
    git: Read
    template: tuple[str, str]
    source: str
    marketplace: str
    plugin: str
    pre_commit: str | None


def rows(t: Target) -> list[str]:
    """The outstanding rows, read after the run's writes."""
    found: list[str] = []
    url, why = None, ""
    try:
        owner, number, url = _linked(t)
        public, missing, same = _project_state(t, owner, number)
    except Unreadable as exc:
        public, missing, same, why = False, list(WORKFLOWS), True, f" (cannot read: {exc})"
    where = url or "the new copy"
    if not public:
        found.append(
            f"manual project-visibility: {where}/settings -- a copy is private; "
            f"set its visibility as intended{why}"
        )
    if missing:
        enable = ", ".join(WORKFLOWS[name] for name in missing)
        found.append(f"manual project-workflows: {where}/workflows -- enable {enable}{why}")
    if same:
        found.append(
            f"manual project-areas: {where}/settings -- replace the Area options and the area "
            f"views with this repository's own{why}"
        )
    return [
        *found,
        *_outstanding(
            lambda: _secret_set(t),
            f"manual review-secret: https://github.com/{t.repo}/settings/secrets/actions -- "
            f"claude setup-token, then gh secret set {REVIEW_TOKEN} -R {t.repo} and paste the "
            "token at its prompt; the review caller passes it to the review",
        ),
        *_outstanding(
            lambda: _plugin_channel(t),
            "manual plugin-channel: once per machine -- claude plugin marketplace add "
            f'"{t.source}#stable", then /plugin -> Marketplaces -> '
            f"Enable auto-update for {t.marketplace}, then claude plugin install {t.plugin}",
        ),
        *_pre_push_row(t),
    ]


def _outstanding(done: Callable[[], bool], row: str) -> list[str]:
    try:
        return [] if done() else [row]
    except Unreadable as exc:
        return [f"{row} (cannot read: {exc})"]


def _gh_read(t: Target, *args: str) -> Any:
    """A `gh` read's JSON whatever its exit code (a GraphQL error beside `data` exits 1), or
    `Unreadable` with its stderr."""
    done = t.gh(*args)
    try:
        return json.loads(done.stdout)
    except (TypeError, json.JSONDecodeError):
        lines = (done.stderr or "").strip().splitlines()
        raise Unreadable(
            lines[0] if lines else f"`gh {args[0]} {args[1]}` printed no JSON"
        ) from None


def _linked(t: Target) -> tuple[str, int, str | None]:
    """The owner, number and URL of the one Project linked to the repository."""
    data = _gh_read(t, "repo", "view", "--json", "owner,name,projectsV2,defaultBranchRef")
    try:
        linked = data.get("projectsV2") or {}
        nodes = linked.get("Nodes", linked.get("nodes")) or []
        owner = str(data["owner"]["login"])
        if len(nodes) != 1:
            raise Unreadable(f"{len(nodes)} Projects linked to {t.repo}")
        return owner, int(nodes[0]["number"]), nodes[0].get("url")
    except (AttributeError, KeyError, TypeError, ValueError):
        raise Unreadable(f"`gh repo view` printed an unexpected shape: {data}") from None


def _areas(field: Any) -> set[str] | None:
    """The `Area` option names; `None` when the Project has no `Area` field."""
    return None if field is None else {str(option["name"]) for option in field["options"]}


def _project_state(t: Target, owner: str, number: int) -> tuple[bool, list[str], bool]:
    """Whether the Project is public, the template's workflows it lacks or has disabled, and
    whether its `Area` options are still the template's (or it has no `Area` field)."""
    template_owner, template_number = t.template
    data = _gh_read(
        t,
        "api",
        "graphql",
        "-f",
        f"query={QUERY}",
        "-f",
        f"owner={owner}",
        "-F",
        f"number={number}",
        "-f",
        f"template={template_owner}",
        "-F",
        f"source={template_number}",
    )
    try:
        project = data["data"]["linked"]["projectV2"]
        enabled = {w["name"] for w in project["workflows"]["nodes"] if w["enabled"]}
        areas = _areas(project["field"])
        template = _areas(data["data"]["template"]["projectV2"]["field"])
        public = project["public"] is True
    except (KeyError, TypeError):
        errors = data.get("errors") if isinstance(data, dict) else None
        raise Unreadable(f"the Project #{number} of {owner} reads as {errors or data}") from None
    missing = [name for name in WORKFLOWS if name not in enabled]
    return public, missing, areas is None or areas == template


def _secret_set(t: Target) -> bool:
    data = _gh_read(t, "secret", "list", "--repo", t.repo, "--json", "name")
    try:
        return REVIEW_TOKEN in {str(secret["name"]) for secret in data}
    except (KeyError, TypeError):
        raise Unreadable(f"`gh secret list` printed an unexpected shape: {data}") from None


def _plugin_file(path: Path) -> Any:
    """A plugin file's JSON; `None` when it is absent (no plugin was ever installed)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Unreadable(f"{path}: {exc}") from None


def _plugin_channel(t: Target) -> bool:
    """The machine's marketplace is at `stable` with auto-update and the plugin has a
    user-scope install, from Claude Code's plugin files (its CLI prints no `autoUpdate`)."""
    plugins = t.home / ".claude" / "plugins"
    known = _plugin_file(plugins / "known_marketplaces.json")
    installed = _plugin_file(plugins / "installed_plugins.json")
    try:
        entry = None if known is None else known.get(t.marketplace)
        channel = entry is not None and entry["source"].get("repo") == t.source
        channel = channel and entry["source"].get("ref") == "stable"
        channel = channel and entry.get("autoUpdate") is True
        installs = [] if installed is None else installed["plugins"].get(t.plugin) or []
        user = any(install["scope"] == "user" for install in installs)
    except (AttributeError, KeyError, TypeError):
        raise Unreadable(f"{plugins} holds plugin files of an unexpected shape") from None
    return bool(channel) and user


@dataclass
class PrePush:
    """This clone's pre-push hook: `installed` when pre-commit's hook runs on a push, `foreign`
    when a hook pre-commit did not install is there, `blocked` why `init` cannot install it."""

    hook: Path
    installed: bool
    foreign: bool
    blocked: str | None


def pre_push(t: Target) -> PrePush:
    """The clone's pre-push state; `Unreadable` when git or the hook file cannot be read."""
    configured = t.git("config", "--get", "core.hooksPath")
    if configured.returncode not in (0, 1):
        raise Unreadable(f"`git config --get core.hooksPath` exited {configured.returncode}")
    done = t.git("rev-parse", "--git-path", "hooks/pre-push")
    if done.returncode != 0 or done.stdout is None:
        raise Unreadable(f"`git rev-parse --git-path hooks/pre-push` exited {done.returncode}")
    hook = t.root / done.stdout.strip()
    try:
        text = hook.read_bytes()
    except FileNotFoundError:
        text = None
    except OSError as exc:
        raise Unreadable(f"{hook}: {exc}") from None
    if configured.returncode == 0:
        return PrePush(hook, False, False, "core.hooksPath is set")
    installed = text is not None and PRE_COMMIT_ID.encode() in text
    blocked = None if installed or t.pre_commit else "pre-commit is not on PATH"
    return PrePush(hook, installed, text is not None and not installed, blocked)


def _pre_push_row(t: Target) -> list[str]:
    """The row while `init` cannot install this clone's hook; it installs any other clone's."""
    row = (
        "manual pre-push: in this clone -- git config --unset-all core.hooksPath where it is "
        "set, then pre-commit install --hook-type pre-push, so a push runs the declared test"
    )
    try:
        blocked = pre_push(t).blocked
    except Unreadable as exc:
        return [f"{row} (cannot read: {exc})"]
    return [f"{row} ({blocked})"] if blocked else []


if __name__ == "__main__":
    sys.exit("manual.py is imported by init.py; run `agent-process init`")
