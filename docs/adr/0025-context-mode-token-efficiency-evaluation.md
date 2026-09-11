---
status: "accepted"
date: 2026-09-10
decision-makers: ekolvah
---

# Context Mode is not planned: every estimate of the ceiling is below the threshold

## Context and Problem Statement

The owner's goal is lower effective token spend for agent work in this
repository, and `mksglu/context-mode` was the named hypothesis: an MCP sandbox
that routes large tool payloads, persists session state in SQLite, and restores
it after compaction, advertising 96-98% "context savings". The scope evaluated
is a developer using the tool locally while working on this repository — not
shipping it with the process.

This record carries both stages. Stage A (issue #92) was a static evaluation at
a pinned snapshot with nothing executed: no `npm install` of the candidate ran,
with or without `--ignore-scripts`, and no hook, MCP server, or sandbox was
started. The artefact was obtained with `npm pack`, its published
`dist.integrity` digest was verified before unpacking, and its contents were
read. Stage B (issue #94) measured this repository's own token spend and the
best case the candidate's mechanism could reach, using a standard instrument
rather than a purpose-built reader. Upstream claims and locally observed results
are separated throughout: what follows as evidence was read in the verified
tarball, in documentation that is cited, or measured on this machine's own
session files.

One ruling shapes the outcome and is recorded because it is the owner's, not the
evaluation's. The install path's reach beyond its own package directory is a
**coexistence problem to be designed once a saving is shown**, not a gate that
ends the question before one is measured: the agent-process architecture is
itself expected to change, and a mechanism that demonstrably lowers spend is
worth designing around. What Stage A therefore owes is not a verdict on the
installer but an honest account of what the installer does and of whether the
saving can be measured at all.

## Considered Options

* **Adopt through a separate narrow issue** — requires that no stop condition
  fired, no open condition remains, a rollback path, and a named upgrade owner.
* **Retain for future re-evaluation** — the ceiling whenever a condition that
  cannot be closed statically is still open.
* **Not planned** — any one stop condition ends the evaluation here, with no
  pilot and no follow-up issue.

## Decision Outcome

Chosen: **not planned.** No stop condition fired on the verified artefact — the
candidate is not rejected as unsafe or unusable. It is rejected because the
saving it could produce, measured on this repository's own sessions and taken at
its most generous, does not reach the threshold the owner fixed before any
number was read.

The threshold was **40 %** of measured cost, recorded on 2026-09-10 against the
issue that commissioned this measurement, before the instrument ran (#94). Each
route was measured from its own requests; neither figure is extrapolated from
the other.

The method needs one quantity — how many tokens a character of tool output costs
— and this record neither assumes it nor rests the verdict on a fit. It bounds
it. The tool-output part of a prompt cannot cost more tokens than the whole
prompt, so every request supplies one inequality on that quantity, and the
tightest inequality in a corpus is a value no request in it contradicts.
Charging the mechanism nothing at all for what it adds back, that bound puts the
best case at **31.4 %** on the Claude route and **52.1 %** on the Codex route;
the cheapest plausible round-trip charge — one extra request for every fourth
offloaded payload, so three quarters of all offloads are assumed never to be
read back — brings them to **25.2 %** and **45.0 %**.

The Claude figure settles that route: the bound is what no measurement of it can
exceed, and it is below 40 %. The Codex bound does not settle its route, and
this record says so rather than rounding it away. What a one-sided bound leaves
open is how loose it is, and on Claude that is visible, because the same corpus
answers the same question two further ways. Between two consecutive requests of
one session the prompt grows by the records in between and its billed token
count grows with it, and everything invisible in the transcript — the system
prompt, the tool schemas — sits in both prompts and cancels in the difference.
Least squares over 3 574 such intervals puts tool output at **0.221** tokens per
character; the median of the 393 intervals that added tool output and nothing
else puts it at **0.103**; the bound is 0.484. Those are gross savings of
**14.4 %** and **6.7 %**. The Codex route answered the same way gives 0.136
against its bound of 0.269 — a gross saving of **26.4 %**, or **19.3 %** after
the round-trip charge.

Five estimates across two routes, then, all below the threshold, and one
one-sided bound above it on one route. The decision follows the estimates and
records the bound as exactly what it is.

The reason is visible in the baseline and is not about this candidate. Replayed
context is 60 % of cost on both routes independently — 60.7 % on Claude, 60.1 %
on Codex — but it is replayed because the conversation is long, not because tool
payloads are large. Tool output accounts for a minority of the prefix, and a
mechanism that moves it out of context still pays to re-read everything else on
every turn. The lever that matters for this repository is the length of the
conversation, not the size of individual tool results.

The install path is worth stating plainly all the same, because the reach is
real and the bound is also real: every heavy write into the machine's agent
configuration sits behind a guard that a local install inside this Git working
tree does not pass. That finding is preserved for whatever proposal comes next;
it is not what decided this one.

Nothing was adopted, installed, or configured as an outcome. No runtime pilot is
authorised, and none is proposed: `open-a` (Codex per-hook trust) stays open and
is now moot for this candidate.

## Evaluation record

```text
snapshot-commit: 95b4e08bf07c5e16690d8669643f9d1b825d51be
snapshot-package: context-mode@1.0.169
snapshot-digest: sha512-94JIaFuLjF9SO2BsGTrbGtyT44K95+9OC8BdbaL/UT76xOkanJLfUR5CzmNw+GELXZQqH4nBrKg9wjBnSFkVnQ==
route: the Claude route carries navigation_policy.py through hooks.py PreToolUse alongside agent_policy.py and the ADR 0021 Stop gate; the Codex route carries agent_policy.py and the same Stop gate through codex_hooks.py but imports no navigation or read-budget hint, so it has no incumbent token-economy mechanism and the candidate-versus-incumbent framing does not hold there.
metric: the upstream 96-98% figure is a ratio of raw fixture bytes supplied to bytes returned per isolated tool call, with no billed-token category, no cache-read or cache-write accounting, no round-trip count, and no task-success rate, so it is never restated here as a token or cost saving; the document carrying it is in the upstream repository at the snapshot commit and is not part of the published package. The unit this decision uses instead is a billed-token category measured on this repository's own sessions and converted to input-equivalents, recorded under baseline and ceiling below. Money is deliberately not the unit: no USD figure is quoted, because the instrument's offline price table does not know the models this corpus actually used and the transcripts carry no cost of their own, so any USD number here would be a proxy rather than a measurement.
stop-1: not-fired — the install path does reach outside its own package directory, and it is bounded. In scripts/postinstall.mjs at the verified snapshot every heavy write — healing ~/.claude/settings.json enabledPlugins, rewriting ~/.claude/plugins/installed_plugins.json and its plugin cache, sweeping .mcp.json files judged stale, normalising hook registrations, and rewriting npm .cmd shims — sits inside an isGlobalInstall() guard that returns false whenever npm_config_global is not "true" or a .git directory is found within four levels above the package root, which is precisely the shape of a local install in this working tree; the author's comment gives keeping contributors' local installs from rewriting their HOME registry as its purpose. What runs unconditionally is narrow: one step re-creates a junction or symlink only for paths already registered under the context-mode@context-mode key beneath ~/.claude/plugins/cache/, refusing any target that does not resolve inside that cache root, and a native-binding heal that stays inside the package directory. The condition asks whether the install path can be bounded by available means; a local, non-global install inside this Git working tree bounds it, so it does not fire. The residual write authority over the agent configuration this process owns is carried forward as a coexistence requirement for any runtime pilot, on the owner's ruling that the agent-process architecture will itself change and that a demonstrated saving is worth designing around.
stop-2: not-fired — Codex documents that "if more than one hook source exists, Codex loads all matching hooks. Higher-precedence config layers don't replace lower-precedence hooks", and that project-local hooks load when the project layer is trusted, so a user-level hook set installed under CODEX_HOME would run beside project-level .codex/hooks.json rather than displace the ADR 0021 Stop gate; on the Claude side the candidate's PreToolUse hook is deny- and modify-capable, which makes it a competitor to navigation_policy.py, not a replacement for it, and the Layer 1 deny-list is settings rather than a hook — reachable only through the global-install settings writes recorded under stop-1, which a local install does not perform.
stop-3: not-fired — the one outbound path found in the artefact is hooks/platform-bridge.mjs, which POSTs sanitised hook events only when an operator-created config file supplies a ctxm_-prefixed key and a platform URL; without that file every event returns before a request is built, and no install script writes it. This is a read of a bundled build, which can show a gated path but cannot prove absence of egress at runtime.
licence: Elastic-2.0 restricts only providing the software to third parties as a hosted or managed service, circumventing licence-key functionality, and removing notices; it carries no copyleft, so local development use in this repository is unrestricted and the licence is recorded here as a fact rather than evaluated as a gate.
revives-if: a later issue proposes that the process itself ship, render, or require the package for consumer repositories — that shape, and only that shape, makes the licence a live question; separately, and not as a licence matter, the upstream's hosted Insight dashboard and commercial site are a business-model signal bearing on egress and on maintenance risk.
open-a: open — Codex gates hook execution behind a per-hook trusted_hash in $CODEX_HOME/config.toml computed by a private, unversioned algorithm with no supported non-interactive read path; this repository deliberately refuses to compute or infer it (check_codex_project_trust.py), so only an operator running codex interactively can confirm it.
open-b: closed and measured — both hosts publish per-session billed-token categories on local disk. The Claude route writes one JSONL per session under ~/.claude/projects/<repo-slug>/ whose assistant messages each carry usage with input_tokens, cache_creation_input_tokens, cache_read_input_tokens and output_tokens; the Codex route writes rollout-*.jsonl under ~/.codex/sessions/ whose token_usage_record events carry input_tokens, cached_input_tokens, output_tokens and reasoning_output_tokens at turn and thread level. Three corrections to the Stage A wording, each found while measuring. First, the file count: 94 Claude transcripts belong to this repository, not 53 — 53 sit at the top of the project directory and 41 more are subagent transcripts one level down, which a non-recursive reader silently omits; and of 118 Codex rollouts on disk only 40 have a session_meta cwd inside this repository, because ~/.codex/sessions/ is partitioned by date and not by project. Second, the double-counting rule: the hazard is not the Claude iterations array, which is never longer than one entry in this corpus, but that one API response is written as several transcript lines each repeating the whole usage block — 15,835 records carrying usage for 8,278 distinct (message.id, requestId) pairs, a 1.91x inflation for anyone who sums lines. Third, the Codex categories are nested rather than disjoint: cached_input_tokens <= input_tokens in all 1,053 records with zero violations, so billable fresh input is the difference, unlike the Claude categories which are disjoint and add up.
instrument: ccusage@19.0.3, sha512-10dKbFiRtqYThjl6L3CcAusSp+VDH9IX64S/fg8DJvaJcfADAXwqFHJCjWJXGoI6EAlc9eWThj43XIchWengpw==, MIT, obtained with npm pack and digest-verified before unpacking, run from the unpacked tarball with node and never installed. 19.0.3 is the last release that is readable JavaScript: 20.x is a launcher that spawns a prebuilt native binary from a platform-specific optional dependency, which cannot be read the way this repository read the candidate in Stage A. The package declares no install scripts at all, and the only outbound URL anywhere in its bundle is the LiteLLM price table on raw.githubusercontent.com, which --offline does not request.
cross-check: the instrument's arithmetic was checked against an independent walk of the same files before its numbers were used, and the check corrected this evaluation twice rather than the instrument. It found the 41 subagent transcripts a non-recursive count had missed, and it showed that duplicate transcript lines are not always identical: 544 of 8,279 response groups carry a growing output_tokens snapshot, so keeping the first line undercounts output by 12.6% while keeping the last matches. ccusage keeps the last, so the defect reported upstream as ryoppippi/ccusage#888 does not appear in this corpus. After both corrections the independent totals agree with the instrument to within 0.1% on fresh input, cache creation and cache read; the residual is this measurement's own session still being written.
baseline: 50 Claude sessions and 40 Codex sessions for this repository, measured 2026-09-10. Converted to input-equivalents at published ratios — Anthropic cache write 1.25x, cache read 0.1x, output 5x the model's input price; OpenAI cached input 0.1x, output and reasoning output 8x — the shares are: replayed context 60.4%, output 21.5%, cache creation 10.9%, fresh input 7.2%. The two routes agree independently on the dominant term: 60.7% on Claude, 60.1% on Codex. In raw tokens the same corpus is 96.9% cache read on Claude and 96.8% cached input on Codex, which is why raw tokens are not the unit here. Per-session spread, Claude: median 7.3M raw tokens, p25 0.87M, p75 23.2M, max 206M. Codex: median 7.3M, p25 1.7M, p75 23.6M, max 117M. Models are mixed and priced differently, which is why no single price table was used: Claude Sonnet 5 carried 79.8% of raw tokens and Opus 5 19.4%, with a 0.9% tail of other models. One of the 94 Claude files carries no usage record at all; it is reported as no data, not as zero.
ceiling-method: no tokenizer is involved and nothing is assumed about how tool output tokenizes. Every request bills one whole prompt, and the transcript up to that request says what is in it, split into tool-result characters and everything else. Attributing prompt tokens to tool output needs one quantity, alpha, the tokens per character tool output converts at, and it is bounded rather than chosen: the tool-output part of a prompt cannot cost more than the whole prompt, so each request gives one inequality alpha <= prompt_tokens / tool_chars, and the tightest of them is a bound no request contradicts. The removable share then obeys share <= min(1, alpha_max * tool_chars / prompt_tokens), with no lower bound on prose density needed and no free parameter left; prose, system content and tool schemas sit on the other side of the inequality, where the mechanism cannot reach them either. Two estimators sit below the bound, both from one cancellation: between consecutive requests of a session the prompt grows by the intervening records while everything invisible in the transcript sits in both prompts and cancels in the difference, so the growth in billed tokens measures the growth in characters directly — by least squares over every growing interval, and by the median of the intervals that added one stream only. Every tool-output byte is then treated as free, which is the best case by construction. On the Codex route the fresh portion of a prompt is used only to price it, never to attribute it: input_tokens minus cached_input_tokens is the uncached suffix of the current prompt rather than the content added since the previous one, so apportioning that difference by the intervening records would misplace older content, and this method reads whole prompts against whole prompts instead.
ceiling-claude: 94 transcripts, 93 scored, 8,415 responses, 8,259 tool results, measured 2026-09-11. The bound is alpha <= 0.484 tokens per character over 6,802 eligible prompts, and it is not an outlier: the next tightest inequalities are 0.486 at the 0.1st percentile and 0.517 at the 1st, and the min(1, .) cap binds on 0.02% of prompt cost, so the bound constrains rather than saturates. At the bound, gross 31.4%, net 25.2% at one extra request per four offloaded payloads and 18.9% at one per two. The two estimators below it: 0.221 tokens per character by least squares over 3,574 growing intervals, gross 14.4%; 0.103 as the median of the 393 intervals that added tool output and nothing else, gross 6.7%. For scale the same 393-interval method reads prose at 0.444, and the trivial bound that assumes every prompt is nothing but tool output is 81.4%. 2,596 tool results exceed 2 KB and are worth offloading at all; an extra request costs the full cache_read of the prefix it lands on (mean 101,850 tokens) plus its own output (mean 611), 13,242 input-equivalents in total.
ceiling-codex: 40 rollouts, 4,973 charged requests, 4,612 tool results, measured 2026-09-11. The bound is alpha <= 0.269 over 4,651 eligible prompts, again clustered (0.273 at the 0.1st percentile, 0.303 at the 1st) and again never saturating the cap. At the bound, gross 52.1% and net 45.0% — above the 40% threshold, which is stated here rather than smoothed over: on this route the bound alone does not close the question. The least-squares estimator over 4,646 growing intervals gives 0.136, gross 26.4% and net 19.3%. The pure-interval estimator does not transfer: only 19 intervals on this route add tool output alone, and the same method reads Codex prose at 0.123 tokens per character, far below any plausible rate, which says the rollout's character stream carries content the prompt is not billed for rather than that Codex prose is cheap. That is why the Codex verdict rests on its bound and its regression and not on its pure intervals. 1,708 payloads exceed 2 KB; an extra request costs 16,277 input-equivalents (mean cached prefix 117,725 tokens, mean output 563). The route was measured rather than inferred from the Claude result, because matching aggregate cache shares do not constrain how much of a cached prefix is tool output.
ceiling-boundaries: reading whole prompts removes the need for a cache-break model entirely. A cache miss does not change what a prompt contains, only how it is billed, so it is irrelevant to composition; the earlier revision of this analysis tracked 151 Claude prefix breaks and bracketed three ways of handling them, and none of that arithmetic survives into this one. One event does replace a prompt with something the transcript did not build character by character: a compaction, recorded as compact_boundary on the Claude route and compacted on the Codex route, at which the running composition restarts. 176 such boundaries on Claude and 24 on Codex. The remaining way the accumulated composition could diverge from the real prompt is host-side truncation, and that was checked rather than assumed on the route where it was plausible: of 4,911 consecutive Codex intervals the prompt grows in 4,907 and shrinks in 4, each shrink by roughly a whole prompt and therefore a session restart rather than a dropped item.
decision: not planned — no stop condition fired and the install path is bounded for local use, but every estimate of the best-case ceiling is below the 40% threshold fixed before the numbers were read: 31.4% and 14.4% and 6.7% gross on the Claude route, 52.1% and 26.4% on the Codex route, where the first figure of each pair is a one-sided bound and the rest are measurements. Only the Codex bound is above the threshold, and a bound that loose is not a finding of saving. After the cheapest round-trip charge the measurements are 8.1% and 0.5% on Claude and 19.3% on Codex. The candidate is not adopted, not piloted, and not held open: what limits this repository's spend is the length of the conversation being replayed, not the size of individual tool payloads, and no offloading mechanism addresses that.
rollback: nothing was installed or configured, so there is no machine state to undo. The instrument was run from a digest-verified tarball unpacked under Git-ignored evidence/ and never installed; deleting that directory removes it. The change is this record and its rendered root copy, and reverting the merge removes both.
follow-up: none for this candidate. The baseline is the reusable result: replayed context at 60% of cost on both routes is a measured fact about this repository, and any later proposal aimed at token spend is scored against it with the same instrument and the same conversion, so the next evaluation starts from a number rather than from a vendor's claim.
```

### Consequences

* Good, because the question the owner actually asked — is there a saving — is
  answered by a number against a threshold fixed before the number existed,
  rather than by an unexamined claim on either side.
* Good, because the byte-ratio claim is recorded as a byte ratio and the
  decision uses a billed-token unit instead, so the two are never conflated.
* Good, because the baseline outlives the candidate: replayed context at 60 % of
  cost on both routes is now a measured property of this repository, and the
  next token-spend proposal is scored against it instead of re-deriving it.
* Good, because the instrument is a third-party package under a permissive
  licence, verified the same way the candidate was, so the arithmetic is not
  this repository's to maintain — and it corrected this evaluation twice.
* Bad, because the answer points at a lever this record does not pull:
  conversation length, not payload size, is what costs money here, and nothing
  in this decision shortens a conversation.
* Bad, because the Codex route still has no token-economy mechanism at all, and
  this decision supplies none; that gap is unaddressed, not resolved.
* Good, because the method's one unknown is bounded from the corpus rather than
  assumed or fitted, so the Claude verdict rests on an inequality no request in
  that corpus contradicts rather than on a model of it.
* Bad, because the same bound on the Codex route lands above the threshold, so
  that route is settled by two estimates rather than closed by a bound; the
  record says which, and a reader who refuses estimates should read the Codex
  question as open.
* Bad, because the ceiling is an upper bound on one mechanism's saving and not a
  prediction of any real one: it assumes every offloaded byte becomes free,
  which no implementation achieves, so it can only ever refute a candidate and
  never endorse one.
* Neutral, because this record does not ship: it is publisher-only, so a
  consumer of the process inherits neither the measurement nor the verdict, and
  is free to evaluate the same candidate against its own numbers.
* Neutral, because `open-a` (Codex per-hook trust) stays open and is now moot:
  it was a gate on a pilot that will not happen, and it is not carried forward
  as work.
* Neutral, because the snapshot is pinned: a later release changes what the
  install path does and is a new reading, not a contradiction of this one.

### Confirmation

No automated guard holds this record to its shape, and that is a decision rather
than an omission. For a document the failure mode that matters is an untrue
statement, and a schema check over labelled lines cannot see one: an earlier
draft of this record graded its first stop condition `fired` on an install path
that is in fact gated, and a presence-and-consistency guard passed that draft
without complaint. Do not re-add one — its yield on the one real defect was
zero, and its cost was a permanent constraint on every later re-recording of
this decision.

What confirms a research record is reproducibility, which the record carries
above. For Stage A the snapshot commit, the package version, and the published
digest identify one exact artefact, so any reader can re-fetch the same bytes
and check each claim of evidence against them: `npm pack context-mode@1.0.169`
yields 1,166,887 bytes over 354 files whose computed sha512 equals
`snapshot-digest`.

Stage B is reproducible in the same sense but not in the same way, and the
difference is worth naming. Its input is one machine's session files, which
nobody else has and which grow with every session, so re-running the instrument
on a later corpus yields different numbers — that is the measurement working,
not drifting. What is reproducible is the method: the instrument is pinned by
version and digest under `instrument`, the conversion ratios are stated under
`baseline`, the apportioning rule and the charge-back arithmetic are stated
under `ceiling-method` and the two per-route lines, the inequality that bounds
the method's one unknown is stated with the bound it yields and with the two
estimators that sit below it, and the one event that invalidates an accumulated
prompt composition is given with its counts under `ceiling-boundaries` rather
than left to the reader. A reader who disagrees with a ratio or a
handling can recompute the verdict from the figures printed here.

The scripts that produced Stage B's numbers are deliberately not committed. They
are one-shot analysis over files that exist on one machine, they ship to no
consumer repository, and there is nothing for a later change to regress against;
they live under Git-ignored `evidence/issue-94/` with the JSON they emitted.
This follows the reading already applied to the previous delivery of this
evaluation (#93), and it is stated here rather than left as an unexplained
absence of tests.

This record is publisher-only. It lives in `docs/adr/` beside ADR 0013 rather
than in `.agent-process/docs/adr/`, which is the payload consumers receive,
because everything it decides is local to this repository: the baseline is one
machine's sessions, and the verdict is a purchasing decision about a developer's
local tooling, not a process contract anyone inherits. Rendered into a consumer
it would assert measurements of a repository that was never measured, and could
close an evaluation that repository is entitled to run for itself. The cost of
that placement is stated plainly: the MADR structural guard in
`tests/agent_process/test_adr_records.py` scans only the payload directory, so
this file is outside it — as ADR 0013 already is. Widening that guard is a
separate concern from this decision and is not done here.

## More Information

Working notes, both fetched tarballs, and the raw JSON the instrument emitted
stay under Git-ignored `evidence/`; only the summaries above enter this record.
No absolute path, no repository content, no prompt or transcript text, and no
account metadata is quoted here — the session files were read locally, in place,
and nothing from them was transmitted anywhere.

The Codex hook-layer rule is quoted from the Codex hooks documentation at
`https://learn.chatgpt.com/docs/hooks` (retrieved 2026-09-09). The token
categories the two hosts publish are documented at
`https://code.claude.com/docs/en/monitoring-usage` and
`https://developers.openai.com/codex/config-advanced` (retrieved 2026-09-10);
both hosts can also export the same categories as OpenTelemetry metrics going
forward, which is the instrument to reach for if a future proposal needs
per-tool attribution rather than per-session totals — and it is also what would
close the Codex route's bound, since a per-turn attribution measures directly
what an inequality over whole prompts can only bound. That path was not taken
here: it measures only forward, and the retrospective corpus already settled the
question, so no host configuration was changed. Every other statement of
evidence was read in a package whose digest is recorded above, or measured on
this machine's own session files.
