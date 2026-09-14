"""GitHub Project ids for this repository (ADR 0026); `init` rewrites them in v2-2."""

PROJECT_NUMBER = "4"
PROJECT_OWNER = "ekolvah"
PROJECT_ID = "PVT_kwHOApeba84Bhf2x"
PRIORITY_FIELD_ID = "PVTSSF_lAHOApeba84Bhf2xzhgbY60"
PRIORITY_OPTION_IDS = {"high": "52e70f3f", "medium": "a48fdb74", "low": "28ce4089"}
STATUS_FIELD_ID = "PVTSSF_lAHOApeba84Bhf2xzhgbY5M"
STATUS_OPTION_IDS = {"planned": "e6defd68", "in-progress": "47fc9ee4"}


def require_configured() -> None:
    """Fail before any ``gh project`` operation when the Project ids are blank."""
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
            "Agent process is installed but inactive: GitHub Project ids are blank in "
            ".agent-process/scripts/project_settings.py; fill them from the Project's field ids"
        )
