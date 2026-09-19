## Context

See proposal.md — Why. Current state that shapes the approach:

- `wait_for_pr.py`: `run_gh` (raises on rc ≠ 0 or a `None` capture), `_json`, the poll of
  `gh pr view --json statusCheckRollup,headRefOid,url` with its own sorting of the rollup
  (`_concluded`, `_failed`, `_GREEN`, `_name`, `_url`), the settling guard and the head
  comparison, `_unresolved_threads` (GraphQL, paged, returns `(headRefOid, threads)`);
  seams `gh`, `clock`, `sleep`, `timeout`; `main` maps `RuntimeError` to exit 2.
- `test_pending_review` drives it with `_Sequence` (one `_rollup` per `gh pr view`, one
  `_threads` payload per GraphQL call) and asserts the settling (`gh.polls == 4`) and the
  head restarts (`def456`); `test_none_capture_is_an_error` covers `("wait_for_pr", "run_gh")`.
- The `tasks` rule and `agent-process.md` step 3 name `wait_for_pr.py <PR>`.

## Goals / Non-Goals

**Goals:**
- No sorting of the rollup of our own where `gh pr checks` sorts: the bucket and the
  latest-run-per-name are gh's; the script keeps what gh does not do — the retry on the
  empty rollup, the deadline, the threads.
- One seam for `gh` (a callable returning `subprocess.CompletedProcess[str]`), never network.
- A `gh` failure is visible as exit 2 with its stderr, never a verdict (§IV); a timeout
  names what was still awaited.

**Non-Goals:**
- Required-check contexts (`--required` needs admin; on record in v2-1a).
- `check_red` (`v2-2d`), Group 0 scripts (`v2-2f-start-change`), the `tasks` rule.

## Decisions

### D1 `wait_for_pr.py` reads `gh pr checks --json` until nothing is pending

```
deadline = clock() + timeout; last = None
loop:
  result = gh(["gh","pr","checks",PR,"--json","name,bucket,link"])
  rc ≠ 0 and "no checks reported" in stderr → checks = None          # empty rollup
  rc ≠ 0 otherwise                          → RuntimeError(stderr)   # main: exit 2
  else checks = json(stdout); pending = names with bucket == "pending"
  if checks and not pending: break
  waiting = ", ".join(pending) or "no checks reported"
  now = clock(); if now >= deadline: print "timeout after N s: <waiting>"; return 3
  if waiting != last: print "waiting: <waiting>"; last = waiting     # one line per state, not per poll
  sleep(min(30, deadline - now))   # the remainder last: the timeout is elapsed time (PR 147, round 1)
url, threads = _unresolved_threads(gh, PR)        # query asks `url` where it asked `headRefOid`
failed = bucket not in {"pass", "skipping"}       # fail and cancel both block the merge
print failed: <name> <link> / unresolved: … / clean: N checks green, no unresolved threads (<url>)
return 1 if failed or threads else 0
```

*Why `--json` and not `--watch`.* The loop exists for the empty rollup: the watch exits 1 on
it (line 303 via 184–186, and inside its loop 228–237 when a push moves the head) exactly as
on a failed check (248–249), refuses `--json` (line 81), and leaves on `Pending == 0`
(line 218) — so a script around the watch still loops, re-reads `--json` after every watch
and sleeps 30 s between rounds. That loop, on `--json` alone, is the same watcher at the
same cadence with one `gh` call per round, one exit-code meaning, no child timeout, no
captured table, and a timeout line that names the pending checks. What `gh pr checks`
gives that `gh pr view` did not: the bucket (aggregate.go 72–88) and the latest run per
name (96–120) — the sorting the script copied. The `--json` read's exit code is
unambiguous: 0 with failed or pending checks (the export returns first, lines 189–191),
non-zero only for the empty rollup (line 303, distinguished by its text) or an error
outside the checks — the latter is `RuntimeError` → exit 2, the meaning `run_gh` gives
every `gh` failure today, not exit 1 (a verdict on the PR).

*Why the retry and the deadline.* Right after a push the rollup is empty for seconds, then
the runs attach (v2-1a); every read is of the current head (`commits(last: 1)`), so a
push during the wait is followed by the next read. The deadline is checked before every
sleep and the last sleep is the remainder, so a rollup that never fills (Actions disabled,
a workflow file that does not parse) ends in exit 3 with `no checks reported` at the
deadline — never in an endless loop, never before `timeout` seconds elapsed (the first
draft returned when another whole interval did not fit: `--timeout 31` at 30 s, `--timeout
10` at once — PR 147, round 1).

*Failure modes of the new input (`gh pr checks --json`), and what the script does with
each* (issue 146):

| Mode | Where it shows | The script |
| --- | --- | --- |
| Empty rollup (after a push, at the start or mid-wait) | rc 1, stderr `no checks reported on the '<branch>' branch` | `waiting: no checks reported` once, sleeps 30 s, reads again |
| A check queued, running or STALE | rc 0, a `pending` bucket | `waiting: <names>` once per change of the set, sleeps, reads again |
| A check failed or was cancelled | rc 0, `fail`/`cancel` | `failed: <name> <link>`, exit 1 |
| A `gh run rerun` | the rollup entry is replaced (observed on PR 137): `pending` | waited on |
| `gh` cannot answer (auth, network, rate limit, `no commit found` line 287) | rc ≠ 0, stderr without `no checks reported` | `RuntimeError` → exit 2 with the stderr |
| The wording of line 303 changes in a future `gh` | rc ≠ 0, text unmatched | exit 2 with the stderr — visible, never a silent pass |
| Fields renamed in a future `gh` | rc 0, `KeyError` on `name`/`bucket` | the traceback — visible; `link` is read with a default |
| `None` capture | `run_gh` | `RuntimeError("… broken capture …")` as today |

*What the script stops proving.* The settling guard proved that the set of checks did not
grow between two polls 30 s apart; the head comparison proved that the threads were read
on the head the checks settled on. Neither is proved now: a check attaching after the last
read (the observed gap between the runs of one push is seconds, v2-1a) or a push after it
is not seen by this run. What covers it: a required context that attaches late or a new
head blocks the merge on the platform — the person merges — and the next `wait_for_pr` of
the loop (after every push, by the `tasks` rule) sees it. The cost is one round ending
early, never a silent green.

*Alternatives.* `gh pr checks --watch` — above. `--fail-fast` — exits the watch on the
first failure with the rest pending; the run wants all of them. `--required` — needs
admin. Keep the `gh pr view` poll — the copy this change removes. `gh run watch` — per
run, not per PR. Keep the settling (a second read 30 s after a clean one) — 30 s on every
run for a gap of seconds, and no proof for a gap longer than 30 s either.

*Seams.* `gh(cmd) -> subprocess.CompletedProcess[str]`: `run_gh` no longer raises on
rc ≠ 0 (the read needs rc and stderr), keeps the `None`-capture `RuntimeError`; `_json`
raises on rc ≠ 0 for the threads calls. `clock`, `sleep`, `timeout` as today.

### D2 Tests follow the seams, one test per scenario

- `test_pending_review`: `_Sequence` answers `gh pr checks … --json` with the next of a list
  of `(rc, stdout, stderr)` from `_checks(*(name, bucket))` (stdout a JSON list of `{name,
  bucket, link}`), `gh repo view` and the GraphQL threads as today (`url` in place of
  `headRefOid`), counting the reads. Cases: `pending` then `fail` → 1, `failed:
  agent-review` in out, two reads; `cancel` → 1; threads → 1 and `docs/a.md`; all `pass` → 0
  and `clean:` with the URL; `pending` on every read with `timeout=120` (the fake `sleep`
  advances the fake `clock`) → 3 with `timeout` and `agent-review` in out; a read `rc=1`
  with `HTTP 401` → `RuntimeError` matching `401`. Deleted: the settling and head cases,
  `_rollup`.
- `test_empty_rollup_after_push`: the read `rc=1` with `no checks reported on the 'x'
  branch` then `pass` → 0, one `sleep(30)`, two reads; the same on every read with
  `timeout=120` → 3 and `no checks` in out.
- `test_none_capture_is_an_error` keeps `("wait_for_pr", "run_gh")` unchanged.

## Risks / Trade-offs

- [The `pending` bucket hides which state (QUEUED, STALE, …) a check is in] → the timeout
  line names the check; `gh pr checks <PR>` by hand shows its state.
- [A late attachment or a push after the last read] → the next `wait_for_pr` of the loop
  or the platform's required context; see "What the script stops proving".
- [The first live run of the rewritten script is this change's own PR] → the old script is
  on `main` until the merge; a failure is visible in the PR's review loop, on a branch.

## Migration Plan

One PR. Rollback is the revert of the PR: no data, no platform state.
