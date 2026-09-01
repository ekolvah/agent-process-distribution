"""Persisted GitHub Project identifiers created by bootstrap.

Repository activation runs ``python .agent-process/scripts/bootstrap_github_project.py`` and
rewrites this module with real, project-owned IDs. It is deliberately tracked:
every process runner must use the same board.
"""

PROJECT_NUMBER = "4"
PROJECT_OWNER = "ekolvah"
PROJECT_ID = "PVT_kwHOApeba84Bhf2x"
PRIORITY_FIELD_ID = "PVTSSF_lAHOApeba84Bhf2xzhgbY60"
PRIORITY_OPTION_IDS = {"high": "52e70f3f", "medium": "a48fdb74", "low": "28ce4089"}
STATUS_FIELD_ID = "PVTSSF_lAHOApeba84Bhf2xzhgbY64"
STATUS_OPTION_IDS = {"planned": "aec55350", "in-progress": "fdfac3be"}


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
            "`python .agent-process/scripts/bootstrap_github_project.py` first"
        )
