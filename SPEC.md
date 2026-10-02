# SPEC — VERA, Increment 2 (thin loop on TreeHFD)

## Overview

Current-increment features only, in build order. Each `##` below becomes a
tracked feature (`scripts/features-init.sh`); do not add `###` headings.
Source: [docs/07-increments.md](docs/07-increments.md) Increment 2; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.7, with v0.8 proposed in the
first feature; requirements due: FND-F-03, RSH-F-01, RSH-F-02, RSH-F-03,
RSH-F-05, RSH-F-06, RSH-F-07, RSH-P-01, AUD-F-03, AUD-F-04, AUD-F-09
([docs/02-requirements.md](docs/02-requirements.md)); trades to decide: T4,
T5 (citation checking), T6, T7, and the generator model(s)
([docs/04-trade-studies.md](docs/04-trade-studies.md)). Rewrite this file at
each increment review. The Increment 1 SPEC is in git history.

The product, crude but end to end, on one CPU-scale problem: **TreeHFD**
(Benard, NeurIPS 2025, arXiv 2510.24815, code `ThalesGroup/treehfd`; fallback:
credal ambiguity sets, see docs/reviews/incr-0.md). Problem spec + output
guidance + `Budget` → reproduce the baseline on a subset → generate and screen
a few ideas → run the best on the subset → write-up → final gate (a minimal
P1). Every stage transition is a P2 `Verdict` from a component other than the
producer. Direction B changes nothing here: this increment builds the
experiment engine that Increments 3-5 put a topic front end and an app on.

Who does what: Claude Code builds and runs short work; Chris launches long
runs from his terminal, approves the human gates, and decides T4, T5, T6, T7
and the generator with the evidence.

Rules carried from the Increment 1 review:

- **Spend.** Every model call goes through a `Budget` that raises before a
  limit is crossed, inside the $20/month ceiling (ConOps §4, confirmed for
  this increment). Caps confirmed by Chris, 2026-10-01 (with the 2-hour wall
  limit for the complete run and the 90% audit bar below): $3
  for debugging and smoke runs, $4 for the T7 and generator measurement runs,
  $1 for reference-judge calls in the gate re-test, $3 for the complete run
  (about 2x the $1.25 mixed-option estimate; R10's trigger is $10); $11 for
  the increment, each calendar month inside $20. Jev is billed separately and
  counts. The OpenRouter key keeps its credit limit.
- **One ledger file per run**, `data/ledger/run_<run_id>.jsonl`, never
  deleted, truncated or overwritten (the Increment 1 smoke-ledger defect).
  Named result ledgers are committed; the rest are git-ignored.
- **The cheap judge path is one shared function** (T1: Jev → GLM-5.3 Flash at
  0.7, `loop.*` questions straight to GLM). Nothing in the loop builds its own
  router.
- **No peeking.** The loop's problem spec contains the TreeHFD paper and
  repository only, never ScientistTwo's paper on it (ECTS-HFD) or its numbers;
  they are the later comparison (RSH-P-02, Increment 4). The target and
  tolerance for "baseline reproduced" are written in docs/results/ before the
  first baseline run.
- **Independence (docs/06 §5).** Seeded-fault sets and judge re-test sets are
  split dev/test with the test hash recorded before any result on it is seen.
  Thresholds and checks are tuned on dev only.
- **Same model grading itself.** The producer/judge rule is about components,
  but a model grading its own family's work correlates errors. Every
  `StageResult` records the generator model and the judge backend; the review
  reports where they coincide (for example GLM generating and GLM judging
  `loop.*`).
- **Secrets.** No maintainer key in any artifact (APP-C-01) from now on, and
  none reaches the sandbox. `tests/test_no_secrets.py` stays in the suite.
- **Long runs** are resumable and launched from Chris's terminal, or split
  into segments under 10 minutes (the agent's background limit).
- **Dogfood.** Overhead hours are logged at the end of every session
  (`bash scripts/dogfood.sh overhead <hours>`); gate blocks are labelled.
  Missed in Increments 0 and 1, so it is checked at the review.

Gate DAG proposed for `.meridian/gates.yaml` after `incr2_scoped`:

```text
incr1_review ─► incr2_scoped ─┬─► run_core_ready ──────┬─► stages_ready ──┐
                (human)       │   (automated)          │   (automated)    │
                              └─► design_trades_decided┼─► sandbox_ready ─┤
                                  (human: T4, T5)      │   (automated)    ├─► trades_decided_2 ─► loop_run ─► judge_retest ─► incr2_review
                                                       └─► audit_ready ───┘   (human: T6, T7,    (automated)   (automated)     (human + Evaluator)
                                                           (automated)         generator)
```

## Run foundation: spec, ledger, cheap path, budget

`vera/loop/` (new) and `vera/judge/`. The pieces every stage uses, built and
tested offline before any stage exists:

- **`RunSpec`** (RSH-F-01): the problem (parent paper id, repository URL and
  pinned commit, metric, datasets and subset), output guidance (format,
  length, emphasis, constraints), the `Budget`, and the model chosen per stage.
  Propose it in docs/03 first with `LedgerRecord.provider` (the serving
  provider OpenRouter reports, so per-provider cost and quality can be
  separated; Increment 1 open item), as v0.8 with a changelog line, then
  implement.
- **Per-run ledger** `data/ledger/run_<run_id>.jsonl` under the rule above;
  starting a run whose ledger exists is an error unless it is a resume.
- **Cheap path function** `vera.judge.cheap_path(...)` returning the T1
  path: Jev → GLM at 0.7, with every `loop.*` question id (the set
  `vera.loop.LOOP_QUESTION_IDS`) sent straight to GLM, never to Jev, writing
  to the run's ledger and `Budget`.
- **Budget stop** (RSH-P-01, RSH-F-06): on exhaustion the run stops, writes a
  best-so-far report naming the stop reason and the stage reached, and
  returns; it never overshoots.

**Acceptance:** `test_RSH_F_01_…` (spec round-trips, invalid specs rejected);
`test_RSH_P_01_…` (injected cost forces exhaustion at every stage boundary
and inside a stage; spend never exceeds `max_usd`, using the real `Budget`
and fake backends); `test_RSH_F_06_…` (best-so-far report with stop reason
and stage); tests that a second start over an existing run ledger raises,
that `loop.*` ids route to GLM, that `provider` is recorded; docs/03 is v0.8
and `check_schema_version.py` passes.
**Gate:** `run_core_ready`.

## Decisions before building: T4 sandbox and T5 bibliographic source

Two decisions that block later features, each with a short measurement:

- **T4 (sandbox).** Try local Docker (network off, WSL2; GROBID already runs
  there) for TreeHFD's baseline script and for a hostile snippet; hosted
  sandboxes only if Docker fails a criterion. Note the Increment 5 link: the
  choice fixes where experiments run for a hosted app (T8).
- **T5 (bibliographic source).** Look up the reference lists already
  extracted from the 10 T3 papers (GROBID output) against Crossref, arXiv,
  OpenAlex and Semantic Scholar: coverage of ML venues and preprints, hit
  rate by title + year, rate limits, terms, and a title search for the
  Increment 3 literature stage. Free tiers only; polite rate limits.

Each is written in docs/04 with **Scores:**, **Decision:** and **Reverse
if:**. Chris decides.

**Acceptance:** `tools/checks/check_trade_decided.py T4` and `… T5` pass.
**Gate:** `design_trades_decided` (human approval).

## Sandbox for generated code (T4, FND-F-03)

`vera/sandbox/`: the only place agent-written or third-party code executes,
through one function that takes a script, a working directory and limits and
returns exit code, output and files. The image is built in advance from the
pinned TreeHFD commit and its dependencies (xgboost, and what the repository
needs), the repository's licence is recorded, and the container runs with no
network, a read-only root, a writable working directory only, CPU, memory and
wall-clock limits, and an environment with no API keys. A check forbids
`exec`, `eval` and `subprocess` outside `vera/sandbox/` (FND-F-03, the
vendor-imports pattern).

**Acceptance:** `test_FND_F_03_…` run real containers: a snippet cannot open
a network connection or resolve a name, cannot read the repository's `.env`
or any path outside its working directory, cannot write outside it, is killed
at the wall limit and the memory limit, and sees no key-like environment
variable; per-run network grant is off by default and recorded when on;
`tools/checks/check_sandbox_use.py` passes; a TreeHFD baseline smoke script
(the README's simulated-data example without plotting,
`docker/sandbox-treehfd/baseline_smoke.py`) runs in the sandbox and prints its
metric; the gate runs these tests with Docker required, not skipped.
**Gate:** `sandbox_ready`.

## Baseline and idea stages

`vera/loop/` stages as LangGraph nodes with VERA's gate helpers and the
SQLite checkpointer (synchronous). Each stage's artifact is produced by one
component and gated by the shared judge path; stage results are `StageResult`
records.

1. **Baseline reproduction** (RSH-F-02): the loop writes and runs, in the
   sandbox, a script that runs TreeHFD on the subset and reports the metric
   (decomposition residual / reconstruction error; subset: the parent's small
   public datasets, n and trees reduced as set in the `RunSpec`). Gate
   `loop.baseline_reproduced`: Boolean, "do these numbers match the
   reference within the recorded tolerance?". No later stage starts without
   an accepted baseline.
2. **Ideas** (a few, default 5): generate, then screen with `loop.idea_worth_run`
   (Score) on the baseline result and the idea text; the best go to the subset.
3. **Idea run on the subset:** each selected idea implemented and run in the
   sandbox on the same subset; gates `loop.beats_baseline` (Boolean) and
   `loop.best_idea` (Choice).
4. **Programmatic shadow label.** Wherever the answer is computable from the
   run's own table (beats baseline, best idea), the node records the
   computed answer next to the verdict, never as the gate. This costs
   nothing and gives the real-decision re-test its labels.

If the baseline cannot be reproduced within one time-boxed session of effort,
stop and tell Chris: the fallback (credal ambiguity sets) has an unresolved
compute question (docs/reviews/incr-0.md) and switching is his call.

**Acceptance:** `test_RSH_F_02_…` (idea stages blocked until the baseline gate
accepts; a rejected baseline stops the run with a reason);
`test_RSH_F_03_…` (every transition is gated by a verdict whose `judge_id`
differs from the stage's producer; a self-issued gate raises); a graph test
with fake backends and a fake sandbox that runs to the idea stage, is killed
and resumed without repeating a completed node or its ledger records (the
FND-F-02 pattern on the real graph); one live smoke run of stages 1-3 on the
smallest dataset under the debugging cap, with every call in the run ledger.
**Gate:** `stages_ready`.

## Write-up and output guidance

The write-up stage turns the run's logs and tables into a paper-shaped
document following the run's output guidance (RSH-F-07): format, length,
emphasis and constraints from the `RunSpec`. For this increment the shape is
crude (abstract, method, results with the baseline-versus-idea table,
limitations, references); the full paper structure is Increment 4
(RSH-F-11). Numbers come from `results.json` written by the sandboxed runs;
references come from sources the loop actually retrieved, not from model
memory. The stage checks guidance conformance (length, required sections,
constraints) with a `loop.guidance_met` verdict plus deterministic checks.

**Acceptance:** `test_RSH_F_07_…`: a write-up that violates each guidance
constraint (too long, missing section, forbidden content) is rejected by the
final check, and one that meets them passes; the write-up stage on recorded
fixture logs produces a document whose every table number appears in the
logs.
**Gate:** `stages_ready` (same gate; this feature closes it).

## Minimal P1: the final gate

`vera/audit/`: citation existence and numeric consistency of the write-up
against the run's own logs, with evidence links, built on the shared judge
path and the T5 source.

- **Citations** (AUD-F-03): the write-up cites only records the loop
  retrieved, so each reference is first matched exactly against the run's
  retrieval log, then looked up in the T5 sources (Crossref and arXiv; OpenAlex
  when a key is set) by title with the year as a hint. A reference that is in
  neither is a `fail` finding with the query and results recorded. An exact
  title with a different year (preprint against journal) is a match with an
  `info` finding. This rule is for the loop's own text: T5 measured 74.5% to
  81.2% coverage of real references, so on other people's papers (Increment 6)
  "not found" can only mean "unverified".
- **Numbers** (AUD-F-04): numeric claims are extracted from the write-up
  as written, not from the writer's own markup, and matched to
  `results.json` and the run ledger within rounding; an unmatched number in a
  results claim is a `fail`, in other prose a `warn`.
- **Evidence** (AUD-F-09): every finding links to its evidence (quote
  location, source record, log line) in the `AuditReport`.
- **Blocking** (RSH-F-05): a run whose audit has any `fail` is never reported
  as a success; the report states the failing findings.

**Seeded faults:** plant fabricated citations and numeric mismatches into
recorded write-ups (docs/06 §1; manifest in `data/seeded/`), split dev/test
with the test hash recorded first.

**Acceptance:** `test_AUD_F_03_…` and `test_AUD_F_04_…` on seeded write-ups:
on the test split at least 90% of planted faults are flagged (the
AUD-P-01 starting value, not yet a target; Increment 6 sets it) and the
unseeded control write-ups raise no `fail`; `test_AUD_F_09_…` (every finding
has at least one evidence entry with a reference); `test_RSH_F_05_…` (an
audit `fail` blocks success and the report says why). Fixture write-ups come
from `stages_ready` smoke output, not hand-written ones.
**Gate:** `audit_ready`.

## Measurement runs: T7, generator, T6

Decide how the loop holds its context and which models generate, from runs
instead of preference. Fixed inputs: the same recorded baseline result and
the same problem spec for every arm.

- **T7:** (a) plain LangGraph state with summarisation against (b) the
  prompt-as-variable pattern from prime-agent inside VERA's own nodes (papers,
  logs and code held outside the prompt; recursive sub-calls bounded by the
  `Budget`). Two repeats per arm on the idea and write-up stages. Report
  input tokens, cost, gate pass rate, audit result, and whether the idea's
  result beats the baseline. N is tiny, so the result is directional and the
  decision records that.
- **Generator:** GLM-5.3 Flash throughout, GLM for code and ideas with
  Sonnet 5.5 for the write-up, and one other cheap candidate from ConOps §4
  (for example MiMo-V2.6-Pro or DeepSeek V4.x Flash), using billed cost per
  call (prices vary by provider; keep `provider.sort = price`) and the
  recorded generator/judge overlap. Sonnet 5.5 throughout is the quality
  reference only if the $4 cap allows.
- **T6:** decide or close with a reason; the default is "ledger plus
  checkpoints are enough", reopened only if the measurement runs could not be
  debugged from them.

Docs/04 gets **Scores:**, **Decision:** and **Reverse if:** for T7, the
generator choice (as a new trade, T9) and T6; T2's reverse-if (2) is
answered by the T7 result.

**Acceptance:** `tools/checks/check_trade_decided.py T6`, `… T7` and `… T9`
pass; the measured spend of these runs is ≤ $4.00 from the run ledgers
(`check_ledger.py`); per-stage cost per arm is in docs/04.
**Gate:** `trades_decided_2` (human approval).

## Complete run

One end-to-end run from Chris's terminal with the decided configuration
(T7, generator, cheap path), a $3.00 budget and a wall limit set in the
`RunSpec` (proposed 2 hours): baseline → ideas → idea run → write-up → final
gate. Output: the run's ledger with per-stage cost, the checkpoint database,
the write-up, `results.json`, and the `AuditReport` on its own paper. A
run that ends in budget exhaustion or a failed audit is a valid result if it
reports its stop reason honestly, but the gate wants a complete run, so a
second attempt is allowed inside the increment cap.

**Acceptance:** `tools/checks/check_run.py`: the run ledger exists and is
append-only complete (every `StageResult` has a ledger span; no record without
a run id), total ≤ the run's `Budget`, every stage transition has a verdict
from a different component, the audit report exists and its overall status is
recorded (green, amber or red, stated, not hidden), and per-stage cost is
tabulated in `data/results/run_<run_id>.json`.
**Gate:** `loop_run`.

## Judge re-test on the loop's real gate decisions

T1's first reverse-if: the Increment 1 benchmark was near ceiling on two of
three tasks and its targets were set after the test results were seen. The
complete run, the smoke runs and the measurement runs produced real `loop.*`
gate states. Build a new test set from them: every `loop.*` state with a
programmatic shadow label (beats baseline, best idea), plus near-tie and
perturbed copies of the run's own tables generated by the Increment 1
generators to reach at least 100 items. Split dev/test by run, hash the test
split before any backend sees it, then replay the decided path (Jev → GLM,
`loop.*` to GLM) and Sonnet 5.5 over it, three repeats for the reference,
within the $1 cap.

Report agreement with labels and with the reference, ECE, flip rate, cost and
latency, with confidence intervals this time (the Increment 1 benchmark had
none). `loop.idea_worth_run` (Score) has no computable label and is reported
separately, not in agreement.

**Acceptance:** `tools/checks/check_retest.py`: items and test hash recorded,
every `loop.*` verdict in the run ledgers accounted for, results with
intervals, spend within the cap; the review states whether T1's reverse-if (1)
fired (decided path below 95% agreement with the reference). A failure does
not block the gate; it opens T1 again in the review.
**Gate:** `judge_retest`.

## Increment 2 review

Write `docs/reviews/incr-2.md` against the docs/07 exit criteria: one
complete run inside its budget with a per-stage cost ledger and an audit
report on its own paper, and an honest write-up of what the crude loop got
right and wrong. Also: measured cost per run against the Increment 1
estimate (about $0.5 to $5.7 by option) and R10; T4, T5, T6, T7 and generator
decisions with their evidence; the re-test result and T1's reverse-if (1);
the same-model-judging overlap; the seeded-fault detection numbers; the
result against ScientistTwo's ECTS-HFD on TreeHFD as one data point (the
formal comparison is Increment 4); spend against caps; dogfood overhead hours
per session; and what changes in the Increment 3 SPEC (topic front end and
literature stage, using T5 and T7 as decided). Open items from the
Increment 1 review are closed or restated: provider field, T1 router
function, T6, the 4 parents with unknown code, corpus likely success-only,
the T3 escalation run not spot-checked, `tmp/`.

**Acceptance:** `tools/checks/check_dogfood.py` finds an overhead entry for
each calendar day on which a gate passed in this increment; the review passes
the independent Evaluator (`run-evaluator.sh`), fresh per round, with every
verdict kept.
**Gate:** `incr2_review`.
