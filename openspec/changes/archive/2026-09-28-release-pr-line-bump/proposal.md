## Why

Release PR 258 (`chore(main): release 3.0.3`) fails `agent-process / link` with
`not a release PR: skills/agent-process/scripts/init.py changes more than the version`, and
`agent-process / quality` fails after it (run 36472852057, base `1e14286`, head `26000da`). The
PR's diff of that file is the one annotated line `VERSION = "3.0.2"  # x-release-please-version`
→ `"3.0.3"`.

Root cause: `.agent-process/scripts/release_pr.py::_beyond_the_version` expects the head of a
versioned file to be its base with every occurrence of the old version replaced. Release-please
rewrites only the annotated line and the JSON version fields. `init.py` also holds the comment
`# The \`test:\` input of a caller rendered by \`init\` up to 3.0.2.`, which the release keeps as
it is, so the detector's expected head differs from the real one. Any literal of the old version
in a versioned file blocks the next release this way (#260).

## What Changes

- A versioned file passes when it has the same number of lines as its base and each line either
  equals its base line or equals it with the old manifest versions replaced by the new ones.
  A line that keeps the old version no longer disqualifies the PR; a line added, removed or
  changed in any other way still does.

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: requirement "A release PR is recognised by its diff" compares versioned
  files line by line and gains the scenario of an old version kept elsewhere in the file.

## Impact

- Edited: `.agent-process/scripts/release_pr.py` (`_beyond_the_version` and the module
  docstring), `tests/publisher/test_release_pr.py`,
  `.agent-process/docs/adr/0031-release-prs-merge-without-the-person.md` (D1 wording),
  `openspec/specs/review-and-merge/spec.md` (by the archive).
- Added and removed: none.
- After the merge, release-please rebuilds PR 258 on the new `main` and its gates run again with
  the fixed detector; no consumer action.
