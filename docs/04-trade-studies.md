# 04 — Trade studies

Each trade: options → criteria → decision → what would reverse it.
Keep each to one short section. Status: **open** until decided.

## T1 — Cheap judge backend (decided 2026-10-01, Increment 1)

- **Options:** (a) TypeSafe Jev (hosted decision model); (b) small local
  model (e.g. a 1–8B instruct model with constrained/logprob output);
  (c) fine-tuned classifier on labeled judge data; (d) frontier LLM only
  (baseline).
- **Criteria:** agreement with reference, calibration, consistency, cost,
  latency, vendor lock-in, offline availability.
- **Leaning:** implement (a) and (b) behind `JudgeBackend`; compare in the
  benchmark rather than choosing up front. Confirm Jev pricing/terms first.
- **Reverse if:** Jev terms prevent benchmarking/publication, or local models
  match it closely.
- **Candidates (2026-09-30, OpenRouter catalogue prices per million tokens,
  in/out):** MiMo-V2.6-Flash $0.14/$0.28 (Chris's pick; no logprobs, so
  self-reported confidence), DeepSeek V4.1 Flash $0.02/$0.40 (logprobs),
  GLM-5.3 Flash $0.15/$0.50 (logprobs); reference Claude Sonnet 5.5 $2/$10;
  TypeSafe Jev via its direct API at **$0.042 per million input tokens,
  output free** (confirmed by Chris from the TypeSafe console).
  Local (option (b), added 2026-09-30 with Chris's agreement): Gemma 4 12B
  (`gemma4:12b`, ~8 GB) through Ollama 0.34.2 on the RTX A4500 Laptop GPU
  (16 GB), thinking off; $0 per token, so latency is its cost. It is the
  only candidate that scores the offline and lock-in criteria, and R4's
  local fallback. Smoke run (same 10 dev items): 10/10 parsed, 8/10
  agree; first call 84 s (model load), then p50 1.6 s. Ollama 0.34.2
  returns token log-probabilities for the first token only, so confidence
  is self-reported, and it reported 1.0 on all 10: the router cannot
  escalate on it unless the benchmark shows otherwise.
- **Jev terms (Master Customer Agreement, typesafe.ai/legal/mca, read
  2026-09-30):** no benchmarking clause. §2.3(b) forbids using Jev output to
  distil or train a model, so option (c) must never train on Jev answers.
  §14.1 counts "non-public information with respect to the Services" as
  TypeSafe's confidential information, which is ambiguous for published
  performance results. **Decision (Chris):** benchmark Jev; get TypeSafe's
  written consent before publishing any Jev results (risk R4).
  **Revised (Chris, 2026-09-30):** publish Jev results, ledgers included,
  without seeking consent: Jev benchmarks and comparisons are already
  public, as are open-source Jev clones, so published performance figures
  are not treated as TypeSafe confidential information. §2.3(b) still
  stands: never train on Jev output.
- **Smoke run (2026-09-30, 10 dev items each, $0.038 in all):** all five
  answer through the ledger. OpenRouter's endpoints for Sonnet 5.5 and
  GLM-5.3 Flash refuse to disable reasoning (HTTP 400), so both run at the
  provider default with `max_tokens` 2048; MiMo and DeepSeek run with
  reasoning off (DeepSeek returned empty answers with reasoning on and a
  small `max_tokens`). GLM's reasoning costs it latency and output tokens on
  the cheap path; the benchmark will measure how much. Settings in
  `vera/bench/candidates.py`. Ledger: `data/ledger/smoke.jsonl`.
- **Benchmark run (2026-10-01):** the 115-item test split (hash
  `0ae2c8d6f11a…`, fixed before any run), cheap backends 10 repeats, Sonnet
  3; 6,095 verdicts, $1.61, no failed calls (`data/benchmark/results.json`,
  `docs/figures/threshold_curve.png`, raw verdicts and ledgers committed).
  OpenRouter routes a model to many providers at different prices (DeepSeek
  V4.1 Flash: 32 providers, $0.024-0.60 per million input tokens); costs
  below are OpenRouter's billed costs, which ran above catalogue prices even
  with `provider.sort = price`. The first 50 DeepSeek verdicts used default
  routing.
- **Scores** (test split; agreement = with labels, which Sonnet matched on
  every item, so agreement with the reference is the same number):

  | Backend | Agreement | Loop gate | ECE | Flip rate | Cost/item | vs Sonnet | p50 / p95 |
  |---|---|---|---|---|---|---|---|
  | Sonnet 5.5 (reference) | 1.000 | 1.000 | 0.019 | 0.0% | $0.00367 | 100% | 1.26 / 2.13 s |
  | GLM-5.3 Flash | 0.998 | 1.000 | 0.006 | 0.9% | $0.000129 | 3.5% | 1.95 / 8.43 s |
  | Jev | 0.970 | 0.913 | 0.008 | 1.7% | $0.000047 | 1.3% | 0.19 / 0.36 s |
  | DeepSeek V4.1 Flash | 0.963 | 0.890 | 0.044 | 6.1% | $0.000054 | 1.5% | 0.37 / 1.42 s |
  | MiMo-V2.6-Flash | 0.915 | 0.782 | 0.072 | 7.8% | $0.000069 | 1.9% | 3.25 / 11.26 s |
  | Gemma 4 12B (local) | 0.886 | 0.667 | 0.114 | 1.7% | $0 | 0% | 1.70 / 3.80 s |

  Router replayed offline over the recorded verdicts: Jev escalating to
  Sonnet at threshold 0.7 gives 0.976 at 2.8% of Sonnet's cost (1.7%
  escalated); at 0.95, 0.982 at 9.7%. Jev escalating to GLM instead gives
  the same agreement (0.976 at 0.7) at 1.3% of Sonnet's cost with p50
  0.19 s. Jev's errors are 4 loop-gate items it gets wrong on nearly every
  repeat with high confidence, which escalation does not catch. DeepSeek and
  MiMo flip on 6-8% of items and their confidence does not flag their
  errors. Gemma reports confidence 1.0 on every verdict, so nothing it gets
  wrong ever escalates. Numeric and citation items are near ceiling for most
  backends; only the loop-gate task (38 test items) separates them, and with
  115 items a 1-2 point difference is one or two items.
- **Decision:** (Chris, 2026-10-01) the cheap path is **Jev, escalating to
  GLM-5.3 Flash** (`RoutingPolicy` default threshold 0.7, one escalation).
  Loop-gate questions (`loop.*`) go straight to GLM (per-question threshold
  1.0): GLM scored 1.000 on them against Jev's 0.913, and the loop asks few
  of them, so latency does not matter there. Sonnet 5.5 stays the reference
  for benchmarks, not a runtime tier. Gemma 4 12B through Ollama is kept
  working as the offline fallback (R4), not used by default. DeepSeek and
  MiMo are dropped (flip rate above JDG-P-03).
- **Reverse if:** (1) a harder benchmark (the Increment 2 loop's real gate
  decisions, or a new test split that is not near ceiling) shows Jev → GLM
  below 95% agreement with the reference; (2) Jev's price, terms or
  availability change (R4), then GLM alone (or Gemma offline); (3) GLM's
  latency starts to matter for a user-facing path, then re-run the sweep
  with Jev → Sonnet; (4) Ollama returns answer-token log-probabilities,
  then re-test Gemma, whose agreement is too low only because escalation
  can't see its errors.

## T2 — Orchestration runtime (decided 2026-10-01, Increment 1)

- **Options:** (a) LangGraph directly; (b) Meridian's DAG gates as the
  control layer on top of LangGraph; (c) Meridian standalone.
- **Criteria:** checkpoint/resume, human-in-the-loop interrupts, tracing,
  reuse of Meridian's evaluator separation, effort.
- **Leaning:** (b) — LangGraph for durability, Meridian for gate semantics.
- **Reverse if:** the integration costs more than reimplementing the gates.
- **Evidence so far (2026-09-30, `vera/graph/`, LangGraph 1.2.12 with the
  SQLite checkpointer):** checkpoint/resume works across a killed process
  (FND-F-02 test), but only with `durability="sync"`. With LangGraph's
  default (asynchronous checkpoint writes), a process killed in the next
  node lost the last checkpoint and the resumed run repeated a completed
  node and its billed model call. The gate semantics are ~100 lines on top:
  a judge node that refuses to grade its own producer's material, and
  routing that fails closed (low confidence, malformed or unrouted answers
  go to `on_low`). Effort for (b) so far: about half a session.
- **Scores:**

  | Criterion | (a) LangGraph alone | (b) LangGraph + gate semantics | (c) Meridian standalone |
  |---|---|---|---|
  | Checkpoint/resume | yes, with `durability="sync"` (tested by killing a run) | same | no run-time checkpointing; Meridian gates whole build stages |
  | Human-in-the-loop | interrupts built in | same | human gates, at build time only |
  | No self-grading, fail-closed routing | not provided | `judge_node`, `route_on_verdict` (tested) | yes, but for build gates, not run-time steps |
  | Effort | — | ~100 lines, about half a session | would mean reimplementing durable execution |
  | Tracing | checkpoints + VERA's ledger | same | telemetry of build events only |

- **Decision:** (Chris, 2026-10-01) (b). LangGraph runs the loop with the
  SQLite checkpointer and synchronous checkpoints after every node
  (`vera.graph.run`/`resume`); VERA's gate helpers add no-self-grading and
  fail-closed routing. Meridian stays the build harness for VERA itself, not
  its runtime.
- **Reverse if:** (1) the gate layer grows past what a thin wrapper can hold
  (e.g. needs its own scheduler), then reconsider; (2) T7's measurement in
  Increment 2 shows an RLM-style runtime (prime-agent's
  context-as-variables with recursive sub-calls) is clearly cheaper at equal
  quality and does not fit inside LangGraph nodes, then re-run this trade
  with it as an option; (3) synchronous checkpoints make multi-hour runs too
  slow.

## T3 — PDF parsing (decided 2026-09-30, Increment 0)

- **Options:** GROBID (strong on references), a Markdown converter
  (e.g. Marker/Docling), plain PyMuPDF text, LLM-based extraction.
- **Criteria:** reference-list accuracy, table fidelity, speed, Windows setup.
- **Test:** parse 10 corpus papers; score references and tables by hand.
- **Test run (2026-09-30):** 10 generated papers drawn at random
  (`data/t3_sample.json`, seed 635550), parsed by `scripts/t3_parse.py`
  with three candidates. An LLM-based parser was not tested, to stay inside
  the monthly spend ceiling. Scored by hand from the PDFs and parser outputs
  (`data/t3_scoring_guide.md`; `data/t3_pdf_counts.csv`, `data/t3_scores.csv`,
  `data/t3_scores_refs_rest.csv`) by Chris's assistant, not by the agent
  that ran the parsers. Chris spot-checked three papers of the first pass
  against the PDFs (SPECTRA, LC-FTT, DR-LEF); the escalation run's scorer
  reported one borderline call (TKFS-Attention, GROBID ref 17: 16 vs 17);
  Chris did not spot-check the escalation run and approved on the first-pass
  check.

  | Parser | Windows setup | Median s/paper | Refs extracted | Tables found |
  |---|---|---|---|---|
  | pymupdf4llm 1.28 | pip only (`t3` group); OCR must be turned off (`use_ocr=False`) or it OCRs born-digital pages | 11.7 | 338 | 29 |
  | GROBID 0.8.2 (CRF image) | Docker; the JVM crashed on WSL2's cgroups until `JAVA_TOOL_OPTIONS=-XX:-UseContainerSupport` | 2.0 | 372 | 85 |
  | Docling | pip (`t3` group, pulls torch; CPU build by default, GPU needs a CUDA wheel); downloads models on first run | 79.8 | 331 | 110 |

  Observations before scoring: the ICLR template's line numbers leak into
  pymupdf4llm's text, and it delivers reference lists as long blocks that
  merge entries; GROBID returns one structured entry per reference (authors,
  title, venue, year, arXiv id) but flattens spanning table headers; counts
  are extraction counts, not correctness.
- **Scores:** references are the PDF's references delivered as their own
  intact entry; tables are cells in the right row and column (first 5 data
  rows of Tables 1-2 per paper).

  | Parser | References, first 15 per paper | References, full lists | Table cells |
  |---|---|---|---|
  | GROBID | 135/150 = 90.0% | **348/381 = 91.3%** (worst paper 73%) | 220/633 = 34.8% |
  | Docling | 121/150 = 80.7% | 322/381 = 84.5% (worst paper 26%) | **554/633 = 87.5%** |
  | pymupdf4llm | 39/150 = 26.0% | not scored (out after first pass) | 165/633 = 26.1% |

  The first-pass reference gap (9.3 points) was inside the agreed 10-point
  rule, so GROBID and Docling were scored on full lists. Failure modes
  differ: Docling collapses whole runs of references into multi-reference
  blocks on some papers (FVTG-CP: 7/27), and on the one non-ICLR-template
  paper (LC-FTT) it extracted no usable references in the first 15 and no
  cells of either table; GROBID's failures are local (a few merged
  neighbours, truncated list ends) and its tables lose spanning headers.
- **Decision:** use two parsers by content. **GROBID** (Docker,
  `lfoppiano/grobid:0.8.2`, `JAVA_TOOL_OPTIONS=-XX:-UseContainerSupport` on
  WSL2) for reference lists and bibliographic fields, which the citation
  checks (P1) consume directly; **Docling** for tables and body text, the
  inputs to numeric-consistency checks. Drop pymupdf4llm. Costs accepted:
  two tools to run, and Docling at about 80 s per paper on CPU (GPU build
  not tried).
- **Reverse if:** (1) in Increment 3, citation-check errors on the seeded
  dev set trace to GROBID reference parsing more often than to the check
  itself, then re-test Docling or an LLM repair pass on references;
  (2) Docling's table extraction fails on external (non-ICLR-template)
  papers the way it did on LC-FTT, then re-run this trade on 10 external
  papers before building table checks on it; (3) keeping GROBID running in
  Docker proves unreliable, then fall back to Docling for references too
  (84.5% here) and accept its failure mode.

## T4 — Sandbox (open, decide in Increment 2)

- **Options:** local Docker (network off by default); hosted sandbox service.
- **Criteria:** isolation, GPU access, cost, Windows support (WSL2).

## T5 — Bibliographic source for citation checks (open, Increment 2)

- **Options:** Crossref, arXiv API, Semantic Scholar, OpenAlex (likely a
  combination with fallbacks).
- **Criteria:** coverage of ML venues and preprints, rate limits, terms.

## T6 — Tracing/observability (open, Increment 1)

- **Options:** LangSmith; OpenTelemetry + local store; ledger-only.
- **Criteria:** cost, lock-in, ability to publish traces with results.

## T7 — Loop context management (open, decide in Increment 2)

- **Options:** (a) plain LangGraph state plus summarisation; (b) prime-agent
  style Recursive Language Model patterns: papers, logs, and code held as REPL
  variables instead of in the context window, recursive sub-calls, bounded
  autonomy within turn/token/time budgets, durable sessions
  (PrimeIntellect-ai/prime-agent, MIT; a clone is in the workspace); (c)
  LangChain Deep Agents' filesystem and context management.
- **Criteria:** tokens and cost per loop run, reliability over multi-hour runs,
  implementation effort, fit with the `Budget`/ledger, Windows support.
- **Leaning:** borrow (b)'s prompt-as-variable pattern inside VERA's own
  LangGraph nodes rather than adopting prime-agent wholesale; measure token
  savings against (a) on the Increment 2 problem.
- **Constraint:** prime-agent's worker and kernel processes are explicitly not
  a security sandbox. Agent-generated code still runs only in the T4 sandbox
  (FND-F-03).
- **Reverse if:** the measured token savings are small on CPU-scale problems,
  or the pattern fights LangGraph checkpointing.
