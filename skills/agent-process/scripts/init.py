#!/usr/bin/env python3
"""Install the agent process into the consumer repository at the current directory.

Usage: python init.py [--version <x.y.z>] (--dry-run | --confirm)

The requested release owns its run. With `--version` equal to `VERSION` this file runs
itself; otherwise it clones the requested tag into a temporary directory, removed afterwards,
and runs that tree's `init.py`, forwarding its output and exit code; `--confirm` first prints
`planned hand-off`. The hidden `--selected-release` marks a handed-off child: a tag whose
`VERSION` differs from the requested version exits 1 instead of recursing. Nothing is written
in the user profile.

A run first classifies every transition from observed state — `planned`, `unchanged`, or
`conflict` — and prints one line per transition. Any conflict exits 2 before the first
write; `--dry-run` stops after the plan. Confirmed writes run in a fixed order and print
`written` or `unchanged`:

1. onboarding-root    in a repository with no commits only: one commit with no files pushed to
                       the default branch the repository's settings name, and fetched
2. onboarding-branch  `git switch -c agent-process/install-<version>` from the default branch
3. openspec  the pinned `openspec init`, recorded by the `# openspec:` line of the block
4. config    the marker block of `openspec/config.yaml`, recording `VERSION` by its
             `# agent-process release:` line, which `release_drift` compares
5. workflow  the managed `.github/workflows/agent-process.yml`
6. review    the managed `.github/workflows/agent-review.yml`, the review gate
7. dependabot  the marker block of `.github/dependabot.yml`
8. quality   `.github/agent-process-quality.json`, seeded only beside a created
             `.pre-commit-config.yaml`; an existing declaration is `unchanged`
9. pre-commit  the marker block of `.pre-commit-config.yaml`: the `pre-push` hook that runs
               the declared test; a created file also carries the baseline toolchain
10. settings  the owned marketplace entry and `SessionStart` hook group of `.claude/settings.json`,
              removing the plugin's `enabledPlugins` entry: the plugin is installed at user scope
11. check     the managed `.claude/agent-process-check.py` that hook runs
12. project-copy `gh project copy` of the template Project as `<repository> agent process`,
                unless the repository has a linked Project or its owner an unlinked copy
13. project-link `gh project link` of that one unlinked copy to the repository
14. onboarding-commit  `git add -A` and `git commit` on the installation branch
15. onboarding-issue   `gh issue create` of `Install agent-process <version>`, unless one is open
16. onboarding-push    `git push -u origin` of the installation branch
17. onboarding-pr      `gh pr create` into the default branch, its body `Closes #<issue>`; the
                       written line names the PR's URL
18. pre-push  `pre-commit install --hook-type pre-push` in this clone, whatever else is planned;
              a hook pre-commit did not install moves to `pre-push.legacy`. Its cache
              goes to a temporary `PRE_COMMIT_HOME`, not the user profile

Steps 12-13 are classified from `gh` reads of the repository's linked Projects and its
owner's Projects, never from a previous run's output, so a retry reuses a copy that exists.
The onboarding steps exist only when a file step is planned or the checkout is on the
installation branch, and are classified from git and `gh` reads the same way; a merged
installation PR makes them `unchanged`, and any other starting point — another branch, a dirty
worktree, the branch not checked out, a PR closed unmerged, a checkout with commits of a
repository with none, a checkout with none of a repository with commits — is an
`onboarding-branch` conflict naming the command that resolves it.
The output ends with `manual` rows, read after the run's writes and printed only while their
state is not observed done: the linked Project's visibility, built-in workflows and the `Area`
options and views copied from the template, and the review caller's `CLAUDE_CODE_OAUTH_TOKEN`
secret — that only a UI can change — the `plugin-channel` row, the once-per-machine step that
points the marketplace at `stable` with auto-update and installs the plugin at user scope, and
the `pre-push` row naming why `init` cannot install this clone's hook (`core.hooksPath` is set,
or `pre-commit` is not on PATH). A state `init` cannot read keeps its row with
`(cannot read: <reason>)` and never changes the exit code. While
`.github/agent-process-quality.json` declares no `test` and the run seeds none, a `quality:`
status line before the `manual` rows says so, as a state, not an action: the installer
asks for no quality command. The default branch is written only by `onboarding-root`: the
installation branch is otherwise the only push, and the Project copy and link, the issue and the
PR the only other GitHub writes.
`AGENT_PROCESS_REPOSITORY` overrides the process repository; the
plan then prints it as its first line.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import manual
import onboarding
import quality
from steps import InstallError, Step

VERSION = "3.9.0"  # x-release-please-version
REPOSITORY = "https://github.com/ekolvah/agent-process-distribution.git"
REPOSITORY_ENV = "AGENT_PROCESS_REPOSITORY"
GITHUB_REPO = "ekolvah/agent-process-distribution"
OPENSPEC = "1.13.0"
# `openspec init --tools claude` of the pin in a fresh repository (observed 2026-09-27).
OPENSPEC_OUTPUT = (
    *(
        f".claude/skills/openspec-{name}/SKILL.md"
        for name in (
            "apply-change",
            "archive-change",
            "explore",
            "propose",
            "sync-specs",
            "update-change",
        )
    ),
    *(
        f".claude/commands/opsx/{name}.md"
        for name in ("apply", "archive", "explore", "propose", "sync", "update")
    ),
    "openspec/changes/archive/.gitkeep",
    "openspec/config.yaml",
    "openspec/specs/.gitkeep",
)
BEGIN = "# agent-process:begin"
END = "# agent-process:end"
MANAGED = "# agent-process:managed"
PIN = "# openspec: "
RELEASE = "# agent-process release: "
# A top-level `rules` key in any YAML spelling: plain, quoted, tagged or anchored, an explicit
# `?` key, a flow mapping that opens the document (which may hold one), or a double-quoted key
# with an escape (which may spell it).
TOP_LEVEL_RULES = re.compile(
    r"""^(?:\{|(?:\?\s*)?(?:[!&]\S*\s+)*"""
    r"""(?:rules|"rules"|'rules'|"(?=[^"]*\\)(?:[^"\\]|\\.)*")\s*(?::|$))"""
)
MARKETPLACE = "agent-process-marketplace"
PLUGIN = "agent-process@agent-process-marketplace"
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
CONFIG = "openspec/config.yaml"
WORKFLOW = ".github/workflows/agent-process.yml"
REVIEW_WORKFLOW = ".github/workflows/agent-review.yml"
DEPENDABOT = ".github/dependabot.yml"
PRE_COMMIT = ".pre-commit-config.yaml"
SETTINGS = ".claude/settings.json"
CHECK = ".claude/agent-process-check.py"
TEMPLATE_OWNER = "ekolvah"
TEMPLATE_PROJECT = "4"
# The owner's Projects with what tells a reusable copy from one linked elsewhere; `gh project
# list` carries no linked repositories (observed 2026-09-23).
PROJECTS_QUERY = (
    "query($login:String!){repositoryOwner(login:$login){... on ProjectV2Owner{"
    "projectsV2(first:100){totalCount nodes{number title closed url repositories{totalCount}}}"
    "}}}"
)
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class Conflict(Exception):
    """A target the installer does not own."""


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """The process boundary. Captured output is UTF-8; uncaptured output goes to this
    process's own streams and `stdout`/`stderr` stay `None`."""
    return subprocess.run(
        [str(part) for part in cmd],
        cwd=cwd,
        env=env,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


# --- rendering --------------------------------------------------------------------------


def _template(name: str, **values: str) -> str:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    return string.Template(text).substitute(values)


def render_workflow(version: str) -> str:
    """The managed caller; it passes no command — the repository declares them."""
    return _template("agent-process.yml", version=version)


def render_review_workflow(version: str) -> str:
    """The managed review caller; its secret is the consumer's own."""
    return _template("agent-review.yml", version=version)


def render_config_block() -> str:
    return _template("config.yaml", openspec=OPENSPEC, version=VERSION)


def _render_settings(version: str) -> dict[str, Any]:
    return json.loads(_template("settings.json", version=version))


def _span(lines: list[str]) -> tuple[int, int] | None:
    """The line indexes of the one marker block, `None` without markers."""
    begins = [i for i, line in enumerate(lines) if line.strip() == BEGIN]
    ends = [i for i, line in enumerate(lines) if line.strip() == END]
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or begins[0] > ends[0]:
        raise Conflict("agent-process markers are repeated, unpaired, or out of order")
    return begins[0], ends[0]


def _replace_block(lines: list[str], block: list[str]) -> list[str]:
    """`lines` come from `str.split("\\n")`, so joining them back loses no byte."""
    span = _span(lines)
    if span is None:
        head = lines[:-1] if lines[-1] == "" else lines
        return [*head, *block, ""]
    return [*lines[: span[0]], *block, *lines[span[1] + 1 :]]


def _parent_conflict(path: Path) -> str | None:
    """A link or non-directory as the nearest existing parent: creating `path` would fail."""
    parent = path.parent
    while not os.path.lexists(parent):
        parent = parent.parent
    if _is_link(parent) or not parent.is_dir():
        return f"has a parent `{parent.name}` that is not a directory"
    return None


def _read(path: Path) -> str | None:
    """Decoded text with `\\n` line endings, `None` when absent. A link, a non-file, a
    non-directory parent, or mixed line endings are the person's: a write would replace
    them or fail mid-run."""
    if _is_link(path) or (os.path.lexists(path) and not path.is_file()):
        raise Conflict("is not a regular file")
    if reason := _parent_conflict(path):
        raise Conflict(reason)
    if not path.is_file():
        return None
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise Conflict("is not UTF-8") from None
    if "\r" in text and not text.count("\r") == text.count("\r\n") == text.count("\n"):
        raise Conflict("mixes line endings")
    return text.replace("\r\n", "\n")


def _eol(path: Path) -> str:
    """The line ending a write keeps: `_read` admits only all-LF or all-CRLF files."""
    return "\r\n" if path.is_file() and b"\r\n" in path.read_bytes() else "\n"


def _write(path: Path, text: str, eol: str = "\n") -> None:
    """Atomic UTF-8 write of `\\n`-ended `text` with `eol` endings via a sibling temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=eol) as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _is_link(path: Path) -> bool:
    return os.path.islink(path) or os.path.isjunction(path)


# --- transitions ------------------------------------------------------------------------


@dataclass
class Host:
    root: Path
    home: Path
    platform: str
    runner: Runner
    which: Callable[[str], str | None]
    on_write: Callable[[str], None]


@dataclass
class Context:
    root: Path
    home: Path
    platform: str
    runner: Runner
    which: Callable[[str], str | None]
    repository: str
    version: str

    @property
    def tag(self) -> str:
        return f"v{self.version}"

    def exe(self, name: str) -> str:
        found = self.which(name)
        if not found:
            raise InstallError(f"{name} not found on PATH")
        return found

    def call(
        self,
        name: str,
        *args: str,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        done = self.runner([self.exe(name), *args], cwd=cwd, env=env)
        if check and done.returncode != 0:
            streams = [s.strip() for s in (done.stderr, done.stdout) if s is not None]
            output = "\n".join(s for s in streams if s) if streams else "output not captured"
            raise InstallError(f"`{name} {' '.join(args)}` exited {done.returncode}: {output}")
        return done

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        # No optional locks: a status read never refreshes the index of a checkout it inspects.
        env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        return self.call("git", *args, env=env, check=check)


def _hand_off(ctx: Context, argv: list[str], tree: Path) -> int:
    """Run the release in `tree` with the same arguments; its output and exit code are ours."""
    script = tree / "skills" / "agent-process" / "scripts" / "init.py"
    if not script.is_file():
        raise InstallError(f"{ctx.tag} carries no installer at {script}")
    sys.stdout.flush()
    sys.stderr.flush()
    done = ctx.runner(
        [sys.executable, str(script), *argv, "--selected-release"], cwd=ctx.root, capture=False
    )
    return done.returncode


def _recorded(text: str | None, prefix: str) -> str | None:
    """The value of the block's `prefix` line, `None` without a readable one."""
    if text is None:
        return None
    lines = text.splitlines()
    try:
        span = _span(lines)
    except Conflict:
        return None
    if span is None:
        return None
    for line in lines[span[0] + 1 : span[1]]:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def release_drift(root: Path, script_dir: Path) -> str | None:
    """`None` when `root` records this skill's release or `script_dir` is the publisher's
    source checkout of `root`; otherwise the message naming both releases and the fix."""
    publisher = root / "skills" / "agent-process" / "scripts"
    if os.path.normcase(script_dir.resolve()) == os.path.normcase(publisher.resolve()):
        return None
    try:
        recorded = _recorded(_read(root / CONFIG), RELEASE)
    except Conflict:
        recorded = None
    if recorded == VERSION:
        return None
    head = f"release drift: project records {recorded or 'none'}, skill is {VERSION}"
    parsed = recorded is not None and re.fullmatch(r"\d+\.\d+\.\d+", recorded)
    if parsed and _release(parsed[0]) > _release(VERSION):
        return (
            f"{head} — update the skill to {recorded}: "
            "`claude plugin update agent-process@agent-process-marketplace --scope <user|project>` "
            "(the scope `claude plugin list` shows for this project); then restart the session"
        )
    install = TEMPLATES.parent / "SKILL.md"
    return f"{head} — re-run Install with this skill ({install}#install)"


def _release(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _with_pin(text: str) -> str:
    lines = text.split("\n")
    span = _span(lines)
    if span is None:
        return "\n".join(_replace_block(lines, [BEGIN, PIN + OPENSPEC, END]))
    inner = [line for line in lines[span[0] + 1 : span[1]] if not line.startswith(PIN)]
    return "\n".join([*lines[: span[0] + 1], PIN + OPENSPEC, *inner, *lines[span[1] :]])


def _openspec(ctx: Context) -> Step:
    config = ctx.root / CONFIG
    detail = f"openspec init --tools claude (@fission-ai/openspec@{OPENSPEC})"

    def current() -> bool:
        paths = all((ctx.root / rel).exists() for rel in OPENSPEC_OUTPUT)
        try:
            text = _read(config)
        except Conflict:  # reported by the config step, which runs before any write
            return False
        return paths and _recorded(text, PIN) == OPENSPEC

    def apply() -> bool:
        if current():
            return False
        ctx.call(
            "npx",
            "-y",
            f"@fission-ai/openspec@{OPENSPEC}",
            "init",
            "--tools",
            "claude",
            "--no-animation",
            cwd=ctx.root,
            env={**os.environ, "OPENSPEC_TELEMETRY": "0"},
        )
        _write(config, _with_pin(_read(config) or ""), _eol(config))
        return True

    return Step("openspec", "unchanged" if current() else "planned", detail, apply)


def _config_text(ctx: Context) -> tuple[str | None, str]:
    text = _read(ctx.root / CONFIG)
    lines = (text or "").split("\n")
    span = _span(lines)
    outside = lines if span is None else [*lines[: span[0]], *lines[span[1] + 1 :]]
    # A column-0 match is the whole top-level check only for one document whose root starts
    # at column 0; there alone the appended column-0 block also stays valid YAML.
    content = [
        line
        for line in outside
        if line.strip() and not line.lstrip().startswith("#") and not line.startswith("%")
    ]
    if content and content[0][0].isspace():
        raise Conflict("has an indented root mapping")
    if any(re.match(r"(?:---|\.\.\.)(?:\s|$)", line) for line in content[1:]):
        raise Conflict("holds more than one YAML document")
    if any(TOP_LEVEL_RULES.match(line) for line in outside):
        raise Conflict("has a top-level `rules` outside the agent-process block")
    block = render_config_block().splitlines()
    return text, "\n".join(_replace_block(lines, block))


def _managed_text(ctx: Context, rel: str, rendered: str) -> tuple[str | None, str]:
    text = _read(ctx.root / rel)
    if text is not None and text.split("\n", 1)[0].strip() != MANAGED:
        raise Conflict(f"exists without its first line `{MANAGED}`")
    return text, rendered


def _test_declared(root: Path) -> bool:
    """Whether the repository declares a `test`; a malformed declaration declares none (D5)."""
    try:
        return quality.read(root) is not None
    except ValueError:
        return False


# The `test:` input of a caller rendered by `init` up to 3.0.2.
_PASSED_TEST = re.compile(r"^ +test: *\S.*$", re.MULTILINE)


def _workflow_text(ctx: Context) -> tuple[str | None, str]:
    text, rendered = _managed_text(ctx, WORKFLOW, render_workflow(ctx.version))
    passed = _PASSED_TEST.search(text or "")
    if passed and not _test_declared(ctx.root):
        # The new caller passes no command: rewriting it would stop the tests silently.
        raise Conflict(
            f"passes the quality command `{passed.group().strip()}`; declare it in "
            f'{quality.DECLARATION} as {{"test": "<command>"}}, or delete this caller '
            "when the repository has no tests"
        )
    return text, rendered


def _review_text(ctx: Context) -> tuple[str | None, str]:
    return _managed_text(ctx, REVIEW_WORKFLOW, render_review_workflow(ctx.version))


def _dependabot_text(ctx: Context) -> tuple[str | None, str]:
    return _block_text(ctx, DEPENDABOT, _template("dependabot.yml"))


def _pre_commit_text(ctx: Context) -> tuple[str | None, str]:
    return _block_text(ctx, PRE_COMMIT, _template("pre-commit-config.yaml", version=ctx.version))


def _block_text(ctx: Context, rel: str, rendered: str) -> tuple[str | None, str]:
    """A consumer file whose marker block `init` owns: a fresh file gets the whole template,
    a file with the block gets the block replaced, a file without it is a conflict."""
    text = _read(ctx.root / rel)
    if text is None or not text.strip():
        return text, rendered
    lines = text.split("\n")
    if _span(lines) is None:
        raise Conflict("exists without an agent-process block")
    template = rendered.splitlines()
    span = _span(template)
    assert span is not None
    return text, "\n".join(_replace_block(lines, template[span[0] : span[1] + 1]))


def _settings_text(ctx: Context) -> tuple[str | None, str]:
    text = _read(ctx.root / SETTINGS)
    try:
        data = json.loads(text) if text is not None else {}
    except json.JSONDecodeError as exc:
        raise Conflict(f"is not valid JSON ({exc.msg})") from None
    if not isinstance(data, dict):
        raise Conflict("is not a JSON object")
    wanted = _render_settings(ctx.version)
    for key in ("extraKnownMarketplaces", "enabledPlugins"):
        if not isinstance(data.get(key, {}), dict):
            raise Conflict(f"`{key}` is not an object")
    group = wanted["hooks"]["SessionStart"][0]
    hooks, starts, new_starts = _session_starts(data, group)
    marketplaces = data.get("extraKnownMarketplaces", {})
    plugins = data.get("enabledPlugins", {})
    market = marketplaces.get(MARKETPLACE)
    if MARKETPLACE in marketplaces:
        source = market.get("source") if isinstance(market, dict) else None
        repo = source.get("repo") if isinstance(source, dict) else None
        if repo != GITHUB_REPO:
            raise Conflict(f"`{MARKETPLACE}` names {repo!r}, not {GITHUB_REPO}")
    if plugins.get(PLUGIN, True) is not True:
        raise Conflict(f"`{PLUGIN}` is set to {json.dumps(plugins[PLUGIN])}")
    entry = wanted["extraKnownMarketplaces"][MARKETPLACE]
    if market == entry and PLUGIN not in plugins and starts == new_starts:
        return text, text or ""
    # Re-serialising is lossless only from the form written here; any other form (spacing,
    # key order, escapes, repeated keys) is the person's to edit.
    if text is not None and text != json.dumps(data, indent=2, ensure_ascii=False) + "\n":
        raise Conflict(
            f'is not in the form init writes; add `"extraKnownMarketplaces": {{"{MARKETPLACE}":'
            f" {json.dumps(entry)}}}` and the `hooks.SessionStart` group {json.dumps(group)},"
            f" and remove the `{PLUGIN}` entry of `enabledPlugins`, by hand"
        )
    updated = _without_plugin(data)
    updated["extraKnownMarketplaces"] = {**marketplaces, MARKETPLACE: entry}
    updated["hooks"] = {**hooks, "SessionStart": new_starts}
    return text, json.dumps(updated, indent=2, ensure_ascii=False) + "\n"


def _without_plugin(data: dict[str, Any]) -> dict[str, Any]:
    """A copy of `data` without the plugin's `enabledPlugins` entry, which earlier releases wrote.
    An emptied `enabledPlugins` stays: the key is the consumer's."""
    if "enabledPlugins" not in data:
        return dict(data)
    plugins = {k: v for k, v in data["enabledPlugins"].items() if k != PLUGIN}
    return {**data, "enabledPlugins": plugins}


def _session_starts(
    data: dict[str, Any], group: dict[str, Any]
) -> tuple[dict[str, Any], list[Any], list[Any]]:
    """`hooks`, its `SessionStart` groups, and those groups with the owned one in place: the
    first owned group is replaced, a repeated one dropped, a missing one appended."""
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise Conflict("`hooks` is not an object")
    starts = hooks.get("SessionStart", [])
    if not isinstance(starts, list):
        raise Conflict("`hooks.SessionStart` is not a list")
    owned = [i for i, start in enumerate(starts) if _is_owned_start(start, group)]
    new_starts = [start for i, start in enumerate(starts) if i not in owned[1:]]
    if owned:
        new_starts[owned[0]] = group
    else:
        new_starts.append(group)
    return hooks, starts, new_starts


def _is_owned_start(start: Any, group: dict[str, Any]) -> bool:
    """`start` is the owned group: exactly `group` as some release writes it, differing only
    in the release tag of the Install URL. Anything else is the consumer's."""
    command = group["hooks"][0]["command"]
    head, tail = re.split(r"/blob/v[^/]+/", command)
    pattern = re.escape(head) + r"/blob/v[^/\s]+/" + re.escape(tail)
    hooks = start.get("hooks") if isinstance(start, dict) else None
    return (
        isinstance(hooks, list)
        and len(start) == 1
        and len(hooks) == 1
        and isinstance(hooks[0], dict)
        and hooks[0].keys() == {"type", "command"}
        and hooks[0]["type"] == "command"
        and re.fullmatch(pattern, str(hooks[0]["command"])) is not None
    )


def _check_text(ctx: Context) -> tuple[str | None, str]:
    text = _read(ctx.root / CHECK)
    if text is not None and text.split("\n", 1)[0].strip() != MANAGED:
        raise Conflict(f"exists without its first line `{MANAGED}`")
    return text, (TEMPLATES / "skill_check.py").read_text(encoding="utf-8")


def _file_step(
    ctx: Context, label: str, rel: str, render: Callable[[Context], tuple[str | None, str]]
) -> Step:
    path = ctx.root / rel

    def apply() -> bool:
        try:
            current, wanted = render(ctx)
        except Conflict as exc:
            raise InstallError(f"{rel} {exc}") from None
        if current == wanted:
            return False
        _write(path, wanted, _eol(path))
        return True

    try:
        current, wanted = render(ctx)
    except Conflict as exc:
        return Step(label, "conflict", f"{rel} {exc}")
    return Step(label, "unchanged" if current == wanted else "planned", rel, apply)


def _quality_text(ctx: Context) -> tuple[str | None, str]:
    """An existing declaration, even a malformed one, is the repository's (D4)."""
    text = _read(ctx.root / quality.DECLARATION)
    return text, text if text is not None else _template("agent-process-quality.json")


def _seeds_quality(root: Path) -> bool:
    """Whether the `quality` step is listed: `unchanged` when the declaration exists, `planned`
    when neither it nor the config it runs exists yet (D4)."""
    if os.path.lexists(root / quality.DECLARATION):
        return True
    try:
        text = _read(root / PRE_COMMIT)
    except Conflict:
        return False
    return text is None or not text.strip()


def _consumer_steps(ctx: Context) -> list[Step]:
    seed = _seeds_quality(ctx.root)
    return [
        _openspec(ctx),
        _file_step(ctx, "config", CONFIG, _config_text),
        _file_step(ctx, "workflow", WORKFLOW, _workflow_text),
        _file_step(ctx, "review", REVIEW_WORKFLOW, _review_text),
        _file_step(ctx, "dependabot", DEPENDABOT, _dependabot_text),
        *([_file_step(ctx, "quality", quality.DECLARATION, _quality_text)] if seed else []),
        _file_step(ctx, "pre-commit", PRE_COMMIT, _pre_commit_text),
        _file_step(ctx, "settings", SETTINGS, _settings_text),
        _file_step(ctx, "check", CHECK, _check_text),
    ]


def _gh_json(ctx: Context, *args: str) -> Any:
    done = ctx.call("gh", *args, cwd=ctx.root)
    if done.stdout is None:
        raise InstallError(f"`gh {args[0]} {args[1]}` output not captured")
    try:
        return json.loads(done.stdout)
    except json.JSONDecodeError:
        raise InstallError(f"`gh {args[0]} {args[1]}` printed no JSON") from None


def _repository(ctx: Context) -> tuple[str, str, str, list[dict[str, Any]]]:
    """Owner, name, default branch, and the Projects linked to the repository (gh prints them
    under `Nodes`)."""
    data = _gh_json(ctx, "repo", "view", "--json", "owner,name,projectsV2,defaultBranchRef")
    try:
        linked = data.get("projectsV2") or {}
        nodes = linked.get("Nodes", linked.get("nodes")) or []
        default = str(data["defaultBranchRef"]["name"])
        return str(data["owner"]["login"]), str(data["name"]), default, list(nodes)
    except (AttributeError, KeyError, TypeError):
        raise InstallError(f"`gh repo view` printed an unexpected shape: {data}") from None


def _settings_default(ctx: Context, owner: str, name: str) -> str:
    """The default branch the settings name: `repo view` names none in a repository with no
    commits."""
    data = _gh_json(ctx, "api", f"repos/{owner}/{name}")
    default = data.get("default_branch") if isinstance(data, dict) else None
    if not isinstance(default, str) or not default:
        raise InstallError(f"`gh api repos/{owner}/{name}` names no default branch: {data}")
    return default


def _reusable(ctx: Context, owner: str, title: str) -> tuple[list[dict[str, Any]], list[str]]:
    """The owner's open, unlinked Projects titled `title`, and every one so titled, named."""
    data = _gh_json(ctx, "api", "graphql", "-f", f"query={PROJECTS_QUERY}", "-f", f"login={owner}")
    try:
        projects = data["data"]["repositoryOwner"]["projectsV2"]
        nodes, total = list(projects["nodes"]), int(projects["totalCount"])
    except (KeyError, TypeError, ValueError):
        raise InstallError(f"the Projects of {owner} have an unexpected shape: {data}") from None
    if total > len(nodes):
        raise InstallError(
            f"{owner} has {total} Projects and init reads {len(nodes)}; "
            f"it cannot prove `{title}` unique"
        )
    same = [node for node in nodes if node.get("title") == title]
    reusable = [
        node
        for node in same
        if not node.get("closed") and node.get("repositories", {}).get("totalCount") == 0
    ]
    named = [
        f"#{node.get('number')}"
        + (" closed" if node.get("closed") else "")
        + (" linked" if node.get("repositories", {}).get("totalCount") else "")
        for node in same
    ]
    return reusable, named


def _project_steps(
    ctx: Context, owner: str, name: str, linked: list[dict[str, Any]]
) -> tuple[list[Step], str]:
    """Steps 9-10 from the remote state alone, and the repository's `owner/name`."""
    repo = f"{owner}/{name}"
    title = f"{name} agent process"
    if len(linked) == 1:
        detail = f"#{linked[0].get('number')} {linked[0].get('title')!r} linked to {repo}"
        return (
            [
                Step("project-copy", "unchanged", detail),
                Step("project-link", "unchanged", detail),
            ],
            repo,
        )
    if len(linked) > 1:
        numbers = ", ".join(f"#{node.get('number')}" for node in linked)
        return (
            [
                Step("project-copy", "conflict", f"{numbers} are linked to {repo}; keep one"),
                Step("project-link", "conflict", f"several Projects are linked to {repo}"),
            ],
            repo,
        )
    reusable, named = _reusable(ctx, owner, title)

    def link() -> bool:
        found, names = _reusable(ctx, owner, title)
        if len(found) != 1:
            listed = ", ".join(names) or "none"
            raise InstallError(f"expected one unlinked Project `{title}` of {owner}: {listed}")
        number = str(found[0].get("number"))
        ctx.call("gh", "project", "link", number, "--owner", owner, "--repo", name, cwd=ctx.root)
        return True

    if len(reusable) == 1:
        number = reusable[0].get("number")
        return (
            [
                Step("project-copy", "unchanged", f"#{number} {title!r} of {owner}"),
                Step("project-link", "planned", f"#{number} -> {repo}", link),
            ],
            repo,
        )
    if named:
        why = "several" if reusable else "none of them open and unlinked"
        detail = f"Projects `{title}` of {owner}: {', '.join(named)} ({why})"
        return (
            [
                Step("project-copy", "conflict", detail),
                Step("project-link", "conflict", "no single Project to link"),
            ],
            repo,
        )

    def copy() -> bool:
        ctx.call(
            "gh",
            "project",
            "copy",
            TEMPLATE_PROJECT,
            "--source-owner",
            TEMPLATE_OWNER,
            "--target-owner",
            owner,
            "--title",
            title,
            cwd=ctx.root,
        )
        return True

    source = f"{TEMPLATE_OWNER} #{TEMPLATE_PROJECT}"
    return (
        [
            Step("project-copy", "planned", f"{source} -> {owner} as {title!r}", copy),
            Step("project-link", "planned", f"the copy -> {repo}", link),
        ],
        repo,
    )


def _manual(ctx: Context, repo: str) -> list[str]:
    """What only the Project's UI, the repository's settings, the machine or the clone can do,
    while its state is not observed done (`manual.py`); `init` prints it and never performs it."""
    return manual.rows(_target(ctx, repo))


def _target(ctx: Context, repo: str) -> manual.Target:
    return manual.Target(
        repo=repo,
        root=ctx.root,
        home=ctx.home,
        gh=lambda *args: ctx.call("gh", *args, cwd=ctx.root, check=False),
        git=lambda *args: ctx.git("-C", str(ctx.root), *args, check=False),
        template=(TEMPLATE_OWNER, TEMPLATE_PROJECT),
        source=GITHUB_REPO,
        marketplace=MARKETPLACE,
        plugin=PLUGIN,
        pre_commit=ctx.which("pre-commit"),
    )


def _pre_push_step(ctx: Context, repo: str) -> list[Step]:
    """This clone's pre-push hook, installed by pre-commit whatever else the run plans. A clone
    `init` cannot install, or cannot read, has no step: its `manual pre-push` row says why."""
    target = _target(ctx, repo)
    try:
        state = manual.pre_push(target)
    except manual.Unreadable:
        return []
    if state.blocked:
        return []
    if state.installed:
        return [Step("pre-push", "unchanged", f"{state.hook} runs pre-commit")]
    moved = f", moving the hook there to {state.hook.name}.legacy" if state.foreign else ""
    detail = f"pre-commit install --hook-type pre-push into {state.hook}{moved}"

    def apply() -> bool:
        if _installed(target):
            return False
        # pre-commit caches under the user profile unless PRE_COMMIT_HOME says otherwise.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as cache:
            env = {**os.environ, "PRE_COMMIT_HOME": cache}
            ctx.call("pre-commit", "install", "--hook-type", "pre-push", cwd=ctx.root, env=env)
        if not _installed(target):
            raise InstallError(f"`pre-commit install --hook-type pre-push` left no {state.hook}")
        return True

    return [Step("pre-push", "planned", detail, apply)]


def _installed(target: manual.Target) -> bool:
    try:
        return manual.pre_push(target).installed
    except manual.Unreadable as exc:
        raise InstallError(f"pre-push hook: cannot read: {exc}") from None


# --- the run ----------------------------------------------------------------------------


def _version(value: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise argparse.ArgumentTypeError("expected <major>.<minor>.<patch>")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="init.py", description=__doc__.splitlines()[0])
    parser.add_argument("--version", type=_version, default=VERSION, help="release to install")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print the plan and write nothing")
    mode.add_argument("--confirm", action="store_true", help="perform the plan")
    parser.add_argument("--selected-release", action="store_true", help=argparse.SUPPRESS)
    return parser


def install(argv: list[str], host: Host) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    override = os.environ.get(REPOSITORY_ENV)
    if override:
        print(f"repository: {override}")
    if args.selected_release and args.version != VERSION:
        print(
            f"error: release {VERSION} was selected for --version {args.version}; "
            "the tag does not carry its own version",
            file=sys.stderr,
        )
        return 1
    ctx = Context(
        root=host.root,
        home=host.home,
        platform=host.platform,
        runner=host.runner,
        which=host.which,
        repository=override or REPOSITORY,
        version=args.version,
    )
    try:
        return _run(ctx, args, argv, host.on_write)
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run(
    ctx: Context, args: argparse.Namespace, argv: list[str], on_write: Callable[[str], None]
) -> int:
    if args.version != VERSION:
        if args.confirm:
            print(f"planned hand-off: {ctx.tag} composes the consumer files")
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            tree = Path(tmp) / "release"
            ctx.git(
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--branch",
                ctx.tag,
                ctx.repository,
                str(tree),
            )
            return _hand_off(ctx, argv, tree)
    consumer = _consumer_steps(ctx)
    owner, name, default, linked = _repository(ctx)
    empty = not default
    if empty:
        default = _settings_default(ctx, owner, name)
    project, repo = _project_steps(ctx, owner, name, linked)
    planned = any(step.status == "planned" for step in consumer)
    to = onboarding.Target(
        version=ctx.version,
        repo=repo,
        default=default,
        git=lambda *args, check=True: ctx.git("-C", str(ctx.root), *args, check=check),
        gh=lambda *args: ctx.call("gh", *args, cwd=ctx.root),
        gh_json=lambda *args: _gh_json(ctx, *args),
        empty=empty,
    )
    before, after = onboarding.plan(to, planned)
    steps = [*before, *consumer, *project, *after, *_pre_push_step(ctx, repo)]
    for step in steps:
        print(f"{step.status} {step.label}: {step.detail}")
    conflict = any(step.status == "conflict" for step in steps)
    code = 0 if conflict or args.dry_run else _perform(steps, on_write)
    seeding = any(step.label == "quality" and step.status == "planned" for step in steps)
    if not seeding and not _test_declared(ctx.root):
        print(
            f"quality: {quality.DECLARATION} declares no test -- CI runs no tests until the "
            'change that adds the first tests declares {"test": "<command>"}'
        )
    # Read after the writes, so a Project this run copied and linked is read too.
    for line in _manual(ctx, repo):
        print(line)
    if conflict:
        print("error: resolve the conflicts above; nothing was written", file=sys.stderr)
        return 2
    return code


def _perform(steps: list[Step], on_write: Callable[[str], None]) -> int:
    for step in steps:
        written = step.status == "planned" and step.apply is not None and step.apply()
        print(f"{'written' if written else 'unchanged'} {step.label}: {step.detail}")
        if written:
            on_write(step.label)
    return 0


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    host = Host(
        root=Path.cwd(),
        home=Path.home(),
        platform=sys.platform,
        runner=run,
        which=shutil.which,
        on_write=lambda label: None,
    )
    sys.exit(install(sys.argv[1:], host))


if __name__ == "__main__":
    main()
