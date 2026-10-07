## Why

The required `agent-review` check is green on every consumer PR while the review leaves no
trace of what it checked (#363). On ekolvah/kinozal_scraper, ~16 PRs reviewed by
`reusable-agent-review.yml@v3.10.1` produced one finding; sessions last 5–37 s with 1–7
permission denials in most runs (e.g. #640, run 37582632300:
`duration_ms=16336 num_turns=9 permission_denials_count=1`), and each still posts
`Reviewed head SHA: <sha>`.

The same holds here: #324 (+948/−480, 27 files) added `edit_lint`, which ran `pre-commit`
from the main checkout for every edited file. Its review, run 37012839939
(`claude-sonnet-5-5`, `duration_ms=20717 num_turns=10 permission_denials_count=1`), posted
`No findings.` and the check went green. The defect reached 3.10.0 and was fixed four days
later in #361 (#360: a worktree file linted against the main checkout's root and config).
Nothing on the PR said what the review had read or which call was denied.

Reproduction (the issue's comment): a local replay of #640 with the CI prompt, allowlist and
model had 0 denials and ended with a substantive final message — scope read, "nothing to
flag", and an explicit "Not verified" list. CI discards that message (`show_full_output:
false`, "no other comment"). A local probe confirms a denied call does not end the session
badly: `claude -p … --allowed-tools "Bash(gh pr diff:*)" --output-format json` asked to run
`gh api user` returned `subtype: success, is_error: false` with
`permission_denials: [{tool_name: Bash, tool_input: {command: "gh api user ."}}]` and the
final text in `result`.

Root cause: the close step posts the marker on `conclusion == success`
(`.github/workflows/reusable-agent-review.yml`, `Close the Claude review of the head`), which
only says the session ended normally. A session that read nothing, ended silently, or was
denied its tools gets the same marker as a full review, and the final message that tells them
apart is thrown away. The cause of the CI denial stays unobserved for the same reason.

## What Changes

- The close step builds the closing comment from the action's `execution_file`: the
  `Reviewed head SHA: <sha>` marker, the session's final message verbatim, and every permission
  denial (tool and command).
- A session whose final message is empty, or whose execution file has no result message,
  gets no closing comment and fails the check: a silent finish is not a clean review.
- Denials do not fail the check.
- The prompt asks the model to end with a final message naming what
  it read, the findings it posted, and what it did not verify.
- Out of scope, decided from the denials this change makes visible: the `--allowed-tools`
  list and a pinned `--model` (design, Non-Goals).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review-and-merge`: *Claude reviews every head* — the closing comment carries the session's
  final message and its permission denials; a session without a final message fails the check.

## Impact

- Added: `.agent-process/scripts/close_review.py`, `tests/publisher/test_close_review.py`.
- Edited: `.github/workflows/reusable-agent-review.yml` (close step, prompt),
  `tests/publisher/test_reusable_workflows.py`,
  `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md` (one
  More Information bullet: the job republishes the final message and gates on its presence,
  never on its content).
- Spec: `openspec/specs/review-and-merge/spec.md` through the archive of this change.
- Consumers get it with the next release through the pinned reusable workflow; no consumer
  file changes. The closing comment keeps its marker line, so `head_review.py` is unchanged.
