#!/usr/bin/env python3
"""Install or update agent-process with a dry-run and one remote-write confirmation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

VERSION = "2.0.0"
OPENSPEC = "@fission-ai/openspec@1.13.0"
REPOSITORY = "https://github.com/ekolvah/agent-process-distribution.git"
RULESET_NAME = "agent-process default branch"
TEMPLATE_PROJECT = 4
TEMPLATE_OWNER = "ekolvah"
MARKER_BEGIN = "# agent-process:begin"
MARKER_END = "# agent-process:end"
MANAGED_HEADER = "# agent-process:managed"
SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_ROOT / "templates"

Runner = Callable[..., subprocess.CompletedProcess[str]]


class InstallConflict(RuntimeError):
    """A consumer-owned target or ambiguous remote state cannot be changed safely."""


def subprocess_runner(
    cmd: list[str], *, cwd: Path | None = None, input: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        input=input,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def run_checked(
    cmd: list[str],
    *,
    runner: Runner = subprocess_runner,
    cwd: Path | None = None,
    input: str | None = None,
) -> str:
    result = runner(cmd, cwd=cwd, input=input)
    if result.stdout is None or result.stderr is None:
        raise RuntimeError(f"`{' '.join(cmd)}`: broken capture (stdout or stderr is None)")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"`{' '.join(cmd)}` failed (rc={result.returncode}): {detail}")
    return result.stdout


def _template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def _write(path: Path, text: str, *, owned: bool = False) -> str:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == text:
            print(f"unchanged: {path}")
            return "unchanged"
        if not owned or not current.startswith(MANAGED_HEADER):
            raise InstallConflict(f"conflict: consumer-owned file {path} is unchanged")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"written: {path}")
    return "written"


def _merge_marked(path: Path, block: str, *, reject_key: str | None = None) -> str:
    block = block.rstrip() + "\n"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block, encoding="utf-8")
        print(f"written: {path}")
        return "written"
    current = path.read_text(encoding="utf-8")
    starts, ends = current.count(MARKER_BEGIN), current.count(MARKER_END)
    if starts or ends:
        if starts != 1 or ends != 1 or current.index(MARKER_BEGIN) > current.index(MARKER_END):
            raise InstallConflict(f"conflict: malformed agent-process markers in {path}")
        before = current[: current.index(MARKER_BEGIN)]
        after = current[current.index(MARKER_END) + len(MARKER_END) :]
        merged = before.rstrip() + ("\n\n" if before.strip() else "") + block + after.lstrip("\r\n")
    else:
        if current.strip() and reject_key is None:
            raise InstallConflict(f"conflict: unmarked consumer-owned file {path}; file unchanged")
        if reject_key and any(line.startswith(f"{reject_key}:") for line in current.splitlines()):
            raise InstallConflict(f"conflict: unmarked {reject_key!r} in {path}; file unchanged")
        merged = current.rstrip() + ("\n\n" if current.strip() else "") + block
    if merged == current:
        print(f"unchanged: {path}")
        return "unchanged"
    path.write_text(merged, encoding="utf-8")
    print(f"written: {path}")
    return "written"


def _merge_settings(path: Path) -> str:
    portable = json.loads(_template("settings.json"))
    if path.exists():
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InstallConflict(f"conflict: {path} is not valid JSON; file unchanged") from exc
        if not isinstance(settings, dict):
            raise InstallConflict(f"conflict: {path} is not a JSON object; file unchanged")
    else:
        settings = {}
    marketplaces = settings.setdefault("extraKnownMarketplaces", {})
    plugins = settings.setdefault("enabledPlugins", {})
    if not isinstance(marketplaces, dict) or not isinstance(plugins, dict):
        raise InstallConflict(f"conflict: plugin settings in {path} are not objects")
    marketplaces["agent-process-marketplace"] = portable["extraKnownMarketplaces"][
        "agent-process-marketplace"
    ]
    plugins["agent-process@agent-process-marketplace"] = True
    rendered = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        print(f"unchanged: {path}")
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    print(f"written: {path}")
    return "written"


def _same_target(link: Path, target: Path) -> bool:
    try:
        return link.exists() and link.resolve(strict=True) == target.resolve(strict=True)
    except OSError:
        return False


def update_codex_skill(home: Path, version: str, runner: Runner, platform: str) -> None:
    checkout = home / ".agent-process" / "distribution"
    target = checkout / "skills" / "agent-process"
    link = home / ".agents" / "skills" / "agent-process"
    if link.exists() or link.is_symlink():
        if not _same_target(link, target):
            raise InstallConflict(
                f"conflict: foreign Codex skill link at {link}; leave it unchanged"
            )
    if checkout.exists():
        dirty = run_checked(["git", "status", "--porcelain"], runner=runner, cwd=checkout)
        if dirty:
            raise InstallConflict(
                f"conflict: dirty Codex checkout at {checkout}; commit or clean it first"
            )
        run_checked(["git", "fetch", "--tags", "origin"], runner=runner, cwd=checkout)
    else:
        checkout.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            ["git", "clone", "--filter=blob:none", "--no-checkout", REPOSITORY, str(checkout)],
            runner=runner,
        )
    run_checked(["git", "checkout", "--detach", f"v{version}"], runner=runner, cwd=checkout)
    if not target.is_dir():
        raise RuntimeError(f"selected tag v{version} has no skill at {target}")
    if _same_target(link, target):
        print(f"unchanged: {link}")
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    if platform == "win32":
        run_checked(["cmd", "/c", "mklink", "/J", str(link), str(target)], runner=runner)
    else:
        run_checked(["ln", "-s", str(target), str(link)], runner=runner)
    print(f"written: {link} -> {target}")


def _repo(root: Path, runner: Runner) -> tuple[str, str]:
    raw = run_checked(
        ["gh", "repo", "view", "--json", "nameWithOwner,defaultBranchRef"], runner=runner, cwd=root
    )
    data = json.loads(raw)
    return str(data["nameWithOwner"]), str(data["defaultBranchRef"]["name"])


def _ruleset_body(default_branch: str) -> dict[str, Any]:
    return json.loads(_template("ruleset.json").replace("__DEFAULT_BRANCH__", default_branch))


def _verify_ruleset(observed: dict[str, Any], default_branch: str) -> None:
    if observed.get("enforcement") != "active" or observed.get("bypass_actors") != []:
        raise RuntimeError("ruleset read-back is not active and no-bypass")
    include = ((observed.get("conditions") or {}).get("ref_name") or {}).get("include") or []
    if f"refs/heads/{default_branch}" not in include:
        raise RuntimeError("ruleset read-back does not target the default branch")
    rules = observed.get("rules", [])
    types = {rule.get("type") for rule in rules if isinstance(rule, dict)}
    barriers = {"pull_request", "deletion", "non_fast_forward"}
    if not barriers <= types:
        missing = ", ".join(sorted(barriers - types))
        raise RuntimeError(f"ruleset read-back is missing barrier rule(s): {missing}")
    required = [r for r in rules if r.get("type") == "required_status_checks"]
    parameters = required[0].get("parameters", {}) if len(required) == 1 else {}
    if parameters.get("strict_required_status_checks_policy") is not True:
        raise RuntimeError("ruleset read-back does not require strict status checks")
    checks = parameters.get("required_status_checks", [])
    if checks != [{"context": "quality / quality", "integration_id": 15368}]:
        raise RuntimeError(
            "ruleset read-back does not require quality / quality from GitHub Actions"
        )


def upsert_ruleset(root: Path, runner: Runner) -> int:
    repo, default_branch = _repo(root, runner)
    endpoint = f"repos/{repo}/rulesets"
    payload = json.loads(
        run_checked(["gh", "api", endpoint, "--paginate", "--slurp"], runner=runner, cwd=root)
    )
    listed = (
        [item for page in payload for item in page]
        if payload and all(isinstance(page, list) for page in payload)
        else payload
    )
    if not isinstance(listed, list) or not all(isinstance(item, dict) for item in listed):
        raise RuntimeError("ruleset list read-back is not a JSON array of objects")
    matches = [item for item in listed if item.get("name") == RULESET_NAME]
    if len(matches) > 1:
        raise InstallConflict(
            f"conflict: several rulesets named {RULESET_NAME!r}; refusing to choose"
        )
    body = _ruleset_body(default_branch)
    if matches:
        rule_id = int(matches[0]["id"])
        method, target = "PUT", f"{endpoint}/{rule_id}"
    else:
        method, target = "POST", endpoint
    created = json.loads(
        run_checked(
            ["gh", "api", target, "--method", method, "--input", "-"],
            runner=runner,
            cwd=root,
            input=json.dumps(body),
        )
    )
    rule_id = int(created["id"])
    observed = json.loads(
        run_checked(["gh", "api", f"{endpoint}/{rule_id}"], runner=runner, cwd=root)
    )
    _verify_ruleset(observed, default_branch)
    print(f"written: ruleset {RULESET_NAME} ({rule_id})")
    return rule_id


def ensure_project(root: Path, runner: Runner) -> int:
    raw = run_checked(
        ["gh", "repo", "view", "--json", "owner,name,projectsV2"], runner=runner, cwd=root
    )
    data = json.loads(raw)
    projects = (
        (data.get("projectsV2") or {}).get("nodes")
        or (data.get("projectsV2") or {}).get("Nodes")
        or []
    )
    if len(projects) > 1:
        names = ", ".join(f"#{p.get('number')} {p.get('title')}" for p in projects)
        raise InstallConflict(
            f"conflict: several Projects are linked ({names}); refusing to choose"
        )
    if projects:
        number = int(projects[0]["number"])
        print(f"unchanged: linked Project #{number} {projects[0].get('title', '')}")
        return number
    copied = json.loads(
        run_checked(
            [
                "gh",
                "project",
                "copy",
                str(TEMPLATE_PROJECT),
                "--source-owner",
                TEMPLATE_OWNER,
                "--target-owner",
                "@me",
                "--format",
                "json",
            ],
            runner=runner,
            cwd=root,
        )
    )
    number = int(copied["number"])
    repo = f"{data['owner']['login']}/{data['name']}"
    run_checked(
        ["gh", "project", "link", str(number), "--owner", "@me", "--repo", repo],
        runner=runner,
        cwd=root,
    )
    print(f"written: copied and linked Project #{number}")
    return number


def _manual_instructions() -> None:
    print("planned: enter the Claude credential yourself: gh secret set CLAUDE_CODE_OAUTH_TOKEN")
    print("planned: enable Codex automatic review for this repository in the Codex GitHub settings")
    print(
        "planned: set Project visibility as intended and enable Auto-add, Item added, Item reopened, Item closed, and Pull request merged workflows in the Project UI"
    )


def _plan(root: Path, home: Path, version: str) -> None:
    for line in (
        f"planned: initialize OpenSpec {OPENSPEC} for claude,codex in {root}",
        "planned: merge openspec pointer rules, one caller, one Dependabot entry, and two Claude settings keys",
        f"planned: update checkout {home / '.agent-process' / 'distribution'} to v{version} and link ~/.agents/skills/agent-process",
        f"planned: upsert ruleset {RULESET_NAME} and copy/link Project {TEMPLATE_OWNER}/{TEMPLATE_PROJECT} when none is linked",
    ):
        print(line)
    _manual_instructions()


def install(
    *,
    root: Path,
    home: Path,
    setup: str,
    test: str,
    version: str = VERSION,
    dry_run: bool,
    confirm_remote: bool,
    runner: Runner = subprocess_runner,
    platform: str = sys.platform,
) -> None:
    if not test.strip():
        raise InstallConflict("a non-empty --test command is required")
    _plan(root, home, version)
    if dry_run:
        return
    if not confirm_remote:
        raise InstallConflict("refusing writes without --confirm-remote; run --dry-run first")
    run_checked(
        ["npx", "-y", OPENSPEC, "init", "--tools", "claude,codex", "--no-animation"],
        runner=runner,
        cwd=root,
    )
    _merge_marked(root / "openspec" / "config.yaml", _template("config.yaml"), reject_key="rules")
    workflow = (
        _template("agent-process.yml")
        .replace("@v2.0.0", f"@v{version}")
        .replace("__SETUP_JSON__", json.dumps(setup))
        .replace("__TEST_JSON__", json.dumps(test))
    )
    _write(
        root / ".github" / "workflows" / "agent-process.yml",
        MANAGED_HEADER + "\n" + workflow,
        owned=True,
    )
    _merge_marked(root / ".github" / "dependabot.yml", _template("dependabot.yml"))
    _merge_settings(root / ".claude" / "settings.json")
    update_codex_skill(home, version, runner, platform)
    upsert_ruleset(root, runner)
    ensure_project(root, runner)
    _manual_instructions()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--setup", default="", help="optional literal consumer setup command")
    parser.add_argument("--test", required=True, help="literal complete consumer quality command")
    parser.add_argument("--version", default=VERSION)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm-remote", action="store_true")
    ns = parser.parse_args(argv)
    try:
        install(
            root=Path.cwd(),
            home=Path.home(),
            setup=ns.setup,
            test=ns.test,
            version=ns.version,
            dry_run=ns.dry_run,
            confirm_remote=ns.confirm_remote,
        )
    except InstallConflict as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
