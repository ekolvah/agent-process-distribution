"""Git guard: stops the agent's merge and irreversible git commands and names the alternative.

The process says the person merges, and the ruleset only covers the server side: a push to the
default branch and a merge without the required checks. Nothing stopped `gh pr merge` on a green
PR, a local `git reset --hard` or `git branch -D`, or `--no-verify` skipping the hooks `init`
installs. A `permissions.deny` block did, in the repositories that copied one; a plugin cannot
ship that block (its `settings` honour only `agent` and `subagentStatusLine`), and a deny rule
names no alternative. A `PreToolUse` hook does both.

A guardrail against agent error, not a security boundary: like any command-text rule it misses
`git 'push'`, a variable, `eval` or a script file. The boundary for merging is an agent identity
without merge rights on the server.

A command the lexer cannot read (typically a heredoc body with an apostrophe) is not checked; when
it names `git` or `gh`, that is a visible, non-blocking hook error, not silence.

The plugin's `hooks/hooks.json` runs it as `agent-process git_guard pre-bash` (PreToolUse,
matcher `Bash`), with the hook JSON on stdin.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass

from navigation_policy import _basename, _deny, first_stage_verdict

_UNCHECKED = "git_guard: command not parsed, not checked"
_GIT_WORD = re.compile(r"\b(?:git|gh)\b")
_DEFAULT_BRANCH = frozenset({"main", "refs/heads/main"})

# Git's global options that take a separate value before the subcommand: `git -C . push`.
_GLOBAL_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})

# Per subcommand, the options whose value is the next token, so `commit -m "--no-verify"` reads
# the message as a value and not as a flag. Short ones also end a cluster: `-nm x`.
_VALUE_OPTIONS: dict[str, frozenset[str]] = {
    "commit": frozenset(
        {
            "-m",
            "-F",
            "-C",
            "-c",
            "-t",
            "--message",
            "--file",
            "--author",
            "--date",
            "--template",
            "--trailer",
            "--fixup",
            "--squash",
            "--reuse-message",
            "--reedit-message",
            "--cleanup",
        }
    ),
    "push": frozenset({"-o", "--push-option", "--repo", "--receive-pack", "--exec"}),
    "branch": frozenset({"-u", "--set-upstream-to", "--sort", "--format"}),
}

_MERGE = "The person merges: report the PR and wait with `agent-process wait_for_pr`."
_REPO_DELETE = "Deleting a repository is the person's action."
_PUSH_MAIN = "Push the branch and open a PR; the default branch changes only through a PR."
_FORCE = "Add a commit on top instead of rewriting pushed history."
_NO_VERIFY = "Fix what the hook reports; hooks are not bypassed."
_RESET_HARD = "`git stash` keeps the changes; ask the person before discarding them."
_BRANCH_FORCE_DELETE = "`git branch -d` deletes a merged branch; ask the person otherwise."


@dataclass(frozen=True)
class Arguments:
    """A git subcommand's arguments: long flags by name, short flags one per letter."""

    flags: frozenset[str]
    operands: list[str]


def _split(subcommand: str, rest: list[str]) -> Arguments:
    value_options = _VALUE_OPTIONS.get(subcommand, frozenset())
    flags: set[str] = set()
    operands: list[str] = []
    index = 0
    while index < len(rest):
        token = rest[index]
        index += 1
        if token == "--":
            operands += rest[index:]
            break
        if token.startswith("--"):
            name, joined, _ = token.partition("=")
            flags.add(name)
            if name in value_options and not joined:
                index += 1
        elif token.startswith("-") and token != "-":
            for position, char in enumerate(token[1:], start=1):
                flags.add(f"-{char}")
                if f"-{char}" in value_options:
                    index += 0 if token[position + 1 :] else 1
                    break
        else:
            operands.append(token)
    return Arguments(frozenset(flags), operands)


def _push(args: Arguments) -> str | None:
    refspecs = args.operands[1:]
    if any(spec.rpartition(":")[2] in _DEFAULT_BRANCH for spec in refspecs):
        return _PUSH_MAIN
    force = {"--force", "-f", "--force-with-lease", "--force-if-includes"}
    if args.flags & force or any(spec.startswith("+") for spec in refspecs):
        return _FORCE
    return _NO_VERIFY if "--no-verify" in args.flags else None


def _commit(args: Arguments) -> str | None:
    return _NO_VERIFY if args.flags & {"--no-verify", "-n"} else None


def _reset(args: Arguments) -> str | None:
    return _RESET_HARD if "--hard" in args.flags else None


def _branch(args: Arguments) -> str | None:
    delete = args.flags & {"-d", "--delete"} and args.flags & {"-f", "--force"}
    return _BRANCH_FORCE_DELETE if "-D" in args.flags or delete else None


_GIT_RULES: dict[str, Callable[[Arguments], str | None]] = {
    "push": _push,
    "commit": _commit,
    "reset": _reset,
    "branch": _branch,
}


def _git(args: list[str]) -> str | None:
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in _GLOBAL_VALUE_OPTIONS else 1
    if index >= len(args) or args[index] not in _GIT_RULES:
        return None
    subcommand = args[index]
    return _GIT_RULES[subcommand](_split(subcommand, args[index + 1 :]))


def _gh(args: list[str]) -> str | None:
    return {("pr", "merge"): _MERGE, ("repo", "delete"): _REPO_DELETE}.get(tuple(args[:2]))


def _rule(tokens: list[str]) -> str | None:
    name = _basename(tokens[0])
    if name == "git":
        return _git(tokens[1:])
    return _gh(tokens[1:]) if name == "gh" else None


def main() -> None:
    if sys.argv[1:] != ["pre-bash"]:
        # Exit 1, not 2: behind a `Bash` matcher exit 2 denies every call, while a hook and a
        # script from different revisions must degrade to a visible, non-blocking error.
        print(
            "usage: agent-process git_guard pre-bash (reads the hook JSON on stdin)",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        sys.exit(0)
    try:
        reason = first_stage_verdict(command, _rule)
    except ValueError:
        if _GIT_WORD.search(command):
            print(_UNCHECKED, file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    if reason is not None:
        print(json.dumps(_deny(reason)))
    sys.exit(0)


if __name__ == "__main__":
    main()
