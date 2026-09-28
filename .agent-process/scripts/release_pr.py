#!/usr/bin/env python3
"""Publish whether a PR is a release PR: `release=true|false` (ADR 0031).

A release PR changes only the files release-please versions, and each of them (the changelog
aside) has its base's lines, each unchanged or with the manifest's old versions replaced by the
new ones. The config
and the manifest are read at the base, so a PR cannot widen the set it is judged by.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

try:
    from scripts.gh_io import publish_step_output, run_gh
except ModuleNotFoundError:  # run as a script from `.agent-process/`
    from gh_io import publish_step_output, run_gh

CONFIG = "release-please-config.json"
MANIFEST = ".release-please-manifest.json"
COMPARE_FILE_LIMIT = 300  # the compare API lists no more files than this


def _release_set(config: dict) -> tuple[set[str], set[str]]:
    """Return (every path release-please writes, the changelogs among them)."""
    paths, changelogs = {MANIFEST}, set()
    for package, spec in config.get("packages", {}).items():
        prefix = "" if package == "." else package.strip("/") + "/"
        changelogs.add(prefix + spec.get("changelog-path", "CHANGELOG.md"))
        for extra in spec.get("extra-files", ()):
            path = extra if isinstance(extra, str) else extra["path"]
            paths.add(path.lstrip("/") if path.startswith("/") else prefix + path)
    return paths | changelogs, changelogs


def _bumps(base_text: dict[str, str], head_text: dict[str, str]) -> dict[str, str]:
    base, head = json.loads(base_text[MANIFEST]), json.loads(head_text[MANIFEST])
    return {base[key]: new for key, new in head.items() if base.get(key) not in (None, new)}


def release_verdict(
    config: dict | None,
    changes: list[tuple[str, str]],
    base_text: dict[str, str],
    head_text: dict[str, str],
) -> str | None:
    """None for a release PR, otherwise why not, naming the file.

    `changes` are the PR's (path, compare status); `base_text` holds the manifest and
    `head_text` the changed manifest, each also holding every in-set, non-changelog,
    `modified` path.
    """
    if config is None:
        return f"no {CONFIG} at the base"
    release_set, changelogs = _release_set(config)
    statuses = dict(changes)
    outside = sorted(set(statuses) - release_set)
    if outside:
        return f"{', '.join(outside)} outside the release set"
    if statuses.get(MANIFEST) != "modified":
        return f"{MANIFEST} is not modified"
    bumps = _bumps(base_text, head_text)
    if not bumps:
        return f"{MANIFEST} changes no version"
    versioned = {path: status for path, status in statuses.items() if path not in changelogs}
    return _beyond_the_version(versioned, bumps, base_text, head_text)


def _beyond_the_version(
    statuses: dict[str, str],
    bumps: dict[str, str],
    base_text: dict[str, str],
    head_text: dict[str, str],
) -> str | None:
    for path, status in sorted(statuses.items()):
        if status != "modified":
            return f"{path} is {status}, not modified"
        base_lines = base_text[path].splitlines(keepends=True)
        head_lines = head_text[path].splitlines(keepends=True)
        if len(head_lines) != len(base_lines) or not all(
            head in (base, _bumped(base, bumps))
            for base, head in zip(base_lines, head_lines, strict=True)
        ):
            return f"{path} changes more than the version"
    return None


def _bumped(line: str, bumps: dict[str, str]) -> str:
    for old, new in bumps.items():
        line = line.replace(old, new)
    return line


def _read(repo: str, path: str, ref: str) -> str:
    return run_gh(
        [
            "api",
            "-H",
            "Accept: application/vnd.github.raw",
            f"repos/{repo}/contents/{path}?ref={ref}",
        ]
    )


def _judge(options: argparse.Namespace) -> tuple[str | None, str]:
    """Return (the verdict, the new version) of the PR's base and head."""
    repo, base, head = options.repo, options.base_sha, options.head_sha
    files = json.loads(run_gh(["api", f"repos/{repo}/compare/{base}...{head}"]))["files"]
    if len(files) >= COMPARE_FILE_LIMIT:
        return f"the compare lists {len(files)} files, the limit is {COMPARE_FILE_LIMIT} files", ""
    changes = [(entry["filename"], entry["status"]) for entry in files]
    root = json.loads(run_gh(["api", f"repos/{repo}/contents/?ref={base}"]))
    if not any(entry["name"] == CONFIG for entry in root):
        return release_verdict(None, changes, {}, {}), ""
    config = json.loads(_read(repo, CONFIG, base))
    release_set, changelogs = _release_set(config)
    base_text, head_text = {MANIFEST: _read(repo, MANIFEST, base)}, {}
    for path, status in changes:
        if path in release_set and path not in changelogs and status == "modified":
            base_text[path], head_text[path] = _read(repo, path, base), _read(repo, path, head)
    verdict = release_verdict(config, changes, base_text, head_text)
    version = "" if verdict else ", ".join(sorted(set(_bumps(base_text, head_text).values())))
    return verdict, version


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    options = _parse_options(argv)
    try:
        verdict, version = _judge(options)
    except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: cannot tell whether PR {options.pr} is a release PR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if verdict is None:
        print(f"release PR: {version}")
        publish_step_output("release=true")
    else:
        print(f"not a release PR: {verdict}")
        publish_step_output("release=false")


if __name__ == "__main__":
    main()
