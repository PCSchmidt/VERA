# 04 — Trade studies

Each trade: options → criteria → decision → what would reverse it.
Keep each to one short section. Status: **open** until decided.

## T1 — Cheap judge backend (open, decide in Increment 1)

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
- **Jev terms (Master Customer Agreement, typesafe.ai/legal/mca, read
  2026-09-30):** no benchmarking clause. §2.3(b) forbids using Jev output to
  distil or train a model, so option (c) must never train on Jev answers.
  §14.1 counts "non-public information with respect to the Services" as
  TypeSafe's confidential information, which is ambiguous for published
  performance results. **Decision (Chris):** benchmark Jev; get TypeSafe's
  written consent before publishing any Jev results (risk R4).
- **Smoke run (2026-09-30, 10 dev items each, $0.038 in all):** all five
  answer through the ledger. OpenRouter's endpoints for Sonnet 5.5 and
  GLM-5.3 Flash refuse to disable reasoning (HTTP 400), so both run at the
  provider default with `max_tokens` 2048; MiMo and DeepSeek run with
  reasoning off (DeepSeek returned empty answers with reasoning on and a
  small `max_tokens`). GLM's reasoning costs it latency and output tokens on
  the cheap path; the benchmark will measure how much. Settings in
  `vera/bench/candidates.py`. Ledgers with Jev rows stay local (R4).

## T2 — Orchestration runtime (open, decide in Increment 1)

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
