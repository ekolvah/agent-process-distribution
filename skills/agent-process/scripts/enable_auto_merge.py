#!/usr/bin/env python3
"""Let the person's approval merge the agent's PR.

Usage: agent-process enable_auto_merge <PR>

Run right after `gh pr create`. The script reads `gh pr view <PR> --json reviewDecision` and
runs `gh pr merge <PR> --auto --squash` only when it is `REVIEW_REQUIRED`: GitHub then holds
the PR for an approval, and the approval merges it once the required checks pass. Any other
value — empty where no rule asks for an approval, `APPROVED` — enables nothing, since
auto-merge there would merge the agent's PR without the person.

Exit 0: auto-merge enabled, the person's approval merges the PR; 1: not enabled, the value
read printed, the person merges; 2: `gh` failed, its message printed (a repository that does
not allow auto-merge, or allows no squash, is refused here).
"""

from __future__ import annotations

import argparse
import sys

from set_status import Gh, _json, run_gh

GATE = "REVIEW_REQUIRED"


def enable_auto_merge(pr: int, *, gh: Gh) -> int:
    view = _json(gh, ["gh", "pr", "view", str(pr), "--json", "reviewDecision"])
    decision = str(view.get("reviewDecision") or "")
    if decision != GATE:
        print(
            f"auto-merge not enabled on #{pr}: reviewDecision is {decision or 'empty'},"
            f" not {GATE}; the person merges"
        )
        return 1
    gh(["gh", "pr", "merge", str(pr), "--auto", "--squash"])
    print(f"auto-merge (squash) enabled on #{pr}: the person's approval merges it")
    return 0


def main(argv: list[str] | None = None, *, gh: Gh = run_gh) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr", type=int, help="the agent's PR number")
    ns = parser.parse_args(argv)
    try:
        sys.exit(enable_auto_merge(ns.pr, gh=gh))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
