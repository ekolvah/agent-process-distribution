"""Harness of the installer tests: the fixture release repository, the fake GitHub behind
`gh`, the process-boundary runner and the state readers. Shared by the `test_init*.py` modules
and the `conftest.py` fixtures."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "skills" / "agent-process"
INIT = PACKAGE / "scripts" / "init.py"
HOST = "win32" if sys.platform == "win32" else "linux"

LINE = re.compile(r"^(planned|unchanged|written|conflict) ([a-z-]+):", re.MULTILINE)
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
# them: a private copy without `Auto-add to project` (observed 2026-09-30, change
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
SECRET_403 = (
    "failed to get secrets: HTTP 403: Resource not accessible by integration "
    f"(https://api.github.com/repos/{OWNER}/{REPO_NAME}/actions/secrets?per_page=100)\n"
)


def _copied_workflows() -> dict[str, bool]:
    return {name: True for name in TEMPLATE_WORKFLOWS if name != "Auto-add to project"}


@dataclass
class Project:
    owner: str
    number: int
    title: str
    closed: bool = False
    repositories: set[str] = field(default_factory=set)
    public: bool = False
    workflows: dict[str, bool] = field(default_factory=_copied_workflows)
    areas: list[str] = field(default_factory=lambda: list(TEMPLATE_AREAS))

    @property
    def url(self) -> str:
        return f"https://github.com/users/{self.owner}/projects/{self.number}"


class FakeGitHub:
    """GitHub behind `gh` for the consumer `ekolvah/consumer`. It starts with template
    Project 4 linked to the publisher; `faults[command]` makes the next `copy` or `link`
    exit 1 either before its effect or after it (the lost response). Issues and PRs share
    one numbering, as on GitHub; `pr create` needs its head and base pushed to `origin`.
    `default_branch` is the settings' name; `empty` makes `repo view` print the empty
    `defaultBranchRef.name` of a repository with no commits (change init-empty-repository).
    `secrets` are the consumer's secret names; `faults["secret-list"]` and
    `faults["project-read"]` make those reads exit 1 (change manual-rows-from-state)."""

    def __init__(self) -> None:
        template = Project(OWNER, 4, "agent-process-distribution agent process", public=True)
        template.workflows = {name: True for name in TEMPLATE_WORKFLOWS}
        template.repositories.add(PUBLISHER)
        self.projects = [template]
        self.secrets: set[str] = set()
        self.faults: dict[str, str] = {}
        self.hidden = 0  # Projects the owner has beyond the first page
        self.issues: list[dict[str, Any]] = []
        self.pulls: list[dict[str, Any]] = []
        self.origin: Path | None = None
        self.default_branch = "main"
        self.empty = False

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

    def __call__(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args == ["api", f"repos/{OWNER}/{REPO_NAME}"]:
            return _done(args, {"name": REPO_NAME, "default_branch": self.default_branch})
        if args[:2] == ["secret", "list"]:
            assert args[2:] == ["--repo", f"{OWNER}/{REPO_NAME}", "--json", "name"], args
            if "secret-list" in self.faults:
                return _done(args, code=1, err=SECRET_403)
            return _done(args, [{"name": name} for name in sorted(self.secrets)])
        if args[:2] == ["api", "graphql"] and "projectV2(number:" in args[3]:
            return self._project_read(args)
        return self._items(args) if args[0] in {"issue", "pr"} else self._projects(args)

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
            assert set(flags) == {"--head"} and state in {"open", "all"}, args
            assert set(fields) <= {"number", "state", "url"}, args
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
        """The linked Project's visibility, workflows and `Area` options and the template's
        `Area` options, from the `owner`/`number` and `template`/`source` variables, in the
        observed shape."""
        if "project-read" in self.faults:
            return _done(args, code=1, err="gh: Could not resolve to a ProjectV2\n")
        variables = dict(part.split("=", 1) for part in args[3::2])

        def project(owner: str, number: str) -> Project:
            (found,) = [p for p in self.projects if (p.owner, p.number) == (owner, int(number))]
            return found

        def area(p: Project) -> dict[str, Any]:
            return {"options": [{"name": name} for name in p.areas]}

        linked = project(variables["owner"], variables["number"])
        template = project(variables["template"], variables["source"])
        workflows = [{"name": name, "enabled": on} for name, on in linked.workflows.items()]
        node = {"public": linked.public, "workflows": {"nodes": workflows}, "field": area(linked)}
        data = {"linked": {"projectV2": node}, "template": {"projectV2": {"field": area(template)}}}
        return _done(args, {"data": data})


def which(name: str) -> str | None:
    return shutil.which(name) or name


@dataclass
class Sandbox:
    """`which` is the installer's PATH lookup; a test replaces it to report a tool absent."""

    root: Path
    home: Path
    repo: Path
    other: Path
    github: FakeGitHub = field(default_factory=FakeGitHub)
    which: Callable[[str], str | None] = which

    @property
    def link(self) -> Path:
        return self.home / ".agents" / "skills" / "agent-process"

    @property
    def origin(self) -> Path:
        return self.root.parent / "origin.git"


BRANCH = f"agent-process/install-{CURRENT}"


def gitconfig(sb: Sandbox) -> str:
    """The sandbox's global git config: no `https://` URL reaches the network, and the
    process repository is the fixture's, which the pre-push hook's pre-commit clones (change
    hermetic-sandbox-push, design D1, D2)."""
    return (
        '[url "file:///no-network/"]\n\tinsteadOf = https://\n'
        f'[url "{sb.repo.as_posix()}"]\n\tinsteadOf = {PROCESS_URL}\n'
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
    ) -> subprocess.CompletedProcess[str]:
        self.log.append([str(part) for part in cmd])
        name = Path(cmd[0]).name.lower()
        if is_gh(cmd):
            return self.github([str(part) for part in cmd[1:]])
        if name.startswith("npx") and not self.real_npx:
            assert cwd is not None
            for rel in self.init.OPENSPEC_OUTPUT:
                path = Path(cwd) / rel
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    text = "schema: spec-driven\n" if rel == "openspec/config.yaml" else "x\n"
                    path.write_text(text, encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return self.init.run(cmd, cwd=cwd, env=env, capture=capture)

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
    host = init.Host(
        root=sb.root,
        home=sb.home,
        platform=platform,
        runner=runner or Runner(init, platform, sb.github),
        which=sb.which,
        on_write=on_write or (lambda label: None),
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
    "dependabot",
    "pre-commit",
    "settings",
    "check",
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
    ".github/dependabot.yml",
    ".pre-commit-config.yaml",
    ".claude/settings.json",
    ".claude/agent-process-check.py",
}
MARKETPLACE = "agent-process-marketplace"
PLUGIN = "agent-process@agent-process-marketplace"
CHECK_COMMAND = (
    'python "$CLAUDE_PROJECT_DIR/.claude/agent-process-check.py" '
    f"https://github.com/ekolvah/agent-process-distribution/blob/v{CURRENT}/skills/agent-process/SKILL.md#install"
)
CHECK_GROUP = {"hooks": [{"type": "command", "command": CHECK_COMMAND}]}


def _installed(init: ModuleType, sb: Sandbox) -> None:
    assert install(init, sb, "--confirm") == 0
