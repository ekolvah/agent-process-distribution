## Context

See proposal.md — Why. `close_review.py` writes the body file, and the close step posts it with
`gh pr comment --body-file`. `head_review.reviewed` takes the first `Reviewed head SHA:` match.
Line 1 is the job's own marker, so nothing below it can shadow it. `_denial_line` renders each
denial as one line, `- <tool_name>: <json>`. `json.dumps` escapes newlines in the input, so the
line holds a multi-line command on one line. `markdown-it-py` (CommonMark) is already pinned in
`.agent-process/requirements.txt`.

## Goals / Non-Goals

**Goals:** `gh pr comment` accepts every closing comment. Nothing the final message opens can
hide the marker, the denial count or the denials. Every cut is marked.

**Non-Goals:**
- Fencing or sanitising the final message. It stays verbatim Markdown, so the findings summary
  renders. An unclosed tag in it hides only text that comes after it.
- Changing the workflow step, `head_review.py` or the denial line format.

## Decisions

**D1 — Order: marker, count, fenced denials, message.** The body is `Reviewed head SHA: <sha>`,
a blank line, `Permission denials: <n>`, then the denial lines between ```` ``` ```` fences, then
the final message. The block is omitted when there are no denials. In CommonMark, HTML inside a
fenced block is literal text, and a block can close only on a fence line at the start of a line.
Every denial line starts with `- ` and stays on one line, so no denial can close the block. The
count line is not fenced: it renders as plain text before anything the model wrote.
Observed on GitHub's renderer (2026-10-08) with
`gh api markdown -f mode=gfm -f context=ekolvah/agent-process-distribution -F text=@body.md`.
The body was the marker, `Permission denials: 1`, a fence holding
`- Bash: "echo '```'\n<!--"`, then `Summary` and a final `<!--` line. The output was:

```
<p dir="auto">Reviewed head SHA: aaaa…</p>
<p dir="auto">Permission denials: 1</p>
<pre class="notranslate"><code class="notranslate">- Bash: "echo '```'
&lt;!--"
</code></pre>
<p dir="auto">Summary</p>
```

The architect review ran the same check with a message that ends in `<details>`, and the result
was the same. The markdown-it tests (task 1.1) stay as the regression proof.
*Alternative:* keep the message first and escape `<` in it. That changes the verbatim text and
still lets `<details>` fold the denials. Rejected.

**D2 — Per-denial cut.** A denial line longer than 1,000 characters is cut to 1,000 and ends with
` … truncated`. A single denied `Write` therefore cannot use the whole budget and push out the
other denials and the message. The tool name and the start of the command, which tell what was
denied, stay.

**D3 — Body budget.** A body longer than 60,000 characters is cut to 60,000 and gets
`\n\n… truncated` on a line of its own. The script also prints
`::warning::The closing comment of <sha> is cut at 60000 characters` to the job log, because an
unclosed tag in a cut message hides its own trailing marker on the PR. 60,000 Python characters
(code points) stays under GitHub's 65,536-character limit. It is also at most 240,000 UTF-8 bytes,
under the 262,144-byte `mediumblob` the GitHub staff answer names (proposal.md — Why). The body is
cut from the end, so the message is cut first. The marker and the count lines always come before
the cut. The denials block is cut only when more than about 58 denials each reach the D2 cap.
*Alternative:* bound only the denials. A long final message would still exceed the limit.
Rejected. *Alternative:* split the review into several comments. That needs a new reader contract.
Rejected (§VII).

No new script and no new check: the change edits the function that has the defect.

## Risks / Trade-offs

- [GitHub counts characters differently from Python] → the 60,000 budget leaves 5,536 characters
  of margin, and the byte bound holds for any code point. If a body is still rejected,
  `gh pr comment` fails red, as it does today.
- [A body cut inside the fenced block leaves the block unclosed] → CommonMark runs an unclosed
  fence to the end of the document, so `… truncated` renders inside the block and stays visible.
- [`tool_name` is printed raw] → tool names come from the action's tool list, not from PR content.
  A name with a newline could end the block early. D1's test covers only inputs.
- [A cut message loses its tail on the PR] → accepted. The execution file stays on the runner,
  and the action logs only a summary, so the tail is lost. The warning annotation names the cut.
  A cut needs a message of more than 60,000 characters. The final message of the replay that
  `close-review-with-session-summary` recorded was a few paragraphs.

## Migration Plan

The caller pins the callee `@main`, so this PR's own heads run the old close step. The first PR
reviewed after the merge runs the new one. Rollback: revert the PR. The marker line is unchanged,
so closing comments that already exist still count.
