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
from typing import Any, Callable, Protocol

import activate_protection
import dashboard

# The built-in workflows of the template by API name, with their targets (the `state` spec's
# template requirement); the API exposes only a workflow's name and whether it is enabled.
WORKFLOWS = {
    "Auto-add to project": "Auto-add to project (this repository)",
    "Item added to project": "Item added -> Todo",
    "Item reopened": "Item reopened -> Todo",
    "Item closed": "Item closed -> Done",
    "Pull request merged": "Pull request merged -> Done",
}
AREA = 'field(name:"Area"){... on ProjectV2SingleSelectField{id options{id name}}}'
TEMPLATE = (
    "template:repositoryOwner(login:$template){... on ProjectV2Owner{projectV2(number:$source){"
    f"{AREA}}}}}}}"
)
# The linked Project's state the rows and the areas step depend on, and the template's `Area`
# options; `TEMPLATE_QUERY` is the template's half alone, for a run with no linked Project.
QUERY = (
    "query($owner:String!,$number:Int!,$template:String!,$source:Int!){"
    "linked:repositoryOwner(login:$owner){... on ProjectV2Owner{projectV2(number:$number){"
    "id public workflows(first:50){nodes{name enabled}} views(first:100){nodes{id name filter}} "
    f"{AREA}}}}}}}{TEMPLATE}}}"
)
TEMPLATE_QUERY = f"query($template:String!,$source:Int!){{{TEMPLATE}}}"
REVIEW_TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
GRAFANA_URL = "GRAFANA_URL"
GRAFANA_TOKEN = "GRAFANA_SERVICE_ACCOUNT_TOKEN"
INFINITY = "yesoreyeram-infinity-datasource"
MCP = "grafana MCP server in ~/.claude.json"
# The line pre-commit writes into every hook it installs (observed 2026-09-30).
PRE_COMMIT_ID = "# ID: 138fd403232d2ddd5efb44317e38bf03"
# The fix the session-start identity marker names; the template's copy is asserted equal.
IDENTITY_FIX = (
    "agent-process agent_identity --bot <login> --dry-run, then with --confirm, then "
    "gh repo edit --enable-auto-merge, then restart Claude Code"
)
SETTINGS = Path(".claude") / "settings.local.json"

Read = Callable[..., "subprocess.CompletedProcess[str]"]


class Unreadable(Exception):
    """A row's state `init` cannot read; the row is printed with this reason."""


class Grafana(Protocol):
    """A Grafana stack's HTTP API; every call raises `Unreadable` when it fails."""

    def datasources(self) -> list[dict[str, Any]]: ...

    def dashboard_titles(self, query: str) -> list[str]: ...

    def post_dashboard(self, model: dict[str, Any]) -> str: ...


@dataclass
class Target:
    """The consumer `owner/name` and the reads the rows need: `gh` and `git` (in the clone)
    return a completion whatever its exit code. `source` is the process repository whose
    `marketplace` and `plugin` the machine should follow; `template` is the template Project's
    owner and number; `pre_commit` is the `pre-commit` on PATH, if any. `gh_write` is a `gh`
    write that raises `InstallError` on a non-zero exit; `grafana` opens a stack by URL and
    token."""

    repo: str
    root: Path
    home: Path
    gh: Read
    gh_write: Read
    grafana: Callable[[str, str], Grafana]
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
        public, missing, areas = _project_state(t, owner, number, url)
        state = areas.state
    except Unreadable as exc:
        public, missing, state, why = False, list(WORKFLOWS), "template", f" (cannot read: {exc})"
    where = url or "the new copy"
    if not public:
        found.append(
            f"manual project-visibility: {where}/settings -- a copy is private; "
            f"set its visibility as intended{why}"
        )
    if missing:
        enable = ", ".join(WORKFLOWS[name] for name in missing)
        found.append(f"manual project-workflows: {where}/workflows -- enable {enable}{why}")
    replace = "replace the Area options and the area views in the UI"
    if state == "template":
        found.append(
            f"manual project-areas: {where}/settings -- re-run init with one --area <name> per "
            f"area of this repository, or {replace}{why}"
        )
    elif state == "none":
        found.append(f"manual project-areas: {where}/settings -- {replace}")
    secrets = _names_or_unreadable(t, "secret")
    repo = _repository(t)
    return [
        *found,
        *_outstanding(
            lambda: _has(secrets, REVIEW_TOKEN),
            f"manual review-secret: https://github.com/{t.repo}/settings/secrets/actions -- "
            f"claude setup-token, then gh secret set {REVIEW_TOKEN} -R {t.repo} and paste the "
            "token at its prompt; the review caller passes it to the review",
        ),
        *_readings_row(
            t,
            secrets,
            f"manual task-readings: https://github.com/{t.repo}/settings/variables/actions -- "
            f"gh variable set {GRAFANA_URL} -R {t.repo} with this repository's Grafana URL, "
            f"then gh secret set {GRAFANA_TOKEN} -R {t.repo} with a service account token of "
            "that stack; the task-readings caller passes them to the recording; "
            f"then agent-process dashboard {t.repo} > per-task.json (list further repositories "
            "for one combined dashboard) and import it in that stack's Grafana "
            "(Dashboards → New → Import), choosing its Infinity datasource",
        ),
        *_outstanding(
            lambda: _plugin_channel(t),
            "manual plugin-channel: once per machine -- claude plugin marketplace add "
            f'"{t.source}#stable", then /plugin -> Marketplaces -> '
            f"Enable auto-update for {t.marketplace}, then claude plugin install {t.plugin}",
        ),
        *_pre_push_row(t),
        *_outstanding(
            lambda: _protected(t, repo),
            "manual protection: once the installation PR has merged with both process checks "
            "green -- agent-process activate_protection --pr <N> --dry-run with its number, then "
            "with --confirm instead of --dry-run, so the default branch requires "
            f"{' and '.join(activate_protection.contexts())}",
        ),
        *_outstanding(
            lambda: _identity_set(t),
            "manual agent-identity: in this clone, once the installation PR has merged -- create "
            "the agent's GitHub account, gh auth login -s project,workflow as it, then "
            f"gh auth switch --user <person>; then {IDENTITY_FIX}",
        ),
        *_outstanding(
            lambda: _field(repo, "allow_auto_merge") is True,
            f"manual auto-merge: https://github.com/{t.repo}/settings -- "
            "gh repo edit --enable-auto-merge, so gh pr merge --auto merges an approved PR",
        ),
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


def _repository(t: Target) -> dict[str, Any] | Unreadable:
    """`repos/<owner>/<name>`, one read for the `protection` and `auto-merge` rows; `gh api`
    prints GitHub's error object on a 4xx, which names neither field."""
    try:
        data = _gh_read(t, "api", f"repos/{t.repo}")
    except Unreadable as exc:
        return exc
    if (
        isinstance(data, dict)
        and isinstance(data.get("default_branch"), str)
        and "allow_auto_merge" in data
    ):
        return data
    return Unreadable(f"`gh api repos/{t.repo}` printed an unexpected shape: {data}")


def _field(repo: dict[str, Any] | Unreadable, name: str) -> Any:
    if isinstance(repo, Unreadable):
        raise repo
    return repo[name]


def _protected(t: Target, repo: dict[str, Any] | Unreadable) -> bool:
    """The default branch's rules require both process checks."""
    branch = _field(repo, "default_branch")
    rules = _gh_read(t, "api", f"repos/{t.repo}/rules/branches/{branch}")
    try:
        if not isinstance(rules, list):
            raise TypeError
        required = {
            str(check["context"])
            for rule in rules
            if rule["type"] == "required_status_checks"
            for check in rule["parameters"]["required_status_checks"]
        }
    except (KeyError, TypeError):
        raise Unreadable(f"the rules of {branch} read as {rules}") from None
    return set(activate_protection.contexts()) <= required


def _identity_set(t: Target) -> bool:
    """This clone's settings carry the agent's `env.GH_TOKEN`; a missing `env` is `{}`."""
    path = t.root / SETTINGS
    data = _plugin_file(path)
    if data is None:
        return False
    env = data.get("env", {}) if isinstance(data, dict) else None
    if not isinstance(env, dict):
        raise Unreadable(f"{path} is not an object whose `env` is an object")
    return bool(env.get("GH_TOKEN"))


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


@dataclass
class Areas:
    """The linked Project's `Area` state: `template` while its options are the template's and
    it is not the template, `none` with no `Area` field, `own` otherwise. `project` and
    `field` are node ids, `options` the option ids by name, `views` each view's `id`, `name`
    and `filter`, `template` the template's option names."""

    state: str
    url: str | None
    project: str
    field: str | None
    options: dict[str, str]
    views: list[dict[str, Any]]
    template: list[str]


def areas(t: Target, project: tuple[str, int, str | None] | None = None) -> Areas:
    """The `Area` state of `project` (owner, number, url), else of the linked Project;
    `Unreadable` unless exactly one Project is linked."""
    return _project_state(t, *(project or _linked(t)))[2]


def template_options(t: Target) -> list[str]:
    """The template's `Area` option names, for a run that has not linked a Project yet."""
    owner, number = t.template
    query, template, source = f"query={TEMPLATE_QUERY}", f"template={owner}", f"source={number}"
    data = _gh_read(t, "api", "graphql", "-f", query, "-f", template, "-F", source)
    try:
        return list(_options(data["data"]["template"]["projectV2"]["field"]))
    except (KeyError, TypeError):
        errors = data.get("errors") if isinstance(data, dict) else None
        raise Unreadable(f"the template Project reads as {errors or data}") from None


def _options(field: Any) -> dict[str, str]:
    return {str(option["name"]): str(option["id"]) for option in field["options"]}


def _project_state(
    t: Target, owner: str, number: int, url: str | None
) -> tuple[bool, list[str], Areas]:
    """Whether the Project is public, the template's workflows it lacks or has disabled, and
    its `Area` state."""
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
        field = project["field"]
        options = {} if field is None else _options(field)
        template = list(_options(data["data"]["template"]["projectV2"]["field"]))
        views = [
            {"id": str(v["id"]), "name": str(v["name"]), "filter": v["filter"]}
            for v in project["views"]["nodes"]
        ]
        field_id = None if field is None else str(field["id"])
        public = project["public"] is True
        project_id = str(project["id"])
    except (KeyError, TypeError):
        errors = data.get("errors") if isinstance(data, dict) else None
        raise Unreadable(f"the Project #{number} of {owner} reads as {errors or data}") from None
    state = "own"
    if field is None:
        state = "none"
    elif set(options) == set(template) and (owner, str(number)) != t.template:
        state = "template"
    found = Areas(state, url, project_id, field_id, options, views, template)
    missing = [name for name in WORKFLOWS if name not in enabled]
    return public, missing, found


def _names_or_unreadable(t: Target, kind: str) -> dict[str, str] | Unreadable:
    """One read shared by several rows, each of which `_has` marks when it failed."""
    try:
        return _names(t, kind)
    except Unreadable as exc:
        return exc


def _has(names: dict[str, str] | Unreadable, name: str) -> bool:
    if isinstance(names, Unreadable):
        raise names
    return name in names


def _names(t: Target, kind: str) -> dict[str, str]:
    """The repository's Actions `secret` names, or `variable` names with their values."""
    fields = "name,value" if kind == "variable" else "name"
    data = _gh_read(t, kind, "list", "--repo", t.repo, "--json", fields)
    try:
        return {str(item["name"]): str(item.get("value", "")) for item in data}
    except (AttributeError, KeyError, TypeError):
        raise Unreadable(f"`gh {kind} list` printed an unexpected shape: {data}") from None


def _plugin_file(path: Path) -> Any:
    """A plugin or settings file's JSON; `None` when it is absent (no plugin was ever
    installed, no setting was ever written)."""
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
        channel = (
            entry is not None
            and entry["source"].get("repo") == t.source
            and entry["source"].get("ref") == "stable"
            and entry.get("autoUpdate") is True
        )
        installs = [] if installed is None else installed["plugins"].get(t.plugin) or []
        user = any(install["scope"] == "user" for install in installs)
    except (AttributeError, KeyError, TypeError):
        raise Unreadable(f"{plugins} holds plugin files of an unexpected shape") from None
    return bool(channel) and user


@dataclass
class Readings:
    """The task-readings state: the `grafana` MCP server's `url` and `token` (read from
    `source`), the repository's `GRAFANA_URL` (`variable`, `None` when unset) and whether its
    token `secret` is set, whether the stack holds the rendered `title` (`dashboard`, `None`
    when not read), its Infinity `datasource` uid, and why `init` cannot set all up
    (`blocked`)."""

    title: str
    url: str | None = None
    token: str | None = None
    source: str = ""
    variable: str | None = None
    secret: bool = False
    datasource: str | None = None
    dashboard: bool | None = None
    blocked: str | None = None


def readings(t: Target, secrets: dict[str, str] | Unreadable | None = None) -> Readings:
    """The names (`secrets` when already read), then the MCP config, then — unless the
    variable names another stack, which leaves `url` and `token` unset — the stack's dashboard
    and, when that is missing, its Infinity datasource."""
    r = Readings(dashboard.render([t.repo])["title"])
    try:
        r.variable = _names(t, "variable").get(GRAFANA_URL)
        r.secret = _has(
            _names_or_unreadable(t, "secret") if secrets is None else secrets, GRAFANA_TOKEN
        )
        config = _mcp_grafana(t.home)
    except Unreadable as exc:
        r.blocked = f"cannot read: {exc}"
        return r
    if isinstance(config, str):
        r.blocked = f"not found: {config}"
        return r
    if r.variable not in (None, config[0]):
        r.blocked = f"another stack: {r.variable}"
        return r
    r.url, r.token, r.source = config
    try:
        stack = t.grafana(r.url, r.token)
        r.dashboard = r.title in stack.dashboard_titles(r.title)
        if not r.dashboard:
            found = [s.get("uid") for s in stack.datasources() if s.get("type") == INFINITY]
            r.datasource = str(found[0]) if found else None
            if r.datasource is None:
                r.blocked = f"not found: Infinity datasource in {r.url}"
    except Unreadable as exc:
        r.dashboard, r.blocked = False, f"cannot read: {exc}"
    return r


def _mcp_grafana(home: Path) -> tuple[str, str, str] | str:
    """The `grafana` MCP server's URL, token and the token's source, or what is missing."""
    path = home / ".claude.json"
    config = _plugin_file(path)
    try:
        server = None if config is None else (config.get("mcpServers") or {}).get("grafana")
        env = None if server is None else server.get("env") or {}
    except AttributeError:
        env = []
    if not isinstance(env, (dict, type(None))):
        raise Unreadable(f"{path} holds an mcpServers entry of an unexpected shape")
    if env is None:
        return MCP
    if not env.get(GRAFANA_URL):
        return f"{GRAFANA_URL} of the {MCP}"
    url = str(env[GRAFANA_URL])
    if env.get(GRAFANA_TOKEN):
        return url, str(env[GRAFANA_TOKEN]), f"{GRAFANA_TOKEN} of the {MCP}"
    name = env.get(f"{GRAFANA_TOKEN}_FILE")
    if not name:
        return f"{GRAFANA_TOKEN} of the {MCP}"
    file = Path(str(name)).expanduser()
    try:
        token = file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        token = ""
    except (OSError, UnicodeDecodeError) as exc:
        raise Unreadable(f"{file}: {exc}") from None
    # An empty file holds no token, as an empty inline value does.
    return (url, token, str(file)) if token else str(file)


def _readings_row(t: Target, secrets: dict[str, str] | Unreadable, row: str) -> list[str]:
    """The row while the variable, the secret or the dashboard is missing and no step sets it
    up; with another stack named, only while the secret is missing."""
    r = readings(t, secrets)
    done = r.variable is not None and r.secret and r.dashboard is not False
    return [f"{row} ({r.blocked})"] if r.blocked and not done else []


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
        try:
            names = sorted(p.name for p in hook.parent.iterdir() if p.suffix != ".sample")
        except FileNotFoundError:
            names = []
        except OSError as exc:
            raise Unreadable(f"{hook.parent}: {exc}") from None
        reason = "core.hooksPath is set"
        if names:
            reason += (
                f" and {hook.parent} holds {', '.join(names)}: git stops running them once it is"
                " unset, so port them to .pre-commit-config.yaml as repo: local hooks first"
            )
        return PrePush(hook, False, False, reason)
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
