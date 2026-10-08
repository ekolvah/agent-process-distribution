## Why

The git guard and the navigation policy unwrap a shell only when the exact token `-c` follows
it, so a clustered flag hides the inner command from both. Observed on `main` (9079a8d):

```
$ echo '{"tool_input":{"command":"bash -lc \"git push --force origin x\""}}' | python skills/agent-process/scripts/git_guard.py pre-bash; echo "exit=$?"
exit=0
```

The same command under `bash -c` is denied (`test_guarded_command_is_denied_with_the_alternative`).
Root cause: `navigation_policy._stage_verdict` tests `"-c" in tokens[1:]` and takes the token after
`tokens.index("-c", 1)`; a short-option cluster that carries `c` (`-lc`, `-ec`, `-xc`) never
matches, and `git_guard` reaches the same walker through `first_stage_verdict`. The shell itself
runs the inner command in each of these forms, and it takes the first operand after the options,
not the token after `-c` (Git Bash on this machine):

```
$ bash -lc 'echo lc-ran'; sh -ec 'echo ec-ran'; bash -c -e 'echo c-then-e-ran'
lc-ran
ec-ran
c-then-e-ran
$ bash -c -- 'echo dashdash-ran'; bash -c +e 'echo plus-ran'; sh -c -- 'echo sh-dashdash-ran'; bash --rcfile /dev/null -c 'echo rcfile-ran'; bash -o pipefail -c 'echo o-before-ran'
dashdash-ran
plus-ran
sh-dashdash-ran
rcfile-ran
o-before-ran
```

So `bash -c -e "git push --force"` slips through by the same lookup: the walker reads `-e` as the
command string.

The navigation policy's `Bash` route costs more tokens than it saves. Measured over the 440
local Claude Code transcripts of this machine (2026-10-08), it denied 1150 commands. A denial
costs one extra model request over the whole context (median 59k tokens at denial, read from
cache at 0.1) plus the call and its reason. The output it prevents is small: of the shell
navigation commands that did run, `cat` printed a median 2.1k characters, `grep` 0.3k, `ls` 0.1k,
and none printed more than 30k characters. After a denial the agent re-ran a
shell command in 40% of cases and read the whole file with `Read` in 18%; it took a sliced
`Read` in 6%. In input-token equivalents the median net effect per denial is about −8.4k, and
72 of the 982 estimable denials come out positive. A larger output does not reach context
whole: the same transcripts record the Bash tool replacing it with a file path, as in
`Output too large (40.2KB). Full output saved to: …` (a Bash result of 2026-09-26).

## What Changes

- The shell unwrap treats any short-option cluster that contains `c` as the `-c` flag, and takes
  as the command string the first token after it that starts with neither `-` nor `+`.
- The navigation policy's `Bash` route goes: its `hooks/hooks.json` entry, `navigation_hint` and
  its rules, and the `pre-bash` subcommand. Its `Read` route (whole-file reads over the budget)
  stays as it is. Any other subcommand becomes a visible, non-blocking hook error, so a released
  `hooks.json` that still calls `pre-bash` cannot block `Bash` calls in the publisher checkout.
- The shell walker (`first_stage_verdict` and its helpers) moves into `git_guard.py`, its only
  remaining consumer.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: "The plugin ships the git guard" names a shell's `-c`, alone or clustered,
  instead of `sh -c`; "The plugin ships the navigation hooks" ships the `Read` hook only.
- `implementation`: "Shift-left feedback in Claude" denies a whole-file `Read` over the budget,
  not shell navigation.

## Impact

- Edited: `skills/agent-process/scripts/navigation_policy.py` (the `Bash` route removed, the walker
  moved out), `skills/agent-process/scripts/git_guard.py` (the walker moved in),
  `hooks/hooks.json`, `skills/agent-process/SKILL.md` (Claude harness, Install).
- Edited: `tests/publisher/test_git_guard.py` (gaining `test_clustered_shell_flag_is_unwrapped`),
  `tests/publisher/test_navigation_policy.py` (the `Bash` route's tests removed),
  `tests/publisher/test_plugin.py`, `tests/agent_process/test_doc_headers.py` (a comment that
  names the policy's `@dataclass`).
- Edited by archive: `openspec/specs/distribution/spec.md`, `openspec/specs/implementation/spec.md`.
- ADR 0021 cites `pre_bash_response` as an example of a fail-open adapter; it records a past
  decision and stays.
- Consumers: after the release, sessions in adopted repositories no longer get shell navigation
  denials.
