"""Harness of the installer tests: the fixture release repository, the fake GitHub behind
`gh`, the process-boundary runner and the state readers. Shared by the `test_init*.py` modules
and the `conftest.py` fixtures."""

from __future__ import annotations

import importlib.util
import itertools
import json
import os
import re
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import yaml

from tests.publisher.post_merge_fake import PostMergeGitHub

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "skills" / "agent-process"
INIT = PACKAGE / "scripts" / "init.py"
HOST = "win32" if sys.platform == "win32" else "linux"

LINE = re.compile(r"^(planned|unchanged|written|conflict|after-merge) ([a-z-]+):", re.MULTILINE)
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


def load_init() -> ModuleType:
    spec = importlib.util.spec_from_file_location("agent_process_init", INIT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # As `python init.py` does: the script's directory resolves its sibling imports.
    sys.path.insert(0, str(INIT.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(INIT.parent))
    return module


# The fixture tags this tree as the current release and the stub as the next minor.
CURRENT = load_init().VERSION
_major, _minor, _ = CURRENT.split(".")
OTHER = f"{_major}.{int(_minor) + 1}.0"
STUB = f"""\
import json
import os
import sys
from pathlib import Path

print("stub-release v{OTHER}")
print("argv " + json.dumps(sys.argv[1:]))
print("cwd " + os.getcwd())
print("file " + str(Path(__file__).resolve()))
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""


def git(*args: str, cwd: Path | None = None) -> str:
    done = subprocess.run(
        [*GIT, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return done.stdout.strip()


OWNER = "ekolvah"
REPO_NAME = "consumer"
TITLE = f"{REPO_NAME} agent process"
PUBLISHER = "ekolvah/agent-process-distribution"
# The hook repository the rendered `.pre-commit-config.yaml` names.
PROCESS_URL = f"https://github.com/{PUBLISHER}"


def _done(
    args: list[str], payload: Any = None, code: int = 0, out: str = "", err: str = "fault"
) -> subprocess.CompletedProcess[str]:
    """`gh`'s completion: JSON `payload` or plain `out` on stdout, a fault on stderr."""
    text = out if payload is None else json.dumps(payload)
    return subprocess.CompletedProcess(args, code, text, err if code else "")


# The template's built-in workflows and `Area` options, and what `gh project copy` leaves of
# them: a copy without `Auto-add to project` (observed 2026-09-30, change
# manual-rows-from-state).
TEMPLATE_WORKFLOWS = [
    "Auto-add sub-issues to project",
    "Auto-add to project",
    "Auto-close issue",
    "Item added to project",
    "Item closed",
    "Item reopened",
    "Pull request linked to issue",
    "Pull request merged",
]
TEMPLATE_AREAS = [
    "Observability",
    "Distribution",
    "Token efficiency",
    "Process quality",
    "Refactoring",
]


# GitHub's error body, which `gh api` prints on stdout before exiting 1.
NOT_FOUND = {"message": "Not Found", "status": "404"}
# The installation PR's head commit, and the GitHub Actions app id of each process check run.
HEAD_SHA = "c" * 40
CHECK_APPS = {"agent-process / quality": 15368, "agent-review / agent-review": 15369}
AGENT = "agent-bot"
AGENT_TOKEN = "gho_agent_secret"


def check_run(name: str, conclusion: str = "success") -> dict[str, Any]:
    return {
        "name": name,
        "conclusion": conclusion,
        "app": {"slug": "github-actions", "id": CHECK_APPS[name]},
    }


def list_403(kind: str) -> str:
    """`gh secret list` or `gh variable list` refused, as observed."""
    return (
        f"failed to get {kind}s: HTTP 403: Resource not accessible by integration "
        f"(https://api.github.com/repos/{OWNER}/{REPO_NAME}/actions/{kind}s?per_page=100)\n"
    )


def _copied_workflows() -> dict[str, bool]:
    return {name: True for name in TEMPLATE_WORKFLOWS if name != "Auto-add to project"}


_VIEW_IDS = itertools.count(1)
# The template's views other than its area views (change init-replaces-project-areas, proposal
# Why); their filters are not observed and only need to stay unchanged.
BASE_VIEWS = {"Open": "-status:Done", "Bugs": "label:bug", "Empty": "no:area"}


def area_filter(name: str) -> str:
    return f'-status:Done area:"{name}"'


def view(name: str, filter: str | None) -> dict[str, Any]:
    """A view in the observed shape, with a fresh node id."""
    return {"id": f"PVTV_{next(_VIEW_IDS)}", "name": name, "filter": filter}


def _template_views() -> list[dict[str, Any]]:
    areas = {name: area_filter(name) for name in TEMPLATE_AREAS}
    return [view(name, filter) for name, filter in {**BASE_VIEWS, **areas}.items()]


@dataclass
class Project:
    """A Project; `areas` are its `Area` options, `None` when it has no `Area` field."""

    owner: str
    number: int
    title: str
    closed: bool = False
    repositories: set[str] = field(default_factory=set)
    workflows: dict[str, bool] = field(default_factory=_copied_workflows)
    areas: list[str] | None = field(default_factory=lambda: list(TEMPLATE_AREAS))
    views: list[dict[str, Any]] = field(default_factory=_template_views)

    @property
    def url(self) -> str:
        return f"https://github.com/users/{self.owner}/projects/{self.number}"

    @property
    def id(self) -> str:
        return f"PVT_{self.owner}_{self.number}"

    @property
    def field_id(self) -> str:
        return f"PVTSSF_{self.owner}_{self.number}"


class FakeGitHub(PostMergeGitHub):
    """GitHub behind `gh` for the consumer `ekolvah/consumer`. It starts with template
    Project 4 linked to the publisher; `faults[command]` makes the next `copy` or `link`
    exit 1 either before its effect or after it (the lost response). Issues and PRs share
    one numbering, as on GitHub; `pr create` needs its head and base pushed to `origin`.
    `default_branch` is the settings' name; `empty` makes `repo view` print the empty
    `defaultBranchRef.name` of a repository with no commits (change init-empty-repository).
    `secrets` are the consumer's secret names and `variables` its variables by name;
    `faults["secret-list"]`, `faults["variable-list"]` and `faults["project-read"]` make
    those reads exit 1 (change manual-rows-from-state). `gh secret set` takes the value from
    standard input into `secret_values`; `faults["secret-set"]` makes it exit 1 (change
    task-readings-auto-setup). The `repos/<owner>/<name>` read carries `allow_auto_merge`, and
    the default branch's rules require `required_checks`; `faults["repo-read"]` and
    `faults["rules-read"]` make those reads print GitHub's error body and exit 1 (change
    install-reports-post-merge-steps); `faults["rules-shape"]` makes the rules read answer a
    rule without `type` (change manual-shared-read-helpers). The `Area` options and views
    mutations apply to a Project by node id (change init-replaces-project-areas). The
    `viewerPermission` read answers by the `GH_TOKEN` of its environment from `permissions`;
    `tokened` logs every call whose environment carries one (change agent-identity-standard-commands).
    `calls` logs every call with its environment. `accounts` are the github.com accounts of
    `gh auth status` and `tokens` their tokens by login; `rulesets` are served as the
    `FakeGh` of `test_activate_protection.py` serves them, and the rules of the default branch
    require their checks too; `check_runs` are the runs on the head of every PR, `callers`
    whether both process callers are on the default branch; a collaborator `PUT` opens an
    invitation the invitee's token lists and accepts, which makes its permission `WRITE`;
    `project_writers` are the logins with the Project's `WRITER` role (change
    init-runs-post-merge-steps)."""

    def __init__(self) -> None:
        template = Project(OWNER, 4, "agent-process-distribution agent process")
        template.workflows = {name: True for name in TEMPLATE_WORKFLOWS}
        template.repositories.add(PUBLISHER)
        self.projects = [template]
        self.secrets: set[str] = set()
        self.variables: dict[str, str] = {}
        self.secret_values: dict[str, str] = {}
        self.faults: dict[str, str] = {}
        self.hidden = 0  # Projects the owner has beyond the first page
        self.issues: list[dict[str, Any]] = []
        self.pulls: list[dict[str, Any]] = []
        self.origin: Path | None = None
        self.default_branch = "main"
        self.empty = False
        self.allow_auto_merge = False
        self.required_checks: list[str] = []
        self.permissions = {"agent-token": "WRITE"}
        self.tokened: list[tuple[str, list[str]]] = []
        self.calls: list[tuple[list[str], dict[str, str] | None]] = []
        self.accounts = [{"login": OWNER, "active": True}]
        self.tokens: dict[str, str] = {}
        self.rulesets: dict[int, dict[str, Any]] = {}
        self.check_runs = [check_run(name) for name in CHECK_APPS]
        self.callers = True
        self.invitations: list[dict[str, Any]] = []
        self.project_writers: set[str] = set()

    def issue(self, title: str, state: str = "OPEN") -> dict[str, Any]:
        issue = {"number": self._item(), "title": title, "state": state, "body": ""}
        self.issues.append(issue)
        return issue

    def _item(self) -> int:
        return len(self.issues) + len(self.pulls) + 1

    def add(self, title: str = TITLE, *, closed: bool = False, linked: str = "") -> Project:
        project = Project(OWNER, self._next(), title, closed)
        if linked:
            project.repositories.add(linked)
        self.projects.append(project)
        return project

    def _next(self) -> int:
        return max(p.number for p in self.projects) + 1

    def state(self) -> dict[str, Any]:
        return {
            "projects": [
                (p.owner, p.number, p.title, p.closed, sorted(p.repositories))
                for p in self.projects
            ],
            "issues": json.loads(json.dumps(self.issues)),
            "pulls": json.loads(json.dumps(self.pulls)),
        }

    def _pushed(self, branch: str) -> bool:
        assert self.origin is not None
        return bool(git("ls-remote", "--heads", str(self.origin), branch))

    def __call__(
        self, args: list[str], input: str | None = None, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        token = (env or {}).get("GH_TOKEN")
        if token:
            self.tokened.append((token, args))
        self.calls.append((args, env))
        return self._post_merge(args, token) or self._route(args, input, token)

    def _route(
        self, args: list[str], input: str | None, token: str | None
    ) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["api", "graphql"] and "viewerPermission" in args[-1]:
            return self._permission(args, token)
        if args[0] == "api" and args[1].startswith(f"repos/{OWNER}/{REPO_NAME}"):
            return self._repo_read(args)
        if args[0] in {"secret", "variable"}:
            return self._list(args) if args[1] == "list" else self._set(args, input)
        if args[:2] == ["api", "graphql"] and "projectV2(number:" in args[3]:
            return self._project_read(args)
        if args[:2] == ["api", "graphql"] and args[3].startswith("query=mutation"):
            return self._areas_write(args)
        return self._items(args) if args[0] in {"issue", "pr"} else self._projects(args)

    def _permission(self, args: list[str], token: str | None) -> subprocess.CompletedProcess[str]:
        """The token's `viewerPermission` on the consumer, as GitHub answers it, and with
        `viewerCanUpdate` asked the token's `viewer` id and its Project role."""
        assert f"owner={OWNER}" in args and f"name={REPO_NAME}" in args, args
        if token not in self.permissions:
            return _done(args, None, code=1, err="HTTP 401: Bad credentials\n")
        data: dict[str, Any] = {"repository": {"viewerPermission": self.permissions[token]}}
        if "viewerCanUpdate" in args[-1]:
            (login,) = [name for name, value in self.tokens.items() if value == token]
            data["viewer"] = {"id": f"U_{login}"}
            data["repositoryOwner"] = {
                "projectV2": {"viewerCanUpdate": login in self.project_writers}
            }
        return _done(args, {"data": data})

    def _repo_read(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """`gh api repos/<owner>/<name>` and `.../rules/branches/<default>`."""
        repo = f"repos/{OWNER}/{REPO_NAME}"
        rules = args == ["api", f"{repo}/rules/branches/{self.default_branch}"]
        assert rules or args == ["api", repo], args
        if ("rules-read" if rules else "repo-read") in self.faults:
            return _done(args, NOT_FOUND, code=1, err="gh: Not Found (HTTP 404)\n")
        if rules and "rules-shape" in self.faults:
            return _done(args, [{"parameters": {}}])
        if not rules:
            read = {"name": REPO_NAME, "default_branch": self.default_branch}
            return _done(args, {**read, "allow_auto_merge": self.allow_auto_merge})
        ruled = [
            check["context"]
            for ruleset in self.rulesets.values()
            for rule in ruleset["rules"]
            if rule["type"] == "required_status_checks"
            for check in rule["parameters"]["required_status_checks"]
        ]
        checks = [{"context": context} for context in [*self.required_checks, *ruled]]
        rule = {"type": "required_status_checks", "parameters": {"required_status_checks": checks}}
        return _done(args, [rule] if checks else [])

    def _list(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """`gh secret list --json name` and `gh variable list --json name,value`."""
        fields = "name" if args[0] == "secret" else "name,value"
        assert args[2:] == ["--repo", f"{OWNER}/{REPO_NAME}", "--json", fields], args
        if f"{args[0]}-list" in self.faults:
            return _done(args, code=1, err=list_403(args[0]))
        if args[0] == "secret":
            return _done(args, [{"name": name} for name in sorted(self.secrets)])
        values = sorted(self.variables.items())
        return _done(args, [{"name": name, "value": value} for name, value in values])

    def _set(self, args: list[str], input: str | None) -> subprocess.CompletedProcess[str]:
        """`gh variable set NAME --body V --repo R` and `gh secret set NAME --repo R`, the
        secret's value on standard input."""
        name, flags = args[2], dict(zip(args[3::2], args[4::2]))
        assert flags.pop("--repo") == f"{OWNER}/{REPO_NAME}", args
        if args[0] == "variable":
            assert set(flags) == {"--body"} and input is None, args
            self.variables[name] = flags["--body"]
            return _done(args, out=f"Created variable {name}\n")
        assert not flags and input is not None, args
        if "secret-set" in self.faults:
            return _done(args, code=1, err="failed to set secret: HTTP 422\n")
        self.secrets.add(name)
        self.secret_values[name] = input
        return _done(args, out=f"Set Actions secret {name}\n")

    def _items(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Issues and PRs in the observed shapes of design D4 (install-links-an-issue)."""
        flags = dict(zip(args[2::2], args[3::2]))
        assert flags.pop("--repo") == f"{OWNER}/{REPO_NAME}", args
        if args[:2] == ["issue", "list"]:
            assert flags == {"--state": "open", "--json": "number,title", "--limit": "1000"}
            opened = [i for i in self.issues if i["state"] == "OPEN"]
            return _done(args, [{"number": i["number"], "title": i["title"]} for i in opened])
        if args[:2] == ["issue", "create"]:
            assert set(flags) == {"--title", "--body"}, args
            issue = self.issue(flags["--title"])
            issue["body"] = flags["--body"]
            number = issue["number"]
            return _done(args, out=f"https://github.com/{OWNER}/{REPO_NAME}/issues/{number}\n")
        if args[:2] == ["pr", "list"]:
            fields, state = flags.pop("--json").split(","), flags.pop("--state")
            assert set(flags) == {"--head"} and state in {"open", "all", "merged"}, args
            assert set(fields) <= {"number", "state", "url", "body"}, args
            listed = [
                {name: p[name] for name in fields}
                for p in self.pulls
                if p["head"] == flags["--head"] and state in {"all", p["state"].lower()}
            ]
            return _done(args, listed)
        assert args[:2] == ["pr", "create"], args
        assert set(flags) == {"--base", "--head", "--title", "--body"}, args
        head = flags["--head"]
        if any(p["head"] == head and p["state"] == "OPEN" for p in self.pulls):
            return _done(args, code=1)
        if not (self._pushed(head) and self._pushed(flags["--base"])):
            return _done(args, code=1)
        number = self._item()
        url = f"https://github.com/{OWNER}/{REPO_NAME}/pull/{number}"
        pull = {"number": number, "head": head, "base": flags["--base"], "url": url}
        self.pulls.append(
            {**pull, "title": flags["--title"], "body": flags["--body"], "state": "OPEN"}
        )
        return _done(args, out=url + "\n")

    def _projects(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        def done(payload: Any = None, code: int = 0) -> subprocess.CompletedProcess[str]:
            return _done(args, payload, code)

        if args[:2] == ["repo", "view"]:
            assert args[2:] == ["--json", "owner,name,projectsV2,defaultBranchRef"], args
            repo = f"{OWNER}/{REPO_NAME}"
            linked = [
                {
                    "number": p.number,
                    "title": p.title,
                    "closed": p.closed,
                    "url": p.url,
                    "resourcePath": f"/users/{p.owner}/projects/{p.number}",
                }
                for p in self.projects
                if repo in p.repositories
            ]
            return done(
                {
                    "name": REPO_NAME,
                    "owner": {"login": OWNER},
                    "projectsV2": {"Nodes": linked},
                    "defaultBranchRef": {"name": "" if self.empty else self.default_branch},
                }
            )
        if args[:2] == ["api", "graphql"]:
            assert f"login={OWNER}" in args, args
            owned = [p for p in self.projects if p.owner == OWNER]
            nodes = [
                {
                    "number": p.number,
                    "title": p.title,
                    "closed": p.closed,
                    "url": p.url,
                    "repositories": {"totalCount": len(p.repositories)},
                }
                for p in owned
            ]
            total = len(owned) + self.hidden
            projects = {"totalCount": total, "nodes": nodes}
            return done({"data": {"repositoryOwner": {"projectsV2": projects}}})
        if args[:2] == ["project", "copy"]:
            fault = self.faults.pop("copy", "")
            if fault == "fail-before":
                return done(code=1)
            number, flags = args[2], dict(zip(args[3::2], args[4::2]))
            assert (number, flags["--source-owner"]) == ("4", OWNER), args
            self.projects.append(Project(flags["--target-owner"], self._next(), flags["--title"]))
            return done(code=1 if fault else 0)
        if args[:2] == ["project", "link"]:
            fault = self.faults.pop("link", "")
            if fault == "fail-before":
                return done(code=1)
            to_link, flags = int(args[2]), dict(zip(args[3::2], args[4::2]))
            (project,) = [
                p for p in self.projects if (p.owner, p.number) == (flags["--owner"], to_link)
            ]
            project.repositories.add(f"{flags['--owner']}/{flags['--repo']}")
            return done(code=1 if fault else 0)
        raise AssertionError(f"unexpected gh command: {args}")

    def _project_read(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """The linked Project's id, workflows, views and `Area` field and the
        template's `Area` field, from the `owner`/`number` and `template`/`source` variables, in
        the observed shape; without `owner` only the template's half."""
        if "project-read" in self.faults:
            return _done(args, code=1, err="gh: Could not resolve to a ProjectV2\n")
        variables = dict(part.split("=", 1) for part in args[3::2])

        def project(owner: str, number: str) -> Project:
            (found,) = [p for p in self.projects if (p.owner, p.number) == (owner, int(number))]
            return found

        def area(p: Project) -> dict[str, Any] | None:
            if p.areas is None:
                return None
            options = [{"id": f"{p.field_id}:{name}", "name": name} for name in p.areas]
            return {"id": p.field_id, "options": options}

        template = project(variables["template"], variables["source"])
        data: dict[str, Any] = {"template": {"projectV2": {"field": area(template)}}}
        if "owner" in variables:
            linked = project(variables["owner"], variables["number"])
            workflows = [{"name": name, "enabled": on} for name, on in linked.workflows.items()]
            data["linked"] = {
                "projectV2": {
                    "id": linked.id,
                    "workflows": {"nodes": workflows},
                    "views": {"nodes": [dict(v) for v in linked.views]},
                    "field": area(linked),
                }
            }
        return _done(args, {"data": data})

    def _areas_write(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """`updateProjectV2Field`, `createProjectV2View`, `updateProjectV2View` and
        `deleteProjectV2View` by node id, their variables as `-f` fields; repeated
        `options[][<key>]` fields make a new option when the key repeats, as `gh` does."""
        query = args[3].removeprefix("query=")
        fields: dict[str, str] = {}
        options: list[dict[str, str]] = []
        for flag, part in zip(args[4::2], args[5::2]):
            assert flag == "-f", args
            key, value = part.split("=", 1)
            if key.startswith("options[]["):
                sub = key.removeprefix("options[][").removesuffix("]")
                if not options or sub in options[-1]:
                    options.append({})
                options[-1][sub] = value
            else:
                fields[key] = value

        def by(attribute: str, value: str) -> Project:
            (found,) = [p for p in self.projects if getattr(p, attribute) == value]
            return found

        def find(view_id: str) -> tuple[Project, dict[str, Any]]:
            (found,) = [(p, v) for p in self.projects for v in p.views if v["id"] == view_id]
            return found

        if "updateProjectV2Field(" in query:
            assert all(o["color"] == "GRAY" and o["description"] == "" for o in options), args
            by("field_id", fields["field"]).areas = [o["name"] for o in options]
            return _done(args, {"data": {"updateProjectV2Field": {"clientMutationId": None}}})
        if "createProjectV2View(" in query:
            assert "layout:BOARD_LAYOUT" in query, args
            made = view(fields["name"], None)
            by("id", fields["project"]).views.append(made)
            payload = {"createProjectV2View": {"projectV2View": {"id": made["id"]}}}
            return _done(args, {"data": payload})
        if "updateProjectV2View(" in query:
            find(fields["view"])[1].update(name=fields["name"], filter=fields["filter"])
            return _done(args, {"data": {"updateProjectV2View": {"clientMutationId": None}}})
        assert "deleteProjectV2View(" in query, args
        project, gone = find(fields["view"])
        project.views.remove(gone)
        return _done(args, {"data": {"deleteProjectV2View": {"clientMutationId": None}}})


GRAFANA = "https://stack.grafana.net"


class FakeGrafana:
    """The stack behind `manual.Grafana`, and its factory: `opened` records each `(url,
    token)` it is opened with, `log` each request. `sources` lists a Prometheus datasource
    before the Infinity one (uid `infinity-uid`); `titles` are the stack's dashboards;
    `faults["datasources"]` or `faults["post"]` makes that request raise `error` with the
    fault as its message (change task-readings-auto-setup)."""

    def __init__(self, error: type[Exception]) -> None:
        self.error = error
        self.sources: list[dict[str, str]] = [
            {"name": "grafanacloud-prom", "type": "prometheus", "uid": "prom-uid"},
            {
                "name": "grafanacloud-infinity",
                "type": "yesoreyeram-infinity-datasource",
                "uid": "infinity-uid",
            },
        ]
        self.titles: list[str] = []
        self.faults: dict[str, str] = {}
        self.posted: list[dict[str, Any]] = []
        self.opened: list[tuple[str, str]] = []
        self.log: list[str] = []

    def __call__(self, url: str, token: str) -> FakeGrafana:
        self.opened.append((url, token))
        return self

    def _request(self, name: str) -> None:
        self.log.append(name)
        if name in self.faults:
            raise self.error(self.faults[name])

    def datasources(self) -> list[dict[str, str]]:
        self._request("datasources")
        return self.sources

    def dashboard_titles(self, query: str) -> list[str]:
        self._request("search")
        return [title for title in self.titles if query in title]

    def post_dashboard(self, dashboard: dict[str, Any]) -> str:
        self._request("post")
        self.posted.append(dashboard)
        self.titles.append(dashboard["title"])
        return f"{GRAFANA}/d/new/per-task-delivery"


def grafana_config(
    home: Path, url: str = GRAFANA, *, token: str | None = None, token_file: Path | None = None
) -> None:
    """`~/.claude.json` configuring the `grafana` MCP server as mcp-grafana documents it."""
    env = {"GRAFANA_URL": url}
    if token is not None:
        env["GRAFANA_SERVICE_ACCOUNT_TOKEN"] = token
    if token_file is not None:
        env["GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE"] = str(token_file)
    config = {"mcpServers": {"grafana": {"command": "mcp-grafana", "args": [], "env": env}}}
    (home / ".claude.json").write_text(json.dumps(config), encoding="utf-8")


def local_settings(sb: Sandbox, token: str = "agent-token", *, text: str | None = None) -> None:
    """This clone's `.claude/settings.local.json`, ignored by git as Claude Code ignores it:
    `text`, or by default the agent's `env.GH_TOKEN`."""
    path = sb.root / ".claude" / "settings.local.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with (sb.root / ".git" / "info" / "exclude").open("a", encoding="utf-8") as exclude:
        exclude.write("\n/.claude/settings.local.json\n")
    path.write_text(text or json.dumps({"env": {"GH_TOKEN": token}}), encoding="utf-8")


def agent_account(sb: Sandbox, login: str = AGENT, token: str = AGENT_TOKEN) -> None:
    """A github.com account besides the person in `gh auth status`, with `token`, which reads
    the consumer as an outside collaborator does until it accepts an invitation."""
    sb.github.accounts.append({"login": login, "active": False})
    sb.github.tokens[login] = token
    sb.github.permissions.setdefault(token, "READ")


def which(name: str) -> str | None:
    return shutil.which(name) or name


@dataclass
class Sandbox:
    """`which` is the installer's PATH lookup; a test replaces it to report a tool absent.
    `grafana`, when set, is the Grafana the installer opens; only the tests of change
    task-readings-auto-setup set it."""

    root: Path
    home: Path
    repo: Path
    other: Path
    github: FakeGitHub = field(default_factory=FakeGitHub)
    which: Callable[[str], str | None] = which
    grafana: FakeGrafana | None = None

    @property
    def link(self) -> Path:
        return self.home / ".agents" / "skills" / "agent-process"

    @property
    def origin(self) -> Path:
        return self.root.parent / "origin.git"


BRANCH = f"agent-process/install-{CURRENT}"


def hook_repositories() -> dict[str, tuple[str, list[str]]]:
    """The created config's hook repositories besides the process one: URL -> (rev, hook ids)."""
    text = (PACKAGE / "templates" / "pre-commit-config.yaml").read_text(encoding="utf-8")
    config = yaml.safe_load(string.Template(text).substitute(version=CURRENT))
    return {
        repo["repo"]: (repo["rev"], sorted({hook["id"] for hook in repo["hooks"]}))
        for repo in config["repos"]
        if repo["repo"] not in ("local", PROCESS_URL)
    }


def hook_mirror(process_repo: Path, url: str) -> Path:
    """The fixture's stand-in for the hook repository at `url`, beside the process repository."""
    return process_repo.parent / "hooks" / f"{url.rsplit('/', 1)[1]}.git"


def gitconfig(sb: Sandbox) -> str:
    """The sandbox's global git config: no `https://` URL reaches the network, and the
    process repository and the created config's hook repositories are the fixture's, which the
    pre-push hook's pre-commit clones (change hermetic-sandbox-push, design D1, D2; pre-commit
    clones every repository of the config, whatever the stage)."""
    mirrors = "".join(
        f'[url "{hook_mirror(sb.repo, url).as_posix()}"]\n\tinsteadOf = {url}\n'
        for url in hook_repositories()
    )
    return (
        '[url "file:///no-network/"]\n\tinsteadOf = https://\n'
        f'[url "{sb.repo.as_posix()}"]\n\tinsteadOf = {PROCESS_URL}\n' + mirrors
    )


def home_baseline(sb: Sandbox) -> dict[str, Any]:
    """What `consumer_repo` itself leaves in `home`, as `snapshot` reads it (design D4)."""
    return {str(sb.home / ".gitconfig"): gitconfig(sb).encode("utf-8")}


def consumer_repo(sb: Sandbox) -> None:
    """`root` becomes a clone of the bare `origin` whose `main` holds one empty commit. The
    identity is the clone's own (HOME is the sandbox, its global config `gitconfig`), and no
    end-of-line conversion makes a checkout differ from the bytes `init` wrote."""
    (sb.home / ".gitconfig").write_bytes(gitconfig(sb).encode("utf-8"))
    git("init", "-q", "--bare", "-b", "main", str(sb.origin))
    git("clone", "-q", str(sb.origin), str(sb.root))
    for key, value in {
        "user.name": "t",
        "user.email": "t@t",
        "commit.gpgsign": "false",
        "core.autocrlf": "false",
    }.items():
        git("config", key, value, cwd=sb.root)
    git("symbolic-ref", "HEAD", "refs/heads/main", cwd=sb.root)
    git("commit", "-q", "--allow-empty", "-m", "initial", cwd=sb.root)
    git("push", "-q", "origin", "main", cwd=sb.root)
    sb.github.origin = sb.origin


def empty_origin(sb: Sandbox) -> None:
    """`origin` loses its only branch: a repository with no commits, whose settings name
    `trunk`, unlike the clone's `main` (change init-empty-repository, design D5)."""
    git("update-ref", "-d", "refs/heads/main", cwd=sb.origin)
    sb.github.empty, sb.github.default_branch = True, "trunk"


def empty_repository(sb: Sandbox) -> None:
    """`empty_origin` and the refs of its clone: an unborn `main` and no `origin/main`."""
    empty_origin(sb)
    git("update-ref", "-d", "refs/heads/main", cwd=sb.root)
    git("update-ref", "-d", "refs/remotes/origin/main", cwd=sb.root)


def commit_seed(sb: Sandbox) -> None:
    """The consumer's own files, seeded by a test, as committed and pushed on `main`."""
    git("add", "-A", cwd=sb.root)
    git("commit", "-q", "-m", "seed", cwd=sb.root)
    git("push", "-q", "origin", "main", cwd=sb.root)


def host_link(target: Path, link: Path) -> None:
    """A link the host can create without privilege: a junction on Windows, else a symlink."""
    link.parent.mkdir(parents=True, exist_ok=True)
    if HOST == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=True,
        )
    else:
        os.symlink(target, link, target_is_directory=True)


def is_link(path: Path) -> bool:
    return os.path.islink(path) or os.path.isjunction(path)


class Runner:
    """The process boundary: logs each command, hands `gh` to the fake GitHub, emulates `npx`
    (unless `real_npx`), and runs every other command for real through the installer's `run`."""

    def __init__(
        self, init: ModuleType, platform: str, github: FakeGitHub, *, real_npx: bool = False
    ) -> None:
        self.init = init
        self.platform = platform
        self.github = github
        self.real_npx = real_npx
        self.log: list[list[str]] = []

    def gh(self, *prefix: str) -> list[list[str]]:
        """The logged `gh` commands whose arguments start with `prefix`."""
        return [
            cmd[1:] for cmd in self.log if is_gh(cmd) and cmd[1 : 1 + len(prefix)] == list(prefix)
        ]

    def __call__(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        capture: bool = True,
        input: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.log.append([str(part) for part in cmd])
        name = Path(cmd[0]).name.lower()
        if is_gh(cmd):
            return self.github([str(part) for part in cmd[1:]], input, env)
        if name.startswith("npx") and not self.real_npx:
            assert cwd is not None
            for rel in self.init.OPENSPEC_OUTPUT:
                path = Path(cwd) / rel
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    text = "schema: spec-driven\n" if rel == "openspec/config.yaml" else "x\n"
                    path.write_text(text, encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return self.init.run(cmd, cwd=cwd, env=env, capture=capture, input=input)

    def state_changing(self) -> list[str]:
        """One key per command that changes persistent state."""
        keys = []
        for cmd in self.log:
            name = Path(cmd[0]).name.lower()
            if name.startswith("npx"):
                keys.append("npx")
            elif is_gh(cmd) and cmd[1:2] == ["project"]:
                keys.append(f"gh-{cmd[2]}")
            elif is_gh(cmd) and cmd[2:3] == ["create"]:
                keys.append(f"gh-{cmd[1]}-create")
            elif name.startswith("git") and cmd[1:2] == ["-C"] and cmd[3] in GIT_WRITES:
                keys.append(cmd[3])
            elif name.startswith("git") and cmd[1:2] != ["-C"] and "clone" in cmd:
                keys.append("clone")
            elif name.startswith("git") and ("fetch" in cmd or "checkout" in cmd):
                keys.append(cmd[3] if cmd[1] == "-C" else cmd[1])
        return keys


# The consumer checkout's persistent git writes of the onboarding steps.
GIT_WRITES = {"switch", "commit", "push"}


def is_gh(cmd: list[str]) -> bool:
    return Path(str(cmd[0])).stem.lower() == "gh"


def install(
    init: ModuleType,
    sb: Sandbox,
    *args: str,
    platform: str = HOST,
    runner: Runner | None = None,
    on_write: Callable[[str], None] | None = None,
) -> int:
    injected = {} if sb.grafana is None else {"grafana": sb.grafana}
    host = init.Host(
        root=sb.root,
        home=sb.home,
        platform=platform,
        runner=runner or Runner(init, platform, sb.github),
        which=sb.which,
        on_write=on_write or (lambda label: None),
        **injected,
    )
    return init.install(list(args), host)


def snapshot(*bases: Path) -> dict[str, Any]:
    """Every file's bytes and every link's resolved target, keyed by path; git state is
    asserted explicitly, so `.git` is skipped."""
    state: dict[str, Any] = {}
    for base in bases:
        for top, dirs, files in os.walk(base):
            for name in list(dirs):
                path = Path(top) / name
                if name == ".git":
                    dirs.remove(name)
                elif is_link(path):
                    state[str(path)] = ("link", os.path.realpath(path))
                    dirs.remove(name)
            for name in files:
                path = Path(top) / name
                if is_link(path):
                    state[str(path)] = ("link", os.path.realpath(path))
                else:
                    state[str(path)] = path.read_bytes()
    return state


def relative(state: dict[str, Any], base: Path) -> dict[str, Any]:
    prefix = str(base) + os.sep
    return {key[len(prefix) :]: value for key, value in state.items() if key.startswith(prefix)}


def transitions(out: str) -> dict[str, str]:
    """The last status each label printed."""
    return {label: status for status, label in LINE.findall(out)}


def head_commit(path: Path) -> str:
    return git("rev-parse", "HEAD", cwd=path)


def tag_commit(sb: Sandbox, tag: str) -> str:
    return git("rev-parse", f"{tag}^{{commit}}", cwd=sb.repo)


# Names shared by the `test_init*.py` modules.

LABELS = [
    "onboarding-branch",
    "openspec",
    "config",
    "workflow",
    "review",
    "task-readings",
    "dependabot",
    "quality",
    "pre-commit",
    "settings",
    "check",
    "rules",
    "project-copy",
    "project-link",
    "onboarding-commit",
    "onboarding-issue",
    "onboarding-push",
    "onboarding-pr",
    "pre-push",
]
CONSUMER_FILES = {
    ".github/workflows/agent-process.yml",
    ".github/workflows/agent-review.yml",
    ".github/workflows/task-readings.yml",
    ".github/dependabot.yml",
    ".pre-commit-config.yaml",
    ".github/agent-process-quality.json",
    ".claude/settings.json",
    ".claude/agent-process-check.py",
    ".claude/rules/agent-process.md",
}
MARKETPLACE = "agent-process-marketplace"
PLUGIN = "agent-process@agent-process-marketplace"
CHECK_COMMAND = (
    'python "$CLAUDE_PROJECT_DIR/.claude/agent-process-check.py" '
    f"https://github.com/ekolvah/agent-process-distribution/blob/v{CURRENT}/skills/agent-process/SKILL.md#install"
)
CHECK_GROUP = {"hooks": [{"type": "command", "command": CHECK_COMMAND}]}
ATTRIBUTION = f"vcs.repository.name={OWNER}/{REPO_NAME},vcs.repository.url.full=https://github.com/{OWNER}/{REPO_NAME}"


def fresh_settings() -> dict[str, Any]:
    """The owned keys a fresh install writes into `.claude/settings.json`."""
    return {
        "extraKnownMarketplaces": {
            MARKETPLACE: {
                "source": {
                    "source": "github",
                    "repo": "ekolvah/agent-process-distribution",
                    "ref": "stable",
                },
                "autoUpdate": True,
            }
        },
        "hooks": {"SessionStart": [CHECK_GROUP]},
    }


def project_settings(sb: Sandbox, data: Any, text: str | None = None) -> Path:
    """The consumer's `.claude/settings.json`, `data` in the form `init` writes unless `text`
    is given, committed and pushed."""
    path = sb.root / ".claude" / "settings.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text or json.dumps(data, indent=2) + "\n", encoding="utf-8")
    commit_seed(sb)
    return path


def user_settings(sb: Sandbox, text: str) -> None:
    """This machine's `~/.claude/settings.json`."""
    (sb.home / ".claude").mkdir(exist_ok=True)
    (sb.home / ".claude" / "settings.json").write_text(text, encoding="utf-8")


def pins() -> dict[str, str]:
    """This repository's tool pins: the `name==version` lines of its dev lockfile."""
    text = (ROOT / ".agent-process" / "requirements-dev.txt").read_text(encoding="utf-8")
    return dict(ln.split("==", 1) for ln in text.splitlines() if "==" in ln and ln[0].isalpha())


def _installed(init: ModuleType, sb: Sandbox) -> None:
    assert install(init, sb, "--confirm") == 0
