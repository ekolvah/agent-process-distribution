## Why

`close_review.closing_body` copies the session into the closing comment without a bound and
puts the model's text before the denials. Observed on `main` (d91109c), from `.agent-process/`:

```
$ python -c "
from scripts import close_review as c
r={'result':'Summary <!--','permission_denials':[{'tool_name':'Write','tool_input':{'file_path':'a.py','content':'x'*100_000}}]}
b=c.closing_body(r,'a'*40); print(len(b), b.index('Permission denials') > b.index('<!--'))"
100140 True
```

- **No bound.** A denied `Write`/`Edit` puts its whole `tool_input` in the body. GitHub rejects
  a comment over 65,536 characters. A GitHub staff answer says the limit is the same in the UI and
  the API ([community thread](https://github.community/t/maximum-length-for-the-comment-body-in-issues-and-pr/148867)):
  bodies are stored as a `mediumblob` of 262,144 bytes, "65,536 4-byte unicode characters". A
  body over the limit makes `gh pr comment` fail, so the Close step goes red and posts no comment.
  Each re-run pays for a new review, posts its inline findings again, and fails the same way, so
  the head never goes green.
- **Hidden denials.** The final message is raw Markdown and comes before
  `Permission denials: <n>`. An unclosed `<!--` or `<details>` in it, which PR content can steer,
  hides the denials on the rendered PR. ADR 0027 makes denials visible instead of failing on them,
  so hiding them removes their only signal.

Root cause: `closing_body` joins the parts in the order marker, message, denials and bounds
none of them. The step has not run live: the only run since the merge was a release PR, which
skips the review.

## What Changes

- The closing comment puts the marker first. The denial count and the denials come next, in a
  fenced block, and the final message comes last.
- Each denial line is cut at a fixed length, and the whole body at a budget below GitHub's limit.
  Each cut ends with `… truncated`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review-and-merge`: "Claude reviews every head" lists the denials in a fenced block before
  the final message. It bounds the comment under GitHub's limit with an explicit truncation
  marker.

## Impact

- Edited: `.agent-process/scripts/close_review.py` (order, fence, bounds, module docstring).
- Edited: `tests/publisher/test_close_review.py` (new tests; the multi-line test counts lines
  inside the block).
- Edited by archive: `openspec/specs/review-and-merge/spec.md`.
- Not edited: `.github/workflows/reusable-agent-review.yml` (it calls the same CLI). ADR 0027's
  sentence "republishes, below the marker, the final message and every denied tool call" stays
  true. `.agent-process/REVIEW_CONTRACT.md` does not describe the comment's layout.
- Consumers: the callee runs from the process ref the caller pins, so it reaches them on that
  ref with no change of theirs.
