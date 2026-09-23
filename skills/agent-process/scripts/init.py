#!/usr/bin/env python3
"""Install the agent process into the consumer repository at the current directory.

Usage: python init.py --test <command> [--setup <command>] [--version <x.y.z>]
       (--dry-run | --confirm)

The requested release owns its run. With `--version` equal to `VERSION` this file runs
itself; otherwise `--dry-run` clones the requested tag into a temporary directory and runs
that tree's `init.py`, forwarding its output and exit code, and `--confirm` moves the
user-scope checkout to the tag, links the Codex skill, and hands off to the checkout's
`init.py`. The hidden `--selected-release` marks a handed-off child: a tag whose `VERSION`
differs from the requested version exits 1 instead of recursing.

A run first classifies every transition from observed state — `planned`, `unchanged`, or
`conflict` — and prints one line per transition. Any conflict exits 2 before the first
write; `--dry-run` stops after the plan. Confirmed writes run in a fixed order and print
`written` or `unchanged`:

1. checkout  `~/.agent-process/distribution` at `v<version>` (staged clone + `os.replace`)
2. link      `~/.agents/skills/agent-process` -> the checkout's skill (junction on Windows)
3. hand-off  to the requested release, when it is not this one
4. openspec  the pinned `openspec init`, recorded by the `# openspec:` line of the block
5. config    the marker block of `openspec/config.yaml`
6. workflow  the managed `.github/workflows/agent-process.yml`
7. dependabot  the marker block of `.github/dependabot.yml`
8. settings  two keys of `.claude/settings.json`

Nothing is committed or pushed, and no GitHub state is written. `AGENT_PROCESS_REPOSITORY`
overrides the process repository; the plan then prints it as its first line.
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

VERSION = "2.0.0"
REPOSITORY = "https://github.com/ekolvah/agent-process-distribution.git"
REPOSITORY_ENV = "AGENT_PROCESS_REPOSITORY"
GITHUB_REPO = "ekolvah/agent-process-distribution"
OPENSPEC = "1.13.0"
# `openspec init --tools claude,codex` of the pin in a fresh repository (observed 2026-09-23).
OPENSPEC_OUTPUT = (
    ".agents/skills/.openspec-target",
    *(
        f"{tool}/skills/openspec-{name}/SKILL.md"
        for tool in (".agents", ".claude")
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
DEPENDABOT = ".github/dependabot.yml"
SETTINGS = ".claude/settings.json"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class Conflict(Exception):
    """A target the installer does not own."""


class InstallError(Exception):
    """A tool or command failed; exit 1."""


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


def render_workflow(version: str, setup: str, test: str) -> str:
    """The managed caller; each command is a JSON string, a valid YAML scalar for any literal."""
    return _template(
        "agent-process.yml", version=version, setup=json.dumps(setup), test=json.dumps(test)
    )


def render_config_block(test: str) -> str:
    quality = f"The repository's complete quality command is: {test}"
    return _template("config.yaml", openspec=OPENSPEC, quality=json.dumps(quality))


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


def _same_path(a: str | Path, b: str | Path) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def _is_link(path: Path) -> bool:
    return os.path.islink(path) or os.path.isjunction(path)


# --- transitions ------------------------------------------------------------------------


@dataclass
class Step:
    label: str
    status: str
    detail: str
    apply: Callable[[], bool] | None = None


@dataclass
class Context:
    root: Path
    home: Path
    platform: str
    runner: Runner
    which: Callable[[str], str | None]
    repository: str
    version: str
    setup: str
    test: str

    @property
    def tag(self) -> str:
        return f"v{self.version}"

    @property
    def checkout(self) -> Path:
        return self.home / ".agent-process" / "distribution"

    @property
    def link(self) -> Path:
        return self.home / ".agents" / "skills" / "agent-process"

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
            output = next((s for s in streams if s), "") if streams else "output not captured"
            raise InstallError(f"`{name} {' '.join(args)}` exited {done.returncode}: {output}")
        return done

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        # No optional locks: a status read never refreshes the index of a checkout it inspects.
        env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        return self.call("git", *args, env=env, check=check)


def _checkout(ctx: Context) -> Step:
    path, tag = ctx.checkout, ctx.tag
    if not os.path.lexists(path):
        if reason := _parent_conflict(path):
            return Step("checkout", "conflict", f"{path} {reason}")

        def clone() -> bool:
            path.parent.mkdir(parents=True, exist_ok=True)
            staging = tempfile.mkdtemp(dir=path.parent)
            try:
                ctx.git("clone", "--quiet", "--branch", tag, ctx.repository, staging)
                os.replace(staging, path)
            except BaseException:
                shutil.rmtree(staging, ignore_errors=True)
                raise
            return True

        return Step("checkout", "planned", f"{path} absent -> {tag}", clone)

    def conflict(reason: str) -> Step:
        return Step("checkout", "conflict", f"{path} {reason}")

    here = ["-C", str(path)]
    top = ctx.git(*here, "rev-parse", "--show-toplevel", check=False)
    if _is_link(path) or top.returncode != 0 or not _same_path(top.stdout.strip(), path):
        return conflict("is not a Git checkout")
    origin = ctx.git(*here, "remote", "get-url", "origin", check=False)
    if origin.returncode != 0 or origin.stdout.strip() != ctx.repository:
        return conflict(f"has origin {origin.stdout.strip() or 'none'}, not {ctx.repository}")
    if ctx.git(*here, "status", "--porcelain").stdout.strip():
        return conflict("has local changes")
    head = ctx.git(*here, "rev-parse", "HEAD").stdout.strip()
    wanted = ctx.git(
        *here, "rev-parse", "--verify", "-q", f"refs/tags/{tag}^{{commit}}", check=False
    )
    if wanted.returncode == 0 and wanted.stdout.strip() == head:
        return Step("checkout", "unchanged", f"{path} at {tag}")
    described = ctx.git(*here, "describe", "--tags", "--exact-match", "HEAD", check=False)
    current = described.stdout.strip() if described.returncode == 0 else head[:12]

    def move() -> bool:
        ctx.git(*here, "fetch", "--quiet", "--tags", "origin")
        ctx.git(*here, "checkout", "--quiet", "--detach", tag)
        return True

    return Step("checkout", "planned", f"{path} {current} -> {tag}", move)


def _link(ctx: Context) -> Step:
    link, target = ctx.link, ctx.checkout / "skills" / "agent-process"
    if not os.path.lexists(link):
        if reason := _parent_conflict(link):
            return Step("link", "conflict", f"{link} {reason}")

        def create() -> bool:
            link.parent.mkdir(parents=True, exist_ok=True)
            if ctx.platform == "win32":
                ctx.call("cmd", "/c", "mklink", "/J", str(link), str(target))
            else:
                ctx.call("ln", "-s", str(target), str(link))
            return True

        return Step("link", "planned", f"{link} -> {target}", create)
    if _is_link(link) and _same_path(link, target):
        return Step("link", "unchanged", f"{link} -> {target}")
    return Step("link", "conflict", f"{link} is not the installer's link to {target}")


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


def _recorded_pin(text: str | None) -> str | None:
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
        if line.startswith(PIN):
            return line[len(PIN) :].strip()
    return None


def _with_pin(text: str) -> str:
    lines = text.split("\n")
    span = _span(lines)
    if span is None:
        return "\n".join(_replace_block(lines, [BEGIN, PIN + OPENSPEC, END]))
    inner = [line for line in lines[span[0] + 1 : span[1]] if not line.startswith(PIN)]
    return "\n".join([*lines[: span[0] + 1], PIN + OPENSPEC, *inner, *lines[span[1] :]])


def _openspec(ctx: Context) -> Step:
    config = ctx.root / CONFIG
    detail = f"openspec init --tools claude,codex (@fission-ai/openspec@{OPENSPEC})"

    def current() -> bool:
        paths = all((ctx.root / rel).exists() for rel in OPENSPEC_OUTPUT)
        try:
            text = _read(config)
        except Conflict:  # reported by the config step, which runs before any write
            return False
        return paths and _recorded_pin(text) == OPENSPEC

    def apply() -> bool:
        if current():
            return False
        ctx.call(
            "npx",
            "-y",
            f"@fission-ai/openspec@{OPENSPEC}",
            "init",
            "--tools",
            "claude,codex",
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
    block = render_config_block(ctx.test).splitlines()
    return text, "\n".join(_replace_block(lines, block))


def _workflow_text(ctx: Context) -> tuple[str | None, str]:
    text = _read(ctx.root / WORKFLOW)
    if text is not None and text.split("\n", 1)[0].strip() != MANAGED:
        raise Conflict(f"exists without its first line `{MANAGED}`")
    return text, render_workflow(ctx.version, ctx.setup, ctx.test)


def _dependabot_text(ctx: Context) -> tuple[str | None, str]:
    text = _read(ctx.root / DEPENDABOT)
    rendered = _template("dependabot.yml")
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
    if market == entry and plugins.get(PLUGIN) is True:
        return text, text or ""
    # Re-serialising is lossless only from the form written here; any other form (spacing,
    # key order, escapes, repeated keys) is the person's to edit.
    if text is not None and text != json.dumps(data, indent=2, ensure_ascii=False) + "\n":
        raise Conflict(
            f'is not in the form init writes; add `"extraKnownMarketplaces": {{"{MARKETPLACE}":'
            f' {json.dumps(entry)}}}` and `"enabledPlugins": {{"{PLUGIN}": true}}` by hand'
        )
    updated = dict(data)
    updated["extraKnownMarketplaces"] = {**marketplaces, MARKETPLACE: entry}
    updated["enabledPlugins"] = {**plugins, PLUGIN: True}
    return text, json.dumps(updated, indent=2, ensure_ascii=False) + "\n"


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


def _consumer_steps(ctx: Context) -> list[Step]:
    return [
        _openspec(ctx),
        _file_step(ctx, "config", CONFIG, _config_text),
        _file_step(ctx, "workflow", WORKFLOW, _workflow_text),
        _file_step(ctx, "dependabot", DEPENDABOT, _dependabot_text),
        _file_step(ctx, "settings", SETTINGS, _settings_text),
    ]


# --- the run ----------------------------------------------------------------------------


def _command(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be empty")
    return value


def _version(value: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise argparse.ArgumentTypeError("expected <major>.<minor>.<patch>")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="init.py", description=__doc__.splitlines()[0])
    parser.add_argument("--test", required=True, type=_command, help="complete quality command")
    parser.add_argument("--setup", default="", help="dependency setup command (optional)")
    parser.add_argument("--version", type=_version, default=VERSION, help="release to install")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print the plan and write nothing")
    mode.add_argument("--confirm", action="store_true", help="perform the plan")
    parser.add_argument("--selected-release", action="store_true", help=argparse.SUPPRESS)
    return parser


def install(
    argv: list[str],
    *,
    root: Path,
    home: Path,
    platform: str,
    runner: Runner,
    which: Callable[[str], str | None],
    on_write: Callable[[str], None],
) -> int:
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
        root=root,
        home=home,
        platform=platform,
        runner=runner,
        which=which,
        repository=override or REPOSITORY,
        version=args.version,
        setup=args.setup,
        test=args.test,
    )
    try:
        if args.version != VERSION and args.dry_run:
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
        steps = [_checkout(ctx), _link(ctx)]
        if args.version != VERSION:
            steps.append(Step("hand-off", "planned", f"{ctx.tag} composes the consumer files"))
        else:
            steps.extend(_consumer_steps(ctx))
        for step in steps:
            print(f"{step.status} {step.label}: {step.detail}")
        if any(step.status == "conflict" for step in steps):
            print("error: resolve the conflicts above; nothing was written", file=sys.stderr)
            return 2
        if args.dry_run:
            return 0
        for step in steps:
            if step.label == "hand-off":
                return _hand_off(ctx, argv, ctx.checkout)
            written = step.status == "planned" and step.apply is not None and step.apply()
            print(f"{'written' if written else 'unchanged'} {step.label}: {step.detail}")
            if written:
                on_write(step.label)
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    sys.exit(
        install(
            sys.argv[1:],
            root=Path.cwd(),
            home=Path.home(),
            platform=sys.platform,
            runner=run,
            which=shutil.which,
            on_write=lambda label: None,
        )
    )


if __name__ == "__main__":
    main()
