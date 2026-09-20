## Verdict

approve — bounded correction for the observed GitHub Actions bootstrap failure.

## Findings

- The proposal records the live reproduction and exact root cause rather than inferring
  from an empty check rollup.
- The delta keeps the immutable-tag guarantee for consumers and narrows the exception to
  this publisher, where the release tag cannot exist before merge.
- The design names the lost immutable-callee proof and the reached catcher: settled-head
  workflow diff inspection by the person before merge.
- The tasks preserve RED-first evidence, the archived-design amendment, strict OpenSpec,
  full CI, and the current-head review loop without creating another issue or branch.

## Scenario coverage

Both delta scenarios map to separate structural tests: the installed consumer template
remains tag-pinned and the publisher caller uses the repository-local reusable workflow.
