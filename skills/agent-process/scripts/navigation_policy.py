"""Navigation policy: a whole-file `Read` whose cost a cheaper call avoids.

A `Read` that pulls a whole large file into context has a cheaper form of itself — a `Grep` or
a slice (`read_budget_hint`). The refusal names the replacement, and it is advisory about cost,
never about safety.

Shell navigation (`cat`, `grep`, `ls`) is not refused. Measured over the local transcripts, a
refusal cost more tokens than the output it kept out of context: the agent paid for the retry
and usually ran another shell command anyway.

The plugin's `hooks/hooks.json` runs it as `agent-process navigation_policy pre-read`
(PreToolUse, matcher `Read`), with the hook JSON on stdin.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The budget, in bytes of the slice `Read` will actually return.
#
# Derived from a measurement over the 203 tracked files on 2026-08-15, not from taste. The
# text corpus ran p50/p75/p90/p95 = 6457 / 13311 / 25694 / 41000 bytes; `principles.md` (16108)
# and `testing.md` (24113) are the two documents this repository orders read *whole*, and the
# smallest driver of the incident below was `tests/agent_process/test_agent_orchestrator.py` (31410). 28000
# is the corridor between them: above everything prescribed whole, below every driver. A
# 16000 threshold was rejected for missing `principles.md` by 108 bytes — pure friction on the
# hottest agent route, saving nothing, since that content is prescribed in full.
#
# Tuning direction is DOWNWARD ONLY, and only on observation. A ratchet that starts loose and
# tightens on data costs less than one that starts tight and gets routed around.
_READ_BUDGET_BYTES = 28_000

# Formats where `offset`/`limit` are not line offsets into text, so the replacement this
# policy names would not apply.
_UNSLICEABLE = frozenset({".pdf", ".ipynb", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})


def _lines_that_fit(lines: list[bytes], start: int) -> int:
    """How many lines from `start` stay inside the budget — at least one, so the message
    never hands back an empty slice."""
    total = 0
    fits = 0
    for line in lines[start:]:
        total += len(line)
        if total > _READ_BUDGET_BYTES:
            break
        fits += 1
    return max(fits, 1)


def read_budget_hint(file_path: object, offset: object = None, limit: object = None) -> str | None:
    """Return a replacement message when a `Read` slice exceeds the byte budget.

    Why `Read` needs a gate. Whole-file `Read` turned out to be the expensive route into the
    filesystem. A measured run
    took 53 steps before a single line of code, with context growing from 29k to 166k, driven by
    ten whole-file reads. The harm is not re-sending those bytes — that goes through
    `cache_read` — it is the chain **ceiling → compaction → reading the same files again**;
    the session paid for its five largest files twice.

    Why the budget is on bytes and not on the presence of `limit`. `limit` counts LINES and
    `Read` truncates at 2000 of them, while the longest file here is 1196 lines: an explicit
    `limit=2000` returns byte-identical content to a whole-file read for every file in this
    repository. So the measurement is the slice `[offset, offset + limit)` as it lands on
    disk, computed here — the hook's own bytes never enter the agent's context.

    The token figure is APPROXIMATE in both directions. `bytes / 4` holds for Latin text; for
    Cyrillic, UTF-8 spends ~2 bytes per character at ~1 token per character, so the byte count
    overstates the size (the refusal fires early, on the policy's side) while the printed
    estimate understates the tokens. Neither number is exact and the message says so.

    Fail-open on every axis it cannot measure — a non-string path, a missing file, a
    directory, bytes that are not UTF-8, a format where slicing is meaningless. This policy
    claims only that a cheaper route exists, so anything unmeasurable is "no opinion".

    The hook is STATELESS: after a compaction, a legitimately large read pays the
    refusal-and-retry again. That is the accepted price of not carrying session state into a
    `PreToolUse` hook, recorded here so it is not reopened as a bug.

    Mechanics confirmed against the documentation, not guessed: `PreToolUse` matches ANY tool
    name, not just `Bash`, and `permissionDecisionReason` is delivered to the model —
    https://code.claude.com/docs/en/hooks

    Revision condition: if refusals fire and context growth before the first edit does not
    fall, tighten the threshold or revert the rule.
    """
    if not isinstance(file_path, str):
        return None
    if (offset is not None and not isinstance(offset, int)) or (
        limit is not None and not isinstance(limit, int)
    ):
        return None
    path = Path(file_path)
    try:
        if not path.is_file() or path.suffix.lower() in _UNSLICEABLE:
            return None
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    lines = raw.splitlines(keepends=True)
    start = max(offset - 1, 0) if offset is not None else 0
    window = lines[start:] if limit is None else lines[start : start + max(limit, 0)]
    size = sum(len(line) for line in window)
    if size <= _READ_BUDGET_BYTES:
        return None
    return (
        f'Read("{file_path}") returns {size} bytes (~{size // 4} tokens, approximate) — over '
        f"the {_READ_BUDGET_BYTES}-byte budget. Grep for the symbol you need, or read the "
        f"largest slice that fits from here: offset={start + 1}, "
        f"limit={_lines_that_fit(lines, start)}. "
        "Rewriting the file whole? Read it in slices first — never Write over bytes you have "
        "not seen."
    )


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def pre_read_response(payload: dict) -> dict | None:
    """Return Claude's PreToolUse denial shape when a `Read` slice busts the budget.

    Fail-open: the policy claims only that a cheaper route exists, and behind a `Read` matcher
    a payload bug that denied would take the agent's primary way of seeing the repository
    with it.
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    hint = read_budget_hint(
        tool_input.get("file_path"), tool_input.get("offset"), tool_input.get("limit")
    )
    return None if hint is None else _deny(hint)


def main() -> None:
    if sys.argv[1:] != ["pre-read"]:
        # Exit 1, not 2: exit 2 would deny the call, and a released `hooks.json` that still
        # names a removed subcommand (`pre-bash`) must degrade to a visible, non-blocking error.
        print(
            "usage: agent-process navigation_policy pre-read (reads the hook JSON on stdin)",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    # PreToolUse denies via exit 0 + JSON on stdout; exit 2 would discard the JSON and feed
    # stderr instead, losing the replacement message this hook exists to deliver.
    response = pre_read_response(payload if isinstance(payload, dict) else {})
    if response is not None:
        print(json.dumps(response))
    sys.exit(0)


if __name__ == "__main__":
    main()
