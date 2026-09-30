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

## T2 — Orchestration runtime (open, decide in Increment 1)

- **Options:** (a) LangGraph directly; (b) Meridian's DAG gates as the
  control layer on top of LangGraph; (c) Meridian standalone.
- **Criteria:** checkpoint/resume, human-in-the-loop interrupts, tracing,
  reuse of Meridian's evaluator separation, effort.
- **Leaning:** (b) — LangGraph for durability, Meridian for gate semantics.
- **Reverse if:** the integration costs more than reimplementing the gates.

## T3 — PDF parsing (open, decide in Increment 0)

- **Options:** GROBID (strong on references), a Markdown converter
  (e.g. Marker/Docling), plain PyMuPDF text, LLM-based extraction.
- **Criteria:** reference-list accuracy, table fidelity, speed, Windows setup.
- **Test:** parse 10 corpus papers; score references and tables by hand.
- **Test run (2026-09-30):** 10 generated papers drawn at random
  (`data/t3_sample.json`, seed 635550), parsed by `scripts/t3_parse.py`
  with three candidates. An LLM-based parser was not tested, to stay inside
  the monthly spend ceiling. Scoring by hand is pending
  (`data/t3_scoring_guide.md`, `data/t3_pdf_counts.csv`, `data/t3_scores.csv`).

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
