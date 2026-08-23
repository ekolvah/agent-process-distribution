"""Persisted GitHub Project identifiers created by bootstrap.

Run ``python scripts/bootstrap_github_project.py`` before planning or
implementation. Bootstrap rewrites this module with real, project-owned IDs.
It is deliberately tracked: every process runner must use the same board.
"""

PROJECT_NUMBER = ""
PROJECT_OWNER = ""
PROJECT_ID = ""
PRIORITY_FIELD_ID = ""
PRIORITY_OPTION_IDS: dict[str, str] = {}
STATUS_FIELD_ID = ""
STATUS_OPTION_IDS: dict[str, str] = {}


def require_configured() -> None:
    """Fail before any ``gh project`` operation when bootstrap has not run."""
    required = (
        PROJECT_NUMBER,
        PROJECT_OWNER,
        PROJECT_ID,
        PRIORITY_FIELD_ID,
        STATUS_FIELD_ID,
    )
    if (
        not all(required)
        or set(PRIORITY_OPTION_IDS) != {"high", "medium", "low"}
        or set(STATUS_OPTION_IDS) != {"planned", "in-progress"}
    ):
        raise RuntimeError(
            "Agent process is installed but inactive: GitHub Project bootstrap is incomplete; run "
            "`python scripts/bootstrap_github_project.py` first"
        )
