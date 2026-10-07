"""Build the review job's closing comment from the Claude session's execution file.

The action writes every SDK message of the session to its ``execution_file``. The body is
the marker ``Reviewed head SHA: <sha>`` on the first line, so ``head_review.py`` finds it
before any text the model wrote, then the last result message's final text verbatim, then
every permission denial on its own line. Nothing here judges what the text says (ADR 0027):
a session that ends without a final message is a silent finish and exits 1 with no body.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path


class SilentFinish(Exception):
    """The execution file holds no final message of the session."""


def _final_result(execution_file: Path) -> Mapping[str, object]:
    try:
        messages = json.loads(execution_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SilentFinish(f"cannot read the execution file {execution_file}: {exc}") from exc
    if not isinstance(messages, list):
        raise SilentFinish(f"the execution file {execution_file} is not a list of messages")
    results = [m for m in messages if isinstance(m, Mapping) and m.get("type") == "result"]
    if not results:
        raise SilentFinish("the session has no result message")
    text = results[-1].get("result")
    if not isinstance(text, str) or not text.strip():
        raise SilentFinish("the session ended without a final message")
    return results[-1]


def _denial_line(denial: object) -> str:
    if not isinstance(denial, Mapping):
        return f"- {json.dumps(denial)}"
    tool_input = denial.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, Mapping) else None
    shown = command if isinstance(command, str) else tool_input
    return f"- {denial.get('tool_name')}: {json.dumps(shown, separators=(',', ':'))}"


def closing_body(result: Mapping[str, object], head_sha: str) -> str:
    denials = result.get("permission_denials")
    denials = denials if isinstance(denials, list) else []
    lines = [
        f"Reviewed head SHA: {head_sha}",
        "",
        str(result["result"]),
        "",
        f"Permission denials: {len(denials)}",
        *(_denial_line(denial) for denial in denials),
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--execution-file", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--body-file", type=Path, required=True)
    options = parser.parse_args(argv)
    try:
        result = _final_result(options.execution_file)
    except SilentFinish as exc:
        print(f"::error::No review of {options.head_sha}: {exc}")
        raise SystemExit(1) from exc
    options.body_file.write_text(
        closing_body(result, options.head_sha), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
