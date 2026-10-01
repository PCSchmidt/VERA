# Increment 1 review — P2 minimum viable judge

Date: 2026-10-01 · Reviewer: Chris (decisions and human gates) · Author: Claude Code
Gates passed: `incr1_scoped`, `judge_core_ready`, `backends_live`,
`graph_ready`, `benchmark_labeled`, `benchmark_run`, `trades_decided_1`.
This review is the evidence for `incr1_review`.

## Outcome

All three docs/07 exit criteria are met: the first cost-vs-agreement
threshold curve exists, JDG-P-01..03 are set from data, and one Increment 2
loop run is estimated from measured costs at well under the $20 ceiling,
which Chris confirmed for Increment 2.
T1 and T2 are decided. During the increment Chris also re-directed the
product (direction B: topic in, paper-shaped write-up out, through an app
with bring-your-own-key); docs/01, 02, 04, 05, 07, CONTRACT and README were
revised for it. Increment 2 (thin loop on TreeHFD) is confirmed unchanged.

## Exit criteria

| Criterion (docs/07) | Status | Evidence |
|---|---|---|
| First cost-vs-agreement threshold curve | **Met** | `docs/figures/threshold_curve.png`, `data/benchmark/results.json` (5 cheap backends x 21 thresholds against Sonnet 5.5); gate `benchmark_run` passed (`check_benchmark_results.py`: test hash unchanged, run ledgers $1.61 <= $8.00). |
| JDG-P targets set from data | **Met, with a caveat** | docs/02 0.3: JDG-P-01 >= 97% agreement at <= 5% of reference cost; JDG-P-02 p50 <= 0.5 s, p95 <= 1.5 s; JDG-P-03 flip rate <= 2%. Caveat: set from the same test split they are measured on (see Benchmark limits). |
| Measured per-call costs used to estimate one loop run against the ceiling | **Met** | Loop-run estimate below: about $0.25-1 per run with a flash-tier generator, about $5 with Sonnet 5.5 generating everything; $20 kept. |

SPEC features (each its own acceptance test): ledger and metered calls
(FND-F-01, FND-C-01), parsing (JDG-F-01), router (JDG-F-02/03), backends
(JDG-F-04, smoke run), graph helpers and checkpoint/resume (JDG-F-05,
FND-F-02), benchmark items, harness and metrics (JDG-F-06). 208 tests pass,
ruff clean; `check_traceability.py`: all 7 test-verified requirements due in
Increment 1 have tests.

## What was built

- **Ledger** (`vera/ledger/`): every model call goes through `metered_call`,
  which checks the `Budget` before the call and records cost, tokens,
  latency, trace id and errors, also for failed calls.
- **Judge** (`vera/judge/`): prompts and parsing for Choice, Score and
  Boolean questions; confidence from token log-probabilities or
  self-report, recorded as which; malformed replies become zero-confidence
  verdicts that escalate. **Router**: cheapest first, escalation by
  threshold (call > question id > question type > default).
- **Backends** (`vera/backends/`): OpenRouter chat models, TypeSafe Jev
  (direct API) and a local model through Ollama (Gemma 4 12B on the RTX
  A4500); candidates in `vera/bench/candidates.py`.
- **Graph** (`vera/graph/`): LangGraph judge nodes that refuse to grade
  their producer's material, routing that fails closed, SQLite
  checkpointing with synchronous writes; a demo graph routing on the loop's
  "beats baseline?" verdict.
- **Benchmark** (`vera/bench/`): 179 items labelled by construction, a
  resumable harness, metrics and an offline router replay.

## Benchmark

**Items** (`data/benchmark/`, schemas 0.7 `BenchmarkItem`): 179 items in
three tasks, each label computed from the material the judge sees:
loop-gate questions on generated TreeHFD-style result tables (59; Boolean,
Choice, Score; ties and near-ties), numeric claims about Docling tables from
the 10 T3 papers (60; exact or perturbed by digit change, decimal shift or
cell swap), and citation presence in GROBID reference lists from all 86
papers (60; near-miss titles, one-word swaps, unrelated titles). Split by
source unit (table or paper), 64 dev : 115 test; test SHA-256
`0ae2c8d6f11a…` recorded before any backend saw an item. `items.jsonl` is
not committed (it quotes corpus text); `scripts/build_benchmark.py`
rebuilds it from the seed and the check recomputes the hash.

**Label check:** 9 items (3 per task) drawn with seed 20261002; Chris
judged all 9 from the sheet material only: 9/9 correct
(`data/benchmark/label_check.csv`, gate `benchmark_labeled`).

**Run** (2026-10-01): test split, cheap backends 10 repeats, Sonnet 5.5
reference 3 repeats; 6,095 verdicts, no failed calls, $1.61.

| Backend | Agreement | Loop gate | ECE | Flip rate | Cost/item | vs Sonnet | p50 / p95 |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 (reference) | 1.000 | 1.000 | 0.019 | 0.0% | $0.00367 | 100% | 1.26 / 2.13 s |
| GLM-5.3 Flash | 0.998 | 1.000 | 0.006 | 0.9% | $0.000129 | 3.5% | 1.95 / 8.43 s |
| Jev | 0.970 | 0.913 | 0.008 | 1.7% | $0.000047 | 1.3% | 0.19 / 0.36 s |
| DeepSeek V4.1 Flash | 0.963 | 0.890 | 0.044 | 6.1% | $0.000054 | 1.5% | 0.37 / 1.42 s |
| MiMo-V2.6-Flash | 0.915 | 0.782 | 0.072 | 7.8% | $0.000069 | 1.9% | 3.25 / 11.26 s |
| Gemma 4 12B (local) | 0.886 | 0.667 | 0.114 | 1.7% | $0 | 0% | 1.70 / 3.80 s |

Router replay (offline, recorded verdicts): Jev escalating to Sonnet at the
default threshold 0.7 gives 0.976 at 2.8% of Sonnet's cost; Jev escalating
to GLM gives 0.976 at 1.3%, p50 0.19 s. Jev's errors are 4 loop-gate items
it gets wrong on nearly every repeat with high confidence, so escalation
plateaus near 0.98. Gemma reports confidence 1.0 on every verdict, so its
errors never escalate.

**Benchmark limits.** (1) Numeric and citation items are near ceiling for
most backends; only the loop-gate task (38 test items) separates them. (2)
Sonnet matched every label, so agreement with the reference adds nothing
to agreement with labels on this set. (3) 115 items: a 1-2 point gap is one
or two items; no confidence intervals were computed. (4) The JDG-P targets
were set from this split, so they describe it rather than predict new
data; the T1 reverse-if conditions call for a harder test on the Increment
2 loop's real gate decisions. (5) The label check covered 9 of 179 items.

## Decisions

- **T1** (Chris): cheap path Jev escalating to GLM-5.3 Flash, threshold
  0.7; loop-gate questions straight to GLM; Sonnet 5.5 as benchmark
  reference only; Gemma kept as the offline fallback (R4); DeepSeek and
  MiMo dropped. docs/04 T1 has the scores and reverse-if conditions.
- **T2** (Chris): LangGraph with synchronous checkpoints plus VERA's gate
  helpers. Reverse if T7 shows an RLM-style runtime clearly cheaper.
- **JDG-P-01..03** set (docs/02 0.3), as above.
- **Jev publication** (Chris, revising his earlier rule): Jev results are
  published, ledgers included, without seeking TypeSafe's consent; never
  train on Jev output (MCA §2.3(b)). docs/04 T1, R4.
- **Local candidate** (Chris agreed): Gemma 4 12B through Ollama added as
  T1 option (b).
- **Direction B** (Chris): the product is topic to paper with an app and
  bring-your-own-key. Increments re-planned: 2 thin loop (unchanged), 3
  topic front end and literature stage, 4 paper quality and the
  ScientistTwo comparison, 5 app UI/UX and BYOK, 6 optional external-paper
  auditing. New requirements RSH-F-08..11, APP-F-01/02, APP-C-01/02; T5
  widened to literature retrieval; new trade T8 (app delivery: BYOK moves
  model spend to the user but not hosted compute); R6 rescored to 9; new
  R11 (others spending the maintainer's money, key leaks).

## Loop-run cost estimate (R10)

Measured, billed per call on the benchmark (OpenRouter's `usage.cost`):
GLM-5.3 Flash $0.000129 (852 input + 128 output tokens, about $0.13 per
million tokens blended), Sonnet 5.5 $0.00367 (1,320 + 102, about $2.58 per
million blended), Jev $0.000047. OpenRouter bills above catalogue prices
for some models (below).

Assumed shape of one Increment 2 run (the call counts are assumptions, not
measurements): baseline reproduction 10 calls of about 15k input / 3k
output tokens, idea generation and screening 10 calls of 8k / 2k,
implementing and running the best idea 10 calls of 15k / 3k, write-up 4
calls of 20k / 4k; about 460k input and 96k output tokens in all. Gates:
about 40 judge questions; minimal P1 final gate: about 40 checks.

| Generator | Generation | Gates + final audit | Per run, x2 for retries and context growth |
|---|---|---|---|
| GLM-5.3 Flash throughout | ~$0.12 (catalogue), ~$0.2 with reasoning and billing above catalogue | ~$0.01 | **~$0.5** |
| GLM for code and ideas, Sonnet 5.5 for the write-up | ~$0.45 | ~$0.01 | **~$1** |
| Sonnet 5.5 throughout | ~$1.9 (catalogue), ~$2.4 with reasoning | ~$0.01 | **~$5** |

Judging is under 5% of a run's cost with the T1 path; generation is the
cost. R10's trigger (one run projected above 50% of the monthly ceiling,
$10) does not fire for any option. **Ceiling: kept at $20 for Increment 2**
(confirmed by Chris, 2026-10-01), which allows about 20 runs on the mixed
option or 4 on Sonnet throughout, including debugging runs. Choosing the
generator is new work for Increment 2 (with T7); Jev is billed by TypeSafe,
separately from OpenRouter, and counts toward the same ceiling.

## Spend against budget

| Item | Budget | Spent | Source |
|---|---|---|---|
| Backend smoke runs and debugging | $1.00 | about $0.12 in all: final smoke ledger $0.038; three earlier smoke runs about $0.077; debug calls $0.008 | `data/ledger/smoke.jsonl`, `data/ledger/debug.jsonl` (local); earlier runs from console output |
| Benchmark run | $8.00 | $1.61 | `data/ledger/bench_*.jsonl` |
| **Increment 1** | | **about $1.73** of the $20 monthly ceiling | |

The three earlier smoke runs were overwritten by the next run of
`scripts/smoke_run.py` (it replaced its ledger each run), so their spend is
known only from console output. That breaks "every model call is in the
ledger" for about $0.08; Increment 2 must keep one ledger file per run.

## Process lessons

- **A demonstration gate can pass with useless output.** The first smoke
  run recorded 50 complete ledger records while two backends returned no
  usable answer (reasoning models spending a 120-token budget on hidden
  reasoning; Sonnet writing working before its JSON). `check_ledger.py`
  checks records, not answers; the smoke script's own "no usable answer"
  count caught it. Fixed: reasoning is a per-model setting, `max_tokens`
  raised, the parser takes the last JSON object with an answer.
- **The kill-and-resume test found a real gap.** With LangGraph's default
  asynchronous checkpoints a killed run repeated a completed, billed node;
  synchronous checkpoints fixed it (docs/04 T2).
- **Catalogue prices are not billed prices.** OpenRouter serves DeepSeek
  V4.1 Flash through 32 providers at $0.024-0.60 per million input tokens;
  the run was stopped, switched to `provider.sort = price` and resumed, and
  DeepSeek still billed about $0.22 per million against a $0.02 headline.
  The first 50 DeepSeek verdicts used default routing.
- **Long runs outlast the agent's background limit** (10 minutes). The run
  was stopped twice by it and resumed; Chris ran the last segment in his
  terminal. The harness's resumability made this cheap: completed calls
  were never repeated, except the one call in flight at each kill (MiMo's
  ledger has 1,152 records for 1,150 verdicts).
- **Meridian escape (high):** MERIDIAN.md says secret rules are enforced at
  the commit boundary, but the pre-commit verifier does not scan file
  contents; the rules fire only on agent tool calls. VERA now scans every
  tracked file for API keys in its test suite (APP-C-01) and has a blocking
  OpenRouter-key rule. Logged with `dogfood.sh escape`.
- **Small slips, caught:** a `ruff format .` reformatted untouched files
  (reverted before commit); the agent once ran an over-broad `taskkill`
  pattern on Windows (no process was found to have been affected).

## Carry-overs from Increment 0

- At least 3 human-checked items drawn by seed and recorded by id:
  **closed** (label check, 3 per task).
- R6 wording and the option-B row: **closed** (Increment 0 errata).
- Dogfood overhead hours logged per session: **not done**. Chris estimates
  10-16 hours in total on VERA over Increments 0-1 (2026-09-29 to
  2026-10-01); the share spent on Meridian itself was not tracked, so no
  overhead hours are logged (`dogfood.sh report` shows 0) rather than an
  invented split. Increment 2 logs overhead per session.
- Still open, unchanged: 4 parents with unknown code; corpus likely
  success-only; T3 escalation run not spot-checked; fallback problem's
  compute question; commit 344374a's message; `tmp/` untracked.

## Open items

- **T6 (tracing)** is listed in docs/04 as an Increment 1 trade but was not
  in the Increment 1 SPEC and is not decided. Proposed: decide in Increment
  2; the ledger plus checkpoints have been enough so far.
- The ledger has no field for the serving provider, so per-provider cost
  and quality cannot be separated; proposed as a docs/03 change in
  Increment 2.
- The T1 router configuration is decided but not yet a function in code;
  Increment 2 adds it.
- Ollama 0.34.2 returns log-probabilities for the first token only; Gemma's
  confidence is self-reported and uninformative.

## Next SPEC (Increment 2 — thin loop on TreeHFD)

Rewrite `SPEC.md` for Increment 2 and add its gates after this gate passes.
Scope per docs/07 Increment 2 (unchanged by direction B). Changes to carry in:

- Use the T1 path through one shared function (Jev → GLM, `loop.*` to GLM),
  every call budgeted and in a per-run ledger file that is never
  overwritten.
- Decide T4 (sandbox) before any generated code runs; decide T7 with the
  RLM pattern measured against plain LangGraph state; decide the generator
  model(s) with measured cost per run; decide T6 or close it.
- Re-test the judge on the loop's real gate decisions (T1 reverse-if 1),
  since the Increment 1 benchmark is near ceiling on two of three tasks.
- Long runs are resumable and launched from Chris's terminal, or split
  into segments under 10 minutes.
- Propose a `provider` field for `LedgerRecord` (docs/03).
- Keep the secret scan in the suite; no maintainer key in any artifact
  (APP-C-01) from now on, not only in Increment 5.
