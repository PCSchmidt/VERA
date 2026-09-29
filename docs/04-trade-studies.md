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
