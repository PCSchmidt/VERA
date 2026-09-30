# SPEC — VERA, Increment 1 (P2 minimum viable judge)

## Overview

Current-increment features only, in build order. Each `##` below becomes a
tracked feature (`scripts/features-init.sh`); do not add `###` headings.
Source: [docs/07-increments.md](docs/07-increments.md) Increment 1; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.3; requirements due:
FND-F-01, FND-F-02, FND-C-01, JDG-F-01..06, JDG-P-01..03
([docs/02-requirements.md](docs/02-requirements.md)). Rewrite this file at
each increment review. The Increment 0 SPEC is in git history.

Who does what: Claude Code builds and runs; Chris approves the human gates,
checks benchmark labels, and decides T1/T2 with the evidence.

Rules carried from the Increment 0 review:

- **Spend.** Every model call goes through a `Budget` that raises before a
  limit is crossed: $1.00 for backend smoke tests, $8.00 for the benchmark
  run, inside the $20/month ceiling (ConOps §4). The OpenRouter key has a
  matching credit limit.
- **Human checks as practised.** An assistant may judge sampled items,
  working from source documents only; Chris personally checks at least 3 per
  sample, drawn by seed and recorded by id with his verdict.
- **Independence (docs/06 §5).** The benchmark's test split and the
  thresholds reported on it are fixed, and the split hashed, before any
  result on it is seen. Tuning uses the dev split only.
- **Dogfood.** Overhead hours are logged per session
  (`bash scripts/dogfood.sh`); gate blocks are labelled.

## Ledger and model-call wrapper

`vera/ledger/`: an append-only JSONL writer for `LedgerRecord` (docs/03)
under `data/ledger/<run_id>.jsonl` (git-ignored except named result
ledgers), plus one wrapper that every backend call goes through: it charges
the `Budget`, times the call, and writes the record. A lint check forbids
vendor SDK imports outside `vera/backends/`.

**Acceptance:** `test_FND_F_01_…` tests show a record with backend, model,
input/output tokens, cost, latency and trace id for every call, including
failed calls, and that a call that would exceed the `Budget` raises before
it is made; `tools/checks/check_vendor_imports.py` passes (FND-C-01).
**Gate:** `judge_core_ready`.

## Questions, verdicts and parsing

`vera/judge/`: prompt construction and answer parsing for the three
`QuestionType`s (Choice, Score, Boolean) into `Verdict`s, with confidence
from token log-probabilities where the backend returns them and a
self-reported probability otherwise (recorded as which, so calibration can
be compared). Malformed answers become a low-confidence `Verdict` flagged
for escalation, never an exception or a bare value.

**Acceptance:** `test_JDG_F_01_…` tests for each question type against a
fake backend, including malformed and out-of-range answers; every `Verdict`
round-trips and enforces `judge_id != producer_id`.
**Gate:** `judge_core_ready`.

## Router and escalation

`Router` tries backends in `cost_rank` order and escalates when confidence is
below the threshold from `RoutingPolicy` (per question type, per question id,
or per call), up to `max_escalations`; the final `Verdict` records the
backend used and `escalated`.

**Acceptance:** `test_JDG_F_02_…` (order, escalation on low confidence, no
escalation above threshold, escalation cap) and `test_JDG_F_03_…`
(threshold precedence: call > question id > question type > default), all
with fake backends and no network.
**Gate:** `judge_core_ready`.

## Backends: cheap and frontier

Two `JudgeBackend`s through OpenRouter (one API key, `.env`): a cheap model
and a frontier reference model, with per-token prices recorded from
OpenRouter at run time. Candidates for trade T1: cheap models named in
ConOps §4 (e.g. DeepSeek V4.1 Flash, GLM-5.3 Flash); a local small model
(via Ollama on the RTX A4500) for the offline criterion; TypeSafe Jev only if
its terms allow benchmarking and publishing results (check first, record in
docs/04).

**Acceptance (JDG-F-04, demonstration):** a smoke run of 10 benchmark dev
items per backend writes `data/ledger/smoke.jsonl` with records from at
least two backends, every field present and costs > 0 for paid backends,
total spend ≤ $1.00 (`tools/checks/check_ledger.py`).
**Gate:** `backends_live`.

## Graph helpers and checkpointing

`vera/graph/`: LangGraph node and conditional-edge helpers that wrap a
`Question` as a node and route on its `Verdict` (JDG-F-05), with a
checkpointer so a run resumes from the last completed node after a crash
(FND-F-02). This is the evidence for trade T2 (LangGraph alone vs. with
Meridian-style gate semantics on top).

**Acceptance:** `test_FND_F_02_…` kills a small graph mid-run and resumes it
without repeating completed nodes or their ledger records; a demo graph
routes on a judge `Verdict` (JDG-F-05).
**Gate:** `graph_ready`.

## Benchmark set with labels by construction

`data/benchmark/items.jsonl`: about 180 atomic questions in three tasks,
each labelled by how it was built (risk R3):

- **loop-gate** (from the Increment 2 problem): "does this result beat the
  TreeHFD baseline on this metric?" (Boolean) and "which candidate is best?"
  (Choice), from generated result tables with near-ties and distractors;
- **numeric consistency**: a claim about a table value, true or perturbed,
  using tables extracted by Docling from corpus papers (T3);
- **citation**: "does this reference list contain an entry for paper X?",
  using GROBID reference lists, with near-miss titles as negatives.

Split fixed before any run: dev (tuning) and test (reporting), about 1:2,
with the test split's SHA-256 recorded. Chris checks at least 3 items per
task, drawn by seed (`data/benchmark/label_check.csv`: id, seed, verdict,
note); any wrong label is fixed and its generator re-checked.

**Acceptance:** `tools/checks/check_benchmark_items.py`: three tasks, all
three question types present, split and test hash recorded, every task has
≥ 3 human-checked items with verdicts and no unresolved `incorrect`.
**Gate:** `benchmark_labeled` (human approval after the check passes).

## Benchmark harness and threshold sweep

`vera/bench/`: runs each backend on the test split (cheap backends N = 10
repeats, reference N = 3), then sweeps the router threshold offline over the
recorded verdicts. Reports per backend and threshold: agreement with labels
and with the reference judge, calibration (ECE), flip rate across repeats,
cost, p50/p95 latency, escalation rate (JDG-F-06). Output:
`data/benchmark/results.json` and the cost-vs-agreement threshold curve
(`docs/figures/threshold_curve.png`), the increment's core result.

**Acceptance:** `test_JDG_F_06_…` tests the metrics on fixed fake verdicts;
`tools/checks/check_benchmark_results.py`: metrics present for every backend
and threshold, test-split hash unchanged since labelling, ledger total for
the run ≤ $8.00.
**Gate:** `benchmark_run`.

## Decisions: T1, T2, targets and loop cost

From the benchmark and graph work: decide T1 (cheap backend) and T2
(runtime) in docs/04 with **Scores:**, **Decision:** and **Reverse if:**;
set JDG-P-01..03 in docs/02 from the measured curve (the defaults in
brackets are starting points, not commitments); estimate one Increment 2
loop run's cost from measured per-call costs against the $20 ceiling
(risk R10), and say whether a run month needs a temporary increase.

**Acceptance:** `tools/checks/check_trade_decided.py T1` and `… T2` pass;
JDG-P-01..03 have values; the loop-cost estimate is in the Increment 1 review.
**Gate:** `trades_decided_1` (human approval).

## Increment 1 review

Write `docs/reviews/incr-1.md` against the docs/07 exit criteria: the
threshold curve, T1/T2 decisions, JDG-P targets with their evidence, the
loop-run cost estimate and any ceiling change, label-check results, spend
against budget, dogfood overhead hours, and what changes in the Increment 2
SPEC. Carry-overs from Increment 0 are closed or restated.

**Acceptance:** passes the independent Evaluator (`run-evaluator.sh`), fresh
per round, with every verdict kept.
**Gate:** `incr1_review`.
