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

## What Changes

- The shell unwrap treats any short-option cluster that contains `c` as the `-c` flag, and takes
  as the command string the first token after it that starts with neither `-` nor `+`.
- The git guard and the navigation policy both get this through the one walker
  (`first_stage_verdict`); no other rule changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: "The plugin ships the git guard" names a shell's `-c`, alone or clustered,
  instead of `sh -c`.
- `implementation`: "Shift-left feedback in Claude" — the shell-navigation scenario covers a stage
  inside a shell's `-c` command string, its flag alone or clustered.

## Impact

- Edited: `skills/agent-process/scripts/navigation_policy.py` (`_stage_verdict`).
- Edited: `tests/publisher/test_git_guard.py` and `tests/publisher/test_navigation_policy.py`,
  each gaining `test_clustered_shell_flag_is_unwrapped`.
- Edited by archive: `openspec/specs/distribution/spec.md`, `openspec/specs/implementation/spec.md`.
- No ADR or doc mentions the shell unwrap outside the code comment and the spec; nothing else to
  update.
