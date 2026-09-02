"""Preflight the credentials required by the two review carriers.

The check is read-only. Exit 0 means both prerequisites are present, exit 1
means one is absent, and exit 2 means GitHub did not supply enough evidence to
make either claim.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from scripts.gh_io import slurp_named_records
    from scripts.request_codex_review import CODEX_REVIEWER
except ModuleNotFoundError:  # Direct execution from the relocated payload.
    from gh_io import slurp_named_records
    from request_codex_review import CODEX_REVIEWER

REVIEW_SECRET = "CLAUDE_CODE_OAUTH_TOKEN"  # pragma: allowlist secret
_SETTINGS_URL = "https://github.com/settings/installations"


@dataclass(frozen=True)
class Prerequisite:
    name: str
    status: int
    message: str


def codex_app_slug() -> str:
    """Derive the GitHub App slug from the reviewer's one canonical login."""
    return CODEX_REVIEWER.split("[", 1)[0]


def workflow_secret_references(workflows: Path) -> set[str]:
    """Return explicitly mapped repository-secret names from rendered callers."""
    references: set[str] = set()
    for path in workflows.glob("agent-review.y*ml"):
        references.update(re.findall(r"secrets\.([A-Za-z0-9_]+)", path.read_text(encoding="utf-8")))
    return references


def _secret_names(records: list[Mapping[str, object]]) -> set[str]:
    return {
        str(record["name"]).casefold() for record in records if isinstance(record.get("name"), str)
    }


def _secret_prerequisite(repository: str) -> Prerequisite:
    try:
        names = _secret_names(
            slurp_named_records(f"repos/{repository}/actions/secrets?per_page=100", "secrets")
        )
    except RuntimeError as exc:
        return Prerequisite(
            "carrier-1 secret",
            2,
            f"cannot determine whether {REVIEW_SECRET} is present: {exc}",
        )
    if REVIEW_SECRET.casefold() in names:
        return Prerequisite(
            "carrier-1 secret",
            0,
            f"ok: {REVIEW_SECRET} is present (presence-only; its value is not validated)",
        )
    try:
        names = _secret_names(
            slurp_named_records(
                f"repos/{repository}/actions/organization-secrets?per_page=100", "secrets"
            )
        )
    except RuntimeError as exc:
        return Prerequisite(
            "carrier-1 secret",
            2,
            f"cannot determine whether {REVIEW_SECRET} is present: {exc}",
        )
    if REVIEW_SECRET.casefold() in names:
        return Prerequisite(
            "carrier-1 secret",
            0,
            f"ok: {REVIEW_SECRET} is present (presence-only; its value is not validated)",
        )
    return Prerequisite(
        "carrier-1 secret",
        1,
        f"missing {REVIEW_SECRET}; add it with `gh secret set {REVIEW_SECRET} --repo {repository}` "
        f"or use https://github.com/{repository}/settings/secrets/actions",
    )


def _app_prerequisite(repository: str) -> Prerequisite:
    slug = codex_app_slug()
    # Live probe, 2026-08-23: the maintainer's ordinary `gh` token received 403
    # from `user/installations` and 401 from `repos/{owner}/{repo}/installation`.
    # The first route is still the only user-to-server collection route attempted:
    # a non-zero answer is exit 2, never a false "App absent" verdict.
    try:
        installations = slurp_named_records("user/installations?per_page=100", "installations")
        matching = [
            installation
            for installation in installations
            if str(installation.get("app_slug", "")).casefold() == slug.casefold()
        ]
        if not matching:
            return Prerequisite(
                "carrier-2 App",
                1,
                f"missing GitHub App {slug}; install and grant it this repository at {_SETTINGS_URL}",
            )
        for installation in matching:
            installation_id = installation.get("id")
            if not isinstance(installation_id, int):
                raise RuntimeError(f"installation for {slug} has no numeric id")
            repositories = slurp_named_records(
                f"user/installations/{installation_id}/repositories?per_page=100",
                "repositories",
            )
            if any(
                str(candidate.get("full_name", "")).casefold() == repository.casefold()
                for candidate in repositories
            ):
                return Prerequisite("carrier-2 App", 0, f"ok: {slug} covers {repository}")
    except RuntimeError as exc:
        return Prerequisite(
            "carrier-2 App",
            2,
            f"cannot determine whether {slug} covers {repository}: {exc}. Check {_SETTINGS_URL}",
        )
    return Prerequisite(
        "carrier-2 App",
        1,
        f"GitHub App {slug} does not cover {repository}; grant it repository access at {_SETTINGS_URL}",
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="OWNER/REPOSITORY")
    options = parser.parse_args(argv)
    repository = options.repo.strip().strip("/")
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        parser.error("--repo must be OWNER/REPOSITORY")

    results = (_secret_prerequisite(repository), _app_prerequisite(repository))
    for result in results:
        stream = sys.stderr if result.status else sys.stdout
        print(result.message, file=stream)
    if any(result.status == 2 for result in results):
        raise SystemExit(2)
    if any(result.status == 1 for result in results):
        raise SystemExit(1)
    print("ok: review credentials are present; secret verification is presence-only")


if __name__ == "__main__":
    main()
