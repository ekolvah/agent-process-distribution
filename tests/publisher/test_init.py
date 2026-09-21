"""Unit contracts for the stdlib-only v2 installer."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INIT = ROOT / "skills" / "agent-process" / "scripts" / "init.py"


def _module() -> ModuleType:
    assert INIT.is_file(), "the RED test expects the new init.py"
    spec = importlib.util.spec_from_file_location("agent_process_init", INIT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeRunner:
    def __init__(
        self,
        home: Path,
        *,
        rulesets: list[dict[str, Any]] | None = None,
        projects: list[dict[str, Any]] | None = None,
    ) -> None:
        self.home = home
        self.rulesets = list(rulesets or [])
        self.projects = list(projects or [])
        self.calls: list[tuple[list[str], str | None]] = []
        self.dirty = False
        self.origin = "https://github.com/ekolvah/agent-process-distribution.git"

    def __call__(
        self, cmd: list[str], *, cwd: Path | None = None, input: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(cmd), input))
        out = ""
        if cmd[:2] == ["git", "clone"]:
            checkout = Path(cmd[-1])
            (checkout / "skills" / "agent-process").mkdir(parents=True)
            (checkout / "skills" / "agent-process" / "SKILL.md").write_text(
                "fixture\n", encoding="utf-8"
            )
        elif cmd[:3] == ["git", "status", "--porcelain"]:
            out = " M dirty\n" if self.dirty else ""
        elif cmd[:4] == ["git", "remote", "get-url", "origin"]:
            out = f"{self.origin}\n"
        elif cmd[:3] == ["gh", "repo", "view"] and "nameWithOwner,defaultBranchRef" in cmd:
            out = json.dumps({"nameWithOwner": "owner/repo", "defaultBranchRef": {"name": "main"}})
        elif cmd[:3] == ["gh", "repo", "view"] and "owner,name,projectsV2" in cmd:
            out = json.dumps(
                {
                    "owner": {"login": "owner"},
                    "name": "repo",
                    "projectsV2": {"nodes": self.projects},
                }
            )
        elif cmd[:3] == ["gh", "api", "repos/owner/repo/rulesets"] and "--method" not in cmd:
            out = json.dumps(self.rulesets)
        elif cmd[:3] == ["gh", "api", "repos/owner/repo/rulesets"] and "--method" in cmd:
            body = json.loads(input or "{}")
            current = {"id": 41, **body}
            self.rulesets = [current]
            out = json.dumps(current)
        elif cmd[:3] == ["gh", "api", "repos/owner/repo/rulesets/41"]:
            out = json.dumps(self.rulesets[0])
        elif cmd[:3] == ["gh", "project", "copy"]:
            self.projects = [
                {
                    "id": "PVT_9",
                    "number": 9,
                    "title": "Agent process",
                    "resourcePath": "/users/owner/projects/9",
                }
            ]
            out = json.dumps(self.projects[0])
        elif cmd[:3] == ["gh", "project", "link"]:
            out = ""
        elif cmd[:3] == ["cmd", "/c", "mklink"]:
            link, target = Path(cmd[-2]), Path(cmd[-1])
            link.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                assert completed.returncode == 0, completed.stderr
            else:
                link.symlink_to(target, target_is_directory=True)
        elif cmd[:2] == ["ln", "-s"]:
            target, link = Path(cmd[-2]), Path(cmd[-1])
            link.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform == "win32":
                completed = subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                assert completed.returncode == 0, completed.stderr
            else:
                link.symlink_to(target, target_is_directory=True)
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")


def _install(
    tmp_path: Path, *, runner: FakeRunner | None = None, platform: str = "linux", setup: str = ""
) -> tuple[Any, FakeRunner, Path, Path]:
    module = _module()
    repo, home = tmp_path / "repo", tmp_path / "home"
    repo.mkdir(parents=True)
    home.mkdir(parents=True)
    fake = runner or FakeRunner(home)
    module.install(
        root=repo,
        home=home,
        setup=setup,
        test="python -m pytest\npython -m ruff check .",
        version="2.0.0",
        dry_run=False,
        confirm_remote=True,
        runner=fake,
        platform=platform,
    )
    return module, fake, repo, home


def test_fresh_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _, fake, repo, home = _install(tmp_path)
    for relative in (
        "openspec/config.yaml",
        ".github/workflows/agent-process.yml",
        ".github/dependabot.yml",
        ".claude/settings.json",
    ):
        assert (repo / relative).is_file(), relative
    assert (home / ".agents" / "skills" / "agent-process").resolve() == (
        home / ".agent-process" / "distribution" / "skills" / "agent-process"
    ).resolve()
    commands = [call[0] for call in fake.calls]
    assert any(cmd[:3] == ["npx", "-y", "@fission-ai/openspec@1.13.0"] for cmd in commands)
    assert any(cmd[:3] == ["gh", "project", "copy"] for cmd in commands)
    out = capsys.readouterr().out
    assert "gh secret set CLAUDE_CODE_OAUTH_TOKEN" in out
    assert "Codex automatic review" in out
    assert "Project visibility" in out
    assert {p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file()} == {
        "openspec/config.yaml",
        ".github/workflows/agent-process.yml",
        ".github/dependabot.yml",
        ".claude/settings.json",
    }


def test_second_run(tmp_path: Path) -> None:
    _, fake, repo, home = _install(tmp_path)
    before = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    module = _module()
    module.install(
        root=repo,
        home=home,
        setup="",
        test="python -m pytest\npython -m ruff check .",
        version="2.0.0",
        dry_run=False,
        confirm_remote=True,
        runner=fake,
        platform="linux",
    )
    after = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert before == after
    assert len(fake.rulesets) == 1
    assert len(fake.projects) == 1


def test_consumer_owned_file(tmp_path: Path) -> None:
    module = _module()
    repo, home = tmp_path / "repo", tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    target = repo / ".github" / "dependabot.yml"
    target.parent.mkdir(parents=True)
    target.write_text("version: 2\nupdates: []\n", encoding="utf-8")
    with pytest.raises(module.InstallConflict):
        module.install(
            root=repo,
            home=home,
            setup="",
            test="pytest",
            version="2.0.0",
            dry_run=False,
            confirm_remote=True,
            runner=FakeRunner(home),
            platform="linux",
        )
    assert target.read_text(encoding="utf-8") == "version: 2\nupdates: []\n"


def test_dry_run_and_confirmation(tmp_path: Path) -> None:
    module = _module()
    repo, home = tmp_path / "repo", tmp_path / "home"
    repo.mkdir()
    home.mkdir()
    fake = FakeRunner(home)
    module.install(
        root=repo,
        home=home,
        setup="",
        test="pytest",
        version="2.0.0",
        dry_run=True,
        confirm_remote=False,
        runner=fake,
        platform="linux",
    )
    assert not any(repo.iterdir()) and fake.calls == []
    with pytest.raises(module.InstallConflict, match="confirm"):
        module.install(
            root=repo,
            home=home,
            setup="",
            test="pytest",
            version="2.0.0",
            dry_run=False,
            confirm_remote=False,
            runner=fake,
            platform="linux",
        )


def test_literal_commands_are_yaml_safe(tmp_path: Path) -> None:
    setup = "python -m pip install -r requirements.txt\necho 'ready: yes'"
    _, _, repo, _ = _install(tmp_path, setup=setup)
    workflow = yaml.safe_load(
        (repo / ".github" / "workflows" / "agent-process.yml").read_text(encoding="utf-8")
    )
    quality = workflow["jobs"]["quality"]
    assert quality["with"]["setup"] == setup
    assert quality["with"]["test"] == "python -m pytest\npython -m ruff check ."


def test_codex_checkout_refuses_dirty_or_foreign_link(tmp_path: Path) -> None:
    module, fake, _, home = _install(tmp_path)
    fake.dirty = True
    with pytest.raises(module.InstallConflict, match="dirty"):
        module.update_codex_skill(home, "2.0.0", fake, "linux")
    fake.dirty = False
    link = home / ".agents" / "skills" / "agent-process"
    link.unlink() if link.is_symlink() else link.rmdir()
    foreign = home / "foreign"
    foreign.mkdir()
    if sys.platform == "win32":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(foreign)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert completed.returncode == 0, completed.stderr
    else:
        link.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(module.InstallConflict, match="foreign"):
        module.update_codex_skill(home, "2.0.0", fake, "linux")


def test_codex_checkout_refuses_foreign_origin_before_update(tmp_path: Path) -> None:
    module, fake, _, home = _install(tmp_path)
    fake.calls.clear()
    fake.origin = "https://github.com/other/process.git"

    with pytest.raises(module.InstallConflict, match="foreign.*origin"):
        module.update_codex_skill(home, "2.0.0", fake, "linux")

    commands = [cmd for cmd, _ in fake.calls]
    assert not any(cmd[:2] == ["git", "fetch"] for cmd in commands)
    assert not any(cmd[:2] == ["git", "checkout"] for cmd in commands)


def test_windows_skill_link_uses_a_junction(tmp_path: Path) -> None:
    _, fake, _, home = _install(tmp_path, platform="win32")
    assert any(cmd[:4] == ["cmd", "/c", "mklink", "/J"] for cmd, _ in fake.calls)
    assert (home / ".agents" / "skills" / "agent-process").exists()


def test_ruleset_create_update_and_ambiguity(tmp_path: Path) -> None:
    module, fake, repo, _ = _install(tmp_path / "create")
    assert fake.rulesets[0]["enforcement"] == "active"
    module.upsert_ruleset(repo, fake)
    assert any("PUT" in cmd for cmd, _ in fake.calls)
    home = tmp_path / "ambiguous" / "home"
    home.mkdir(parents=True)
    many = FakeRunner(
        home,
        rulesets=[{"id": 1, "name": module.RULESET_NAME}, {"id": 2, "name": module.RULESET_NAME}],
    )
    with pytest.raises(module.InstallConflict, match="several"):
        module.upsert_ruleset(tmp_path, many)


def test_ruleset_blocks_direct_updates(tmp_path: Path) -> None:
    _, fake, _, _ = _install(tmp_path)
    rules = {rule["type"] for rule in fake.rulesets[0]["rules"]}
    assert {"pull_request", "deletion", "non_fast_forward"} <= rules
    assert fake.rulesets[0]["bypass_actors"] == []


def test_ruleset_requires_quality(tmp_path: Path) -> None:
    _, fake, _, _ = _install(tmp_path)
    rule = next(r for r in fake.rulesets[0]["rules"] if r["type"] == "required_status_checks")
    assert rule["parameters"]["strict_required_status_checks_policy"] is True
    assert rule["parameters"]["required_status_checks"] == [
        {"context": "quality / quality", "integration_id": 15368}
    ]


@pytest.mark.parametrize("missing", ["pull_request", "deletion", "non_fast_forward"])
def test_ruleset_readback_rejects_a_missing_barrier(missing: str) -> None:
    module = _module()
    observed = module._ruleset_body("main")
    observed["rules"] = [rule for rule in observed["rules"] if rule["type"] != missing]

    with pytest.raises(RuntimeError, match="barrier"):
        module._verify_ruleset(observed, "main")


def test_ruleset_readback_rejects_non_strict_quality() -> None:
    module = _module()
    observed = module._ruleset_body("main")
    required = next(rule for rule in observed["rules"] if rule["type"] == "required_status_checks")
    required["parameters"]["strict_required_status_checks_policy"] = False

    with pytest.raises(RuntimeError, match="strict"):
        module._verify_ruleset(observed, "main")


def test_project_reuse_and_ambiguity(tmp_path: Path) -> None:
    module = _module()
    home = tmp_path / "home"
    home.mkdir()
    one = FakeRunner(
        home,
        projects=[
            {"id": "P", "number": 3, "title": "Existing", "resourcePath": "/users/owner/projects/3"}
        ],
    )
    module.ensure_project(tmp_path, one)
    assert not any(cmd[:3] == ["gh", "project", "copy"] for cmd, _ in one.calls)
    many = FakeRunner(home, projects=[{"number": 1, "title": "A"}, {"number": 2, "title": "B"}])
    with pytest.raises(module.InstallConflict, match="several"):
        module.ensure_project(tmp_path, many)


def test_none_capture_is_not_an_empty_string(tmp_path: Path) -> None:
    module = _module()

    def broken(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout=None, stderr=None)

    with pytest.raises(RuntimeError, match="capture"):
        module.run_checked(["git", "status"], runner=broken)


def test_utf8_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _module()
    seen: dict[str, Any] = {}

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.subprocess_runner(["gh", "repo", "view"])
    assert seen["encoding"] == "utf-8"
    assert seen["capture_output"] is True


def test_printed_instructions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _install(tmp_path)
    out = capsys.readouterr().out
    assert "gh secret set CLAUDE_CODE_OAUTH_TOKEN" in out
    assert "enable Codex automatic review" in out
    assert "Auto-add" in out and "Pull request merged" in out
