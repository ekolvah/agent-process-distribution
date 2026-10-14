#!/usr/bin/env python3
"""Print the per-task dashboard for a list of repositories, ready for Grafana's import.

Usage: agent-process dashboard <owner/name>... > per-task.json

The template is `templates/per-task-dashboard.json`: each data panel holds one prototype
Infinity query carrying the token `__REPOSITORY__`. The render replaces it with one copy per
repository, refIds `A`, `B`..., each reading that repository's `task-readings.csv` and
giving its rows a `repository` column; the panel merges them. One repository is a
per-project dashboard; several are one dashboard holding all their tasks. The Infinity
datasource stays the import input `DS_INFINITY`, chosen on Grafana's Import page.

Exit 2, with nothing on stdout, when no repository is given or an argument is not
`<owner>/<name>`. A repository listed twice, in any letter case, renders once.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "per-task-dashboard.json"
TOKEN = "__REPOSITORY__"
# GitHub rejects `.` and `..` as a repository name.
REPOSITORY = re.compile(r"[A-Za-z0-9-]+/(?!\.\.?$)[A-Za-z0-9._-]+")


def _ref_id(index: int) -> str:
    """`A`...`Z`, then `AA`, `AB`...: Grafana's own refId sequence."""
    name = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(ord("A") + rest) + name
    return name


def render(repositories: list[str]) -> dict:
    dashboard = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    for panel in dashboard["panels"]:
        if "targets" not in panel:
            continue
        (prototype,) = panel["targets"]
        text = json.dumps(prototype)
        panel["targets"] = [
            {**json.loads(text.replace(TOKEN, repository)), "refId": _ref_id(index)}
            for index, repository in enumerate(repositories)
        ]
    dashboard["title"] = f"{dashboard['title']}: {', '.join(repositories)}"
    return dashboard


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: agent-process dashboard <owner/name>...", file=sys.stderr)
        return 2
    for argument in argv:
        if not REPOSITORY.fullmatch(argument):
            print(f"{argument}: not <owner>/<name>", file=sys.stderr)
            return 2
    # GitHub names are case-insensitive: the first spelling of a repository is kept.
    unique: dict[str, str] = {}
    for argument in argv:
        unique.setdefault(argument.casefold(), argument)
    print(json.dumps(render(list(unique.values())), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
