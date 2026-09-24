"""Guards around required status checks for the `main` branch.

Actual enforcement lives in GitHub configuration **outside the repository**: the `pr-link`
workflow once existed and was red in the UI, yet blocked nothing because it was absent from
`required_status_checks.contexts`. The defect class is presence ≠ correctness.

There are two independent layers here:

* `TestDriftDetection` / `TestProtectionFetch`—the pure half of `.agent-process/scripts/check_branch_protection.py`
  (compare “declared ↔ actual” and distinguish “drift” from “tool failure,” §IV). A CI network run is
  unavailable: `GITHUB_TOKEN` lacks `administration` scope, and classic branch protection is invisible
  through the ruleset endpoint—coverage-gaps-quality-gates.md entry AD.
* `TestDeclarationMatchesWorkflows`—the offline half: script declaration is compared with real workflows.
  It compares the **effective check-run name** (`name:` of the job, otherwise its key): renaming a job would
  otherwise leave a required context permanently “Expected,” and `enforce_admins: true` would lock merging,
  including the fixing PR.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from scripts.check_branch_protection import (
    NOT_REQUIRED,
    REQUIRED_CONTEXTS,
    contexts_from_protection,
    declaration_problems,
    fetch_protection,
    load_workflows,
    protection_drift,
    unverified_offline_contexts,
)
from scripts.install_branch_protection import (
    BranchProtectionError,
    install_branch_protection,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_WORKFLOWS = _REPO_ROOT / ".github" / "workflows"
_HOOK = _REPO_ROOT / ".agent-process" / ".githooks" / "pre-push"


class _MemoryProtectionClient:
    """Stateful double: tests assert policy effects, not subprocess spelling."""

    def __init__(
        self,
        protection: Mapping[str, Any] | None,
        *,
        default_branch: Any = "main",
        fail_on: str | None = None,
    ) -> None:
        self.repository: Mapping[str, Any] = {"default_branch": default_branch}
        self.protection: Any = deepcopy(protection)
        self.fail_on = fail_on
        self.writes: list[tuple[Any, ...]] = []
        self.protection_reads = 0

    def _fail(self, operation: str) -> None:
        if self.fail_on == operation:
            raise BranchProtectionError(f"{operation} unavailable")

    def get_repository(self) -> Mapping[str, Any]:
        self._fail("repository")
        return self.repository

    def get_protection(self, branch: str) -> Mapping[str, Any] | None:
        self._fail("protection")
        self.protection_reads += 1
        return deepcopy(self.protection)

    def add_required_contexts(self, branch: str, contexts: Sequence[str]) -> None:
        self._fail("add_contexts")
        values = tuple(contexts)
        self.writes.append(("add_contexts", branch, values))
        checks = self.protection["required_status_checks"]["checks"]
        checks.extend({"context": context, "app_id": 9001} for context in values)

    def enable_required_status_checks(self, branch: str, contexts: Sequence[str]) -> None:
        self._fail("enable_status_checks")
        values = tuple(contexts)
        self.writes.append(("enable_status_checks", branch, values))
        self.protection["required_status_checks"] = {
            "strict": True,
            "checks": [{"context": context, "app_id": 9001} for context in values],
        }

    def set_strict_status_checks(self, branch: str) -> None:
        self._fail("set_strict")
        self.writes.append(("set_strict", branch))
        self.protection["required_status_checks"]["strict"] = True

    def set_admin_enforcement(self, branch: str) -> None:
        self._fail("set_admins")
        self.writes.append(("set_admins", branch))
        self.protection["enforce_admins"] = {"enabled": True}

    def create_protection(self, branch: str, payload: Mapping[str, Any]) -> None:
        self._fail("create")
        self.writes.append(("create", branch, deepcopy(payload)))
        self.protection = deepcopy(payload)


def _protected_policy(*, strict: bool = True, admins: bool = True) -> dict[str, Any]:
    return {
        "required_status_checks": {
            "strict": strict,
            "checks": [
                {"context": "consumer / test", "app_id": 71},
            ],
        },
        "enforce_admins": {"enabled": admins},
        "required_pull_request_reviews": {
            "required_approving_review_count": 2,
            "bypass_pull_request_allowances": {"apps": [{"slug": "release-bot"}]},
        },
        "restrictions": {"teams": [{"slug": "maintainers"}]},
        "required_linear_history": {"enabled": True},
        "allow_force_pushes": {"enabled": True},
        "allow_deletions": {"enabled": False},
        "required_conversation_resolution": {"enabled": True},
        "lock_branch": {"enabled": False},
        "allow_fork_syncing": {"enabled": True},
    }


class TestProtectionInstallation:
    def test_protected_branch_adds_only_missing_contexts_and_preserves_policy(self) -> None:
        before = _protected_policy()
        client = _MemoryProtectionClient(before)

        report = install_branch_protection(client, confirm_write=True, workflows_dir=_WORKFLOWS)

        assert client.writes == [("add_contexts", "main", REQUIRED_CONTEXTS)]
        assert report.changed is True
        assert client.protection_reads == 2
        assert (
            client.protection["required_pull_request_reviews"]
            == before["required_pull_request_reviews"]
        )
        assert client.protection["restrictions"] == before["restrictions"]
        for field in (
            "required_linear_history",
            "allow_force_pushes",
            "allow_deletions",
            "required_conversation_resolution",
            "lock_branch",
            "allow_fork_syncing",
        ):
            assert client.protection[field] == before[field]
        original_pairs = {
            (check["context"], check.get("app_id"))
            for check in before["required_status_checks"]["checks"]
        }
        after_pairs = {
            (check["context"], check.get("app_id"))
            for check in client.protection["required_status_checks"]["checks"]
        }
        assert original_pairs <= after_pairs

    def test_protected_branch_enables_strict_and_admin_through_narrow_subresources(self) -> None:
        policy = _protected_policy(strict=False, admins=False)
        policy["required_status_checks"]["checks"].extend(
            {"context": context, "app_id": 15368} for context in REQUIRED_CONTEXTS
        )
        client = _MemoryProtectionClient(policy)

        install_branch_protection(client, confirm_write=True, workflows_dir=_WORKFLOWS)

        assert client.writes == [("set_strict", "main"), ("set_admins", "main")]

    def test_unprotected_default_branch_creates_the_documented_baseline(self) -> None:
        client = _MemoryProtectionClient(None, default_branch="stable")

        install_branch_protection(client, confirm_write=True, workflows_dir=_WORKFLOWS)

        assert client.writes == [
            (
                "create",
                "stable",
                {
                    "required_status_checks": {
                        "strict": True,
                        "checks": [{"context": context} for context in REQUIRED_CONTEXTS],
                    },
                    "enforce_admins": True,
                    "required_pull_request_reviews": None,
                    "restrictions": None,
                    "allow_force_pushes": False,
                    "allow_deletions": False,
                },
            )
        ]
        assert client.protection_reads == 2

    def test_dry_run_and_failed_preflight_make_no_writes(self, tmp_path: Path) -> None:
        dry_run = _MemoryProtectionClient(_protected_policy(strict=False, admins=False))
        report = install_branch_protection(dry_run, workflows_dir=_WORKFLOWS)
        assert report.changed is False
        assert report.actions
        assert dry_run.writes == []

        malformed_repository = _MemoryProtectionClient(None, default_branch=42)
        with pytest.raises(BranchProtectionError, match="default branch"):
            install_branch_protection(
                malformed_repository, confirm_write=True, workflows_dir=_WORKFLOWS
            )
        assert malformed_repository.writes == []

        malformed_protection = _MemoryProtectionClient(None)
        malformed_protection.protection = []
        with pytest.raises(BranchProtectionError, match="protection"):
            install_branch_protection(
                malformed_protection, confirm_write=True, workflows_dir=_WORKFLOWS
            )
        assert malformed_protection.writes == []

        unavailable_auth = _MemoryProtectionClient(None, fail_on="repository")
        with pytest.raises(BranchProtectionError, match="repository unavailable"):
            install_branch_protection(
                unavailable_auth, confirm_write=True, workflows_dir=_WORKFLOWS
            )
        assert unavailable_auth.writes == []

        invalid_workflows = tmp_path / "workflows"
        invalid_workflows.mkdir()
        (invalid_workflows / "ci.yml").write_text(
            "on: [pull_request]\njobs:\n  unrelated: {}\n", encoding="utf-8"
        )
        invalid_declaration = _MemoryProtectionClient(None)
        with pytest.raises(BranchProtectionError, match="workflow declaration"):
            install_branch_protection(
                invalid_declaration, confirm_write=True, workflows_dir=invalid_workflows
            )
        assert invalid_declaration.writes == []

    def test_partial_failure_is_visible_and_rerun_converges(self) -> None:
        client = _MemoryProtectionClient(
            _protected_policy(strict=False, admins=False), fail_on="set_admins"
        )

        with pytest.raises(BranchProtectionError, match="partial.*add.*strict.*rerun"):
            install_branch_protection(client, confirm_write=True, workflows_dir=_WORKFLOWS)

        assert [write[0] for write in client.writes] == ["add_contexts", "set_strict"]
        client.fail_on = None
        report = install_branch_protection(client, confirm_write=True, workflows_dir=_WORKFLOWS)
        assert client.writes[-1] == ("set_admins", "main")
        assert report.changed is True

    def test_configured_rerun_is_a_noop(self) -> None:
        policy = _protected_policy()
        policy["required_status_checks"]["checks"].extend(
            {"context": context, "app_id": 15368} for context in REQUIRED_CONTEXTS
        )
        client = _MemoryProtectionClient(policy)

        report = install_branch_protection(client, confirm_write=True, workflows_dir=_WORKFLOWS)

        assert report.actions == ()
        assert report.changed is False
        assert client.writes == []
        assert client.protection_reads == 1


class TestDriftDetection:
    def test_controller_gate_is_not_a_required_context(self) -> None:
        assert REQUIRED_CONTEXTS == ("agent-review / agent-review",)

    """Чистое сравнение объявленного состава контекстов с фактическим."""

    def test_missing_required_context_is_drift(self) -> None:
        """The exact defect: `pr-link` is declared but absent from GitHub."""
        missing, unexpected = protection_drift(("quality",), ("quality", "pr-link"))
        assert missing == ["pr-link"]
        assert unexpected == []

    def test_extra_consumer_context_is_preserved_and_not_drift(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The process owns a minimum; a consumer may require additional checks."""
        missing, preserved = protection_drift(("quality", "review"), ("quality",))
        assert missing == []
        assert preserved == ["review"]
        import scripts.check_branch_protection as guard

        monkeypatch.setattr(guard, "fetch_default_branch", lambda: "main")
        monkeypatch.setattr(
            guard,
            "fetch_protection",
            lambda _branch: {
                "required_status_checks": {
                    "checks": [
                        *({"context": context} for context in REQUIRED_CONTEXTS),
                        {"context": "consumer / test"},
                    ]
                }
            },
        )
        guard.main([])
        assert "preserved consumer-required checks: consumer / test" in capsys.readouterr().out

    def test_missing_context_output_points_to_installer_without_inline_patch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import scripts.check_branch_protection as guard

        monkeypatch.setattr(guard, "fetch_default_branch", lambda: "main")
        monkeypatch.setattr(
            guard,
            "fetch_protection",
            lambda _branch: {"required_status_checks": {"checks": []}},
        )
        with pytest.raises(SystemExit) as exc:
            guard.main([])
        assert exc.value.code == 1
        output = capsys.readouterr().err
        assert "install_branch_protection.py" in output
        assert "--method PATCH" not in output

    def test_exact_match_is_clean(self) -> None:
        """A match yields an empty verdict in both directions."""
        assert protection_drift(("quality", "pr-link"), ("quality", "pr-link")) == (
            [],
            [],
        )

    def test_order_does_not_matter(self) -> None:
        """GitHub does not guarantee `checks` order; comparison uses a set."""
        assert protection_drift(("pr-link", "quality"), ("quality", "pr-link")) == (
            [],
            [],
        )


class TestAllowDrift:
    """A gate that regularly demands bypassing teaches bypassing.

    The maintainer removes `agent-review` from required to merge a PR whose review
    is red by construction; the drift detector then blocks every push to unrelated
    feature branches, and the only escape is `--no-verify`, which swallows
    `ci_check` too. `--allow-drift "<reason>"` makes the intentional temporary state
    expressible instead."""

    @staticmethod
    def _patch_actual(monkeypatch: pytest.MonkeyPatch, contexts: list[str]) -> None:
        import scripts.check_branch_protection as guard

        monkeypatch.setattr(guard, "fetch_default_branch", lambda: "main")
        monkeypatch.setattr(
            guard,
            "fetch_protection",
            lambda _branch: {
                "required_status_checks": {"checks": [{"context": c} for c in contexts]}
            },
        )

    def test_drift_without_the_flag_still_exits_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.check_branch_protection as guard

        self._patch_actual(monkeypatch, ["quality", "pr-link"])
        with pytest.raises(SystemExit) as exc:
            guard.main([])
        assert exc.value.code == 1

    def test_allow_drift_exits_zero_and_prints_the_reason(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import scripts.check_branch_protection as guard

        self._patch_actual(monkeypatch, ["quality", "pr-link"])
        guard.main(["--allow-drift", f"agent-review снят для мержа #{458}"])
        out = capsys.readouterr().out
        assert f"#{458}" in out, "the stated reason must reach the push output"

    def test_allow_drift_requires_a_reason(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.check_branch_protection as guard

        self._patch_actual(monkeypatch, ["quality", "pr-link"])
        with pytest.raises(SystemExit) as exc:
            guard.main(["--allow-drift"])
        assert exc.value.code == 2

    def test_no_drift_with_the_flag_is_still_clean(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import scripts.check_branch_protection as guard

        self._patch_actual(monkeypatch, list(REQUIRED_CONTEXTS))
        guard.main(["--allow-drift", "не нужен"])


class TestProtectionFetch:
    """Network layer: tool failure (exit 2) is not masked as a verdict (exit 0/1)."""

    @staticmethod
    def _fake_run(
        monkeypatch: pytest.MonkeyPatch,
        *,
        stdout: str | None,
        stderr: str | None,
        rc: int,
    ) -> None:
        """Replace `subprocess.run` with a fixed `gh api` result."""

        def _run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=["gh"], returncode=rc, stdout=stdout, stderr=stderr
            )

        monkeypatch.setattr(subprocess, "run", _run)

    def test_gh_failure_exits_2_not_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Nonzero `gh` rc is infrastructure failure, not “no drift” or “drift.”"""
        self._fake_run(monkeypatch, stdout="", stderr="HTTP 403", rc=1)
        with pytest.raises(SystemExit) as exc:
            fetch_protection()
        assert exc.value.code == 2

    def test_none_stdout_exits_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Broken output capture is also infrastructure failure, not an empty response."""
        self._fake_run(monkeypatch, stdout=None, stderr=None, rc=0)
        with pytest.raises(SystemExit) as exc:
            fetch_protection()
        assert exc.value.code == 2

    def test_malformed_json_exits_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successful rc but unparseable body is also tool failure."""
        self._fake_run(monkeypatch, stdout="<html>proxy</html>", stderr="", rc=0)
        with pytest.raises(SystemExit) as exc:
            fetch_protection()
        assert exc.value.code == 2

    def test_gh_timeout_exits_2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A hung `gh` must not leave pre-push hanging without output."""

        def _hang(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd="gh", timeout=30)

        monkeypatch.setattr(subprocess, "run", _hang)
        with pytest.raises(SystemExit) as exc:
            fetch_protection()
        assert exc.value.code == 2

    def test_absent_required_status_checks_is_drift_not_infra(self) -> None:
        """Removed protection is the most likely real scenario: drift, not failure."""
        assert contexts_from_protection({}) == ()
        assert contexts_from_protection({"required_status_checks": {}}) == ()

    def test_unprotected_branch_is_drift_not_infrastructure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._fake_run(
            monkeypatch,
            stdout='{"message":"Branch not protected"}',
            stderr="gh: Branch not protected (HTTP 404)",
            rc=1,
        )
        assert fetch_protection() == {}

    def test_null_required_status_checks_is_drift_not_crash(self) -> None:
        """Explicit JSON `null` differs from a missing key; a traceback would yield code 1."""
        assert contexts_from_protection({"required_status_checks": None}) == ()
        assert contexts_from_protection({"required_status_checks": {"checks": None}}) == ()

    def test_contexts_are_read_from_the_checks_field(self) -> None:
        """Read the non-deprecated `checks[*].context` form, the same one written."""
        payload = {
            "required_status_checks": {
                "strict": True,
                "checks": [
                    {"context": "quality", "app_id": 15368},
                    {"context": "pr-link"},
                ],
            }
        }
        assert contexts_from_protection(payload) == ("quality", "pr-link")

    def test_actual_contexts_are_printed_on_success(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Actual list is always printed—the reproducible way to see it."""
        import scripts.check_branch_protection as guard

        payload = {
            "required_status_checks": {"checks": [{"context": c} for c in REQUIRED_CONTEXTS]}
        }
        monkeypatch.setattr(guard, "fetch_default_branch", lambda: "main")
        monkeypatch.setattr(guard, "fetch_protection", lambda _branch: payload)
        guard.main([])
        printed = capsys.readouterr().out
        for context in REQUIRED_CONTEXTS:
            assert context in printed

    def test_main_audits_the_repository_default_branch(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import scripts.check_branch_protection as guard

        seen: list[str] = []
        monkeypatch.setattr(guard, "fetch_default_branch", lambda: "stable", raising=False)
        monkeypatch.setattr(
            guard,
            "fetch_protection",
            lambda *branches: (
                seen.extend(branches)
                or {
                    "required_status_checks": {
                        "checks": [{"context": context} for context in REQUIRED_CONTEXTS]
                    }
                }
            ),
        )

        guard.main([])

        assert seen == ["stable"]
        assert "`stable`" in capsys.readouterr().out


class TestDeclarationMatchesWorkflows:
    """Offline half: the script declaration does not diverge from repository workflows."""

    def test_every_declared_context_is_a_real_job(self) -> None:
        """Real workflows + real declaration—no divergence.

        Non-emptiness of the declaration is checked separately: an empty list would
        vacuously satisfy everything else and silently guarantee nothing (§IV).
        """
        assert REQUIRED_CONTEXTS, "пустое объявление молча не гарантирует ничего"
        assert (
            declaration_problems(load_workflows(_WORKFLOWS), REQUIRED_CONTEXTS, NOT_REQUIRED) == []
        )

    def test_reusable_context_composition_is_visible_offline(self) -> None:
        notices = unverified_offline_contexts(load_workflows(_WORKFLOWS), REQUIRED_CONTEXTS)
        assert len(notices) == len(REQUIRED_CONTEXTS)
        assert all("unverified offline" in notice for notice in notices)

    def test_every_pull_request_job_is_declared_or_excluded(self) -> None:
        """A new PR job must be either required or excluded with a reason."""
        workflows = {
            "new.yml": {"on": {"pull_request": None}, "jobs": {"fresh-gate": {}}},
        }
        problems = declaration_problems(workflows, ("fresh-gate",), {})
        assert problems == []

        problems = declaration_problems(workflows, (), {})
        assert len(problems) == 1
        assert "fresh-gate" in problems[0]

    def test_excluded_job_needs_a_reason(self) -> None:
        """An exclusion without a reason is a forgotten decision, not an accepted one."""
        workflows = {"new.yml": {"on": {"pull_request": None}, "jobs": {"advisory": {}}}}
        assert declaration_problems(workflows, (), {"advisory": "не блокирует fork-PR"}) == []
        assert declaration_problems(workflows, (), {"advisory": ""}) != []

    def test_declared_context_without_a_job_is_a_problem(self) -> None:
        """A declared context without a job is perpetual “Expected”; merge is locked forever."""
        workflows = {"new.yml": {"on": {"pull_request": None}, "jobs": {"gate": {}}}}
        problems = declaration_problems(workflows, ("gate", "ghost"), {})
        assert len(problems) == 1
        assert "ghost" in problems[0]

    def test_job_name_override_defines_the_context(self) -> None:
        """The context is a job’s `name:` when set, not its job key."""
        workflows = {
            "new.yml": {
                "on": {"pull_request": None},
                "jobs": {"gate": {"name": "Gate (strict)"}},
            }
        }
        assert declaration_problems(workflows, ("Gate (strict)",), {}) == []
        assert declaration_problems(workflows, ("gate",), {}) != []

    def test_matrix_job_cannot_be_declared_as_bare_context(self) -> None:
        """A matrix expands context to `job (value)`—the bare name never reports."""
        workflows = {
            "new.yml": {
                "on": {"pull_request": None},
                "jobs": {"gate": {"strategy": {"matrix": {"python": ["3.12", "3.13"]}}}},
            }
        }
        problems = declaration_problems(workflows, ("gate",), {})
        assert len(problems) == 1
        assert "matrix" in problems[0].lower()

    def test_yaml_boolean_on_key_is_understood(self) -> None:
        """YAML 1.1 reads bare `on:` as `True`—the job must not be lost because of it."""
        workflows = {"new.yml": {True: {"pull_request": None}, "jobs": {"gate": {}}}}
        assert declaration_problems(workflows, (), {}) != []

    def test_trigger_filter_on_declared_context_is_a_problem(self) -> None:
        """`paths`/`branches` on a trigger means the context will not report on every PR."""
        for filter_key in ("paths", "paths-ignore", "branches", "branches-ignore"):
            workflows = {
                "new.yml": {
                    "on": {"pull_request": {filter_key: ["src/**"]}},
                    "jobs": {"gate": {}},
                }
            }
            problems = declaration_problems(workflows, ("gate",), {})
            assert len(problems) == 1, filter_key
            assert filter_key in problems[0]

    def test_unfiltered_trigger_is_clean(self) -> None:
        """`types:` is not a filter—it narrows events, not the PR set."""
        workflows = {
            "new.yml": {
                "on": {"pull_request": {"types": ["opened", "edited"]}},
                "jobs": {"gate": {}},
            }
        }
        assert declaration_problems(workflows, ("gate",), {}) == []

    def test_stale_exclusion_is_a_problem(self) -> None:
        """An exclusion outliving its removed job silently means nothing."""
        workflows = {"new.yml": {"on": {"pull_request": None}, "jobs": {"gate": {}}}}
        problems = declaration_problems(workflows, ("gate",), {"ghost": "причина есть"})
        assert len(problems) == 1
        assert "ghost" in problems[0]

    def test_context_in_both_lists_is_a_problem(self) -> None:
        """A context both required and excluded is contradiction, not clarification."""
        workflows = {"new.yml": {"on": {"pull_request": None}, "jobs": {"gate": {}}}}
        problems = declaration_problems(workflows, ("gate",), {"gate": "причина есть"})
        assert len(problems) == 1
        assert "gate" in problems[0]

    def test_duplicate_effective_job_name_is_a_problem(self) -> None:
        """One check-run name for two jobs is ambiguity, not a detail."""
        workflows = {
            "a.yml": {"on": {"pull_request": None}, "jobs": {"gate": {}}},
            "b.yml": {
                "on": {"pull_request": None},
                "jobs": {"other": {"name": "gate"}},
            },
        }
        problems = declaration_problems(workflows, ("gate",), {})
        assert any("более чем одному" in p for p in problems)

    def test_yaml_extension_workflow_is_loaded(self, tmp_path: Path) -> None:
        """GitHub accepts `.yaml`; a guard blind to it would be vacuously green."""
        (tmp_path / "a.yml").write_text(
            "on:\n  pull_request:\njobs:\n  one: {}\n", encoding="utf-8"
        )
        (tmp_path / "b.yaml").write_text(
            "on:\n  pull_request:\njobs:\n  two: {}\n", encoding="utf-8"
        )
        loaded = load_workflows(tmp_path)
        assert set(loaded) == {"a.yml", "b.yaml"}
        problems = declaration_problems(loaded, (), {})
        assert len(problems) == 2

    def test_empty_workflow_file_does_not_crash(self, tmp_path: Path) -> None:
        """`safe_load` returns an empty file as `None`—the wrapper must survive that."""
        (tmp_path / "empty.yml").write_text("", encoding="utf-8")
        assert load_workflows(tmp_path) == {"empty.yml": {}}
        assert declaration_problems(load_workflows(tmp_path), (), {}) == []

    def test_non_pull_request_workflow_is_ignored(self) -> None:
        """A cron job cannot be a required PR context, so it need not be declared."""
        workflows = {
            "cron.yml": {
                "on": {"schedule": [{"cron": "0 5 * * *"}]},
                "jobs": {"run": {}},
            }
        }
        assert declaration_problems(workflows, (), {}) == []
