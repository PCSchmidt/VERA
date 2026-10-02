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
  3; 6,095 verdicts, $1.61; 3 failed calls, each retried successfully (`data/benchmark/results.json`,
  `docs/figures/threshold_curve.png`, raw verdicts and ledgers committed).
  OpenRouter routes a model to many providers at different prices (DeepSeek
  V4.1 Flash: 32 providers, $0.024-0.60 per million input tokens); costs
  below are OpenRouter's billed costs. DeepSeek billed about $0.24/M input
  all-in on its first 50 calls (default routing), $0.20/M on the next 50
  (cheapest-provider routing, not yet settled), then about $0.05/M; GLM
  billed below its catalogue rate.
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
  0.19 s. The decided path (below, with `loop.*` straight to GLM) gives
  1.000 at 1.8% of Sonnet's cost; latency p50 0.19 s and p95 0.36 s for
  the other questions, p50 1.6 s and p95 8.6 s for loop gates. Jev's errors are 4 loop-gate items, wrong on 10, 10, 9 and 5 of
  their 10 repeats, mostly with high confidence, which escalation does not catch. DeepSeek and
  MiMo flip on 6-8% of items and their confidence does not flag their
  errors. Gemma reports confidence 1.0 on 1,149 of 1,150 verdicts, so almost
  nothing it gets wrong escalates. Numeric and citation items are near ceiling for most
  backends; only the loop-gate task (39 test items) separates them, and with
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
- **Re-test (Increment 2, 2026-10-02):** reverse-if (1) was tested on the loop's
  real gate decisions (`data/retest/`, 77 test items, decided path at the
  loop's `effort: minimal` setting): 75/77 = 97.4% agreement with the Sonnet
  reference (95% CI 91.0-99.3), so it did **not fire**; the lower bound is below
  95% and both misses are confident perturbed items. docs/reviews/incr-2.md.

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

## T4 — Sandbox (decided 2026-10-01, Increment 2)

- **Options:** (a) local Docker (network off by default); (b) a hosted sandbox
  service.
- **Criteria:** isolation, GPU access, cost, Windows support (WSL2), startup
  overhead, how well it carries over to a hosted app (T8).
- **Test (2026-10-01, `scripts/t4_sandbox_check.py`, image `docker/sandbox-treehfd/`, Docker Desktop 29.7 on WSL2, 24
  CPUs, 32 GB):** an image built from the TreeHFD checkout at commit
  `dd02152` (Apache-2.0, version 1.4.2; `python:3.12-slim`, `pip install`,
  non-root user) run with `--network none --read-only --tmpfs /tmp
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 128 --memory 1g
  --cpus 2` and only a working directory mounted. The hosted option was not
  measured: it would be an account, a key and a per-run price, and a request
  for a second vendor's terms before any evidence that Docker fails.
- **Scores:**

  | Property | Result |
  |---|---|
  | No network | TCP connect and DNS both fail inside; the same snippet on the default bridge connects (so the test can fail) |
  | Host files | only `/work` is visible; the repository's `.env`, `/c`, `/Users`, `/mnt/host` do not exist; mounts are `/`, `/work` and three Docker files |
  | Writes | `/etc`, `/opt`, `/usr`, home refused (read-only root); `/work` and the 64 MB `/tmp` allowed; `/work` files appear on the host |
  | Wall-clock kill | `docker kill <name>` after 8 s stops an infinite loop and leaves no container (killing only the `docker` client would not) |
  | Memory limit | allocating 4 GB under `--memory 1g` is killed (exit 137) |
  | Process limit | a fork bomb gets `EAGAIN` at 128 processes |
  | Secrets | the host environment is not inherited; the only key-like variable is `GPG_KEY`, the public key id of the Python base image |
  | Overhead | 0.5-0.6 s per container start (1.2 s cold) |
  | The baseline | TreeHFD (n = 5000, 6 dimensions, 100 XGBoost trees, interaction order 2) runs in 21 s inside it, relative residual variance 0.0104 (about 1%) |
  | GPU | Docker Desktop lists an NVIDIA runtime; not needed for CPU-scale problems, not tested |

  Gaps found: `/work` has no size cap (the sandbox module must check the
  directory size after a run); the image's `GPG_KEY` variable means a "no
  key-like variable" test needs an allow-list, or the image should clear it;
  the image takes 2.5 minutes to build and needs the network once, outside the
  sandbox.
- **Decision:** (Chris, 2026-10-01) (a),
  local Docker, run through one function with the flags above, the wall limit
  enforced by `docker kill`, the network off unless a run grants it (recorded),
  and the image built in advance from a pinned commit. No hosted sandbox now.
- **Reverse if:** (1) Docker Desktop proves unreliable on this machine over
  the Increment 2 runs (hangs, daemon restarts); (2) a problem needs a GPU
  or more than the container limits; (3) T8 chooses a hosted app, where the
  same image runs under a hosted container service instead, so this decision
  carries over unless that service cannot run it with the network off.

## T5 — Bibliographic source for citation checks and literature retrieval (decided 2026-10-01, Increment 2-3)

- **Options:** Crossref, arXiv API, Semantic Scholar, OpenAlex (likely a
  combination with fallbacks).
- **Criteria:** coverage of ML venues and preprints, rate limits, terms,
  search quality for the literature stage (Increment 3), open-access PDF links.
- **Test (`scripts/t5_lookup.py`, seed 20261003):** the 10 T3 papers; 15
  references per set drawn by seed from two sets, 292 distinct titles: the
  generated paper's GROBID list (may hold fabricated entries) and its parent
  paper's GROBID list (real papers, so a miss is a coverage gap or a parse
  error). Each looked up by title (top 3 results). A hit has normalised title
  similarity >= 0.90; "title+year" also needs the year within 1. No email or
  key was sent to Crossref or arXiv; requests carried a User-Agent naming the
  project. OpenAlex was first tried keyless and cut off, then completed with
  Chris's free key (read from `.env`, never cached or logged).
- **Scores** (hit rate on real parent references / on generated references;
  Crossref, arXiv and OpenAlex completed all 292 titles; Semantic Scholar was
  throttled to 14 titles):

  | Source | Parent, title+year | Parent, title only | Generated, title+year | p50 latency | Terms and limits found |
  |---|---|---|---|---|---|
  | Crossref | 45.6% (149) | 48.3% | 41.3% (150) | 1.0 s | free, keyless; no limit hit at 0.3 s pauses |
  | arXiv API | 51.7% (147) | 59.9% | 78.7% (150) | 0.2 s | free, keyless; 1 request per 3 s asked; retries on 429/5xx needed |
  | OpenAlex | 64.4% (149) | 69.1% | 79.3% (150) | 0.3 s | **needs an API key**: keyless requests share a tiny daily budget per IP address (about 100 searches, gone after 104 lookups); the free key is limited to $1 a day, about 1,000 searches at $0.001 each |
  | Semantic Scholar | not measured | | 85.7% (14) | 16 s | keyless pool throttled almost every request (HTTP 429); a key is needed in practice |
  | **Crossref + arXiv** | **74.5%** | **80.5%** | **90.0%** (92.0% title only) | | |
  | Crossref + arXiv + OpenAlex | 81.2% | 86.6% | 92.7% (93.3% title only) | | |

  What the misses on real parent references are (38 of 149 missed by both
  completed sources, 9 of them found by title once the year rule is dropped:
  preprint year against journal year, e.g. a 1996 paper cited as 1998): GROBID
  parse errors (author names merged into the title, about 4), books, talks and
  technical notes that neither source indexes (for example "Prediction,
  learning, and games", "Coherent measures of risk", the JAX report), and
  titles Crossref ranks outside its top 3. Of the 15 generated-paper misses,
  about 4 are parse errors, 4 are year differences, and the rest are not found
  (a too-new parent, a real paper not indexed, possibly fabricated entries):
  the measurement cannot tell these apart, so "not found" means "unverified",
  not "fabricated", for anyone else's paper.
- **Decision:** (Chris, 2026-10-01)
  **Crossref and arXiv as the keyless pair** for existence checks and
  retrieval, queried by title with the year used as a hint (an exact title
  with a different year is a match with an `info` finding, not a miss).
  OpenAlex (measured: adds about 7 points on real references) and Semantic
  Scholar (unusable keyless) are optional extras that the user's own key
  switches on (APP-C-01: never a maintainer key in an artifact; a key in
  Chris's `.env` for his own runs is fine). For Increment 2 the loop's own
  write-up cites only records it retrieved, so each reference is first
  matched against the run's retrieval log (exact), then looked up; a
  reference that is neither fails the audit. For external papers
  (Increment 6) the lookup needs a title-with-author fallback and a
  separate "unverified" tier below `fail`; AUD-F-03's detection and
  false-positive targets come from the seeded set there, not from this
  measurement.
- **Reverse if:** (1) in Increment 3, retrieval from Crossref + arXiv
  misses too many relevant papers for the literature stage (judged by the
  topics' known key papers), then make a keyed OpenAlex or Semantic Scholar
  the primary; (2) arXiv's rate limit makes a literature stage too slow;
  (3) either source's terms or limits change; (4) the seeded citation faults
  show false "fail" findings on real references above AUD-P-01's 10%, then
  add the fallback tiers before widening the checks.

## T6 — Tracing/observability (decided 2026-10-02, Increment 2)

- **Options:** LangSmith; OpenTelemetry + local store; ledger-only.
- **Criteria:** cost, lock-in, ability to publish traces with results.
- **Evidence (Increment 2):** every fault found in this increment was diagnosed from what VERA already records:
  the per-run ledger (component, model, provider, tokens, cost, latency, timestamp, error), `gates.jsonl` (each
  judge question with its material, verdict and programmatic shadow answer), the stage artifacts (including the
  generator's raw replies on failure) and the checkpoints. Examples: GLM's unbounded reasoning (ledger output tokens),
  MiMo's empty replies (ledger tokens against the 8000 cap), TreeHFD's non-deterministic `predict`, and a 39-minute
  machine standby that made valid experiments look timed out (file times against the Windows power log).
- **Scores:** none measured, as there are no tracing options to compare; the evidence above is the record.
- **Decision:** (Chris, 2026-10-02, by approving `trades_decided_2` on the proposal as written) ledger plus checkpoints plus `gates.jsonl`; no
  tracing service. They are local, free, publishable with results, and already carry what debugging needed.
- **Reverse if:** (1) Increment 3's literature stage has call trees deep enough that the flat ledger can't show which
  retrieval produced which claim; (2) a failure needs the full prompt and reply of every call, which the ledger
  deliberately does not store; (3) results need to be published with browsable traces.

## T7 — Loop context management (decided 2026-10-02, Increment 2)

- **Options:** (a) plain LangGraph state plus summarisation; (b) prime-agent style Recursive Language Model patterns:
  papers, logs, and code held as REPL variables instead of in the context window, recursive sub-calls, bounded
  autonomy within turn/token/time budgets, durable sessions (PrimeIntellect-ai/prime-agent, MIT); (c) LangChain
  Deep Agents' filesystem and context management.
- **Criteria:** tokens and cost per loop run, reliability over multi-hour runs, implementation effort, fit with the
  `Budget`/ledger, Windows support.
- **Constraint:** prime-agent's worker and kernel processes are explicitly not a security sandbox. Agent-generated
  code still runs only in the T4 sandbox (FND-F-03).
- **Scores:** option (b) was not built; what was measured is the most it could save. Before building it, the ledgers of the
  generator-comparison runs (T9) give the most a context technique could save, which is the input side of the
  generators' bill:

  | Arm | Input tokens | Output tokens | Input share of generator cost (catalogue prices) |
  |---|---|---|---|
  | GLM-5.3 Flash | 10,326 | 10,312 | 23% |
  | GLM + Sonnet write-up | 11,030 | 13,392 | 18% |
  | Sonnet 5.5 | 10,317 | 12,604 | 14% |
  | DeepSeek V4.1 Flash | 9,902 | 86,019 | 1% |
  | MiMo-V2.6-Pro | 7,191 | 100,076 | 4% |

  (the three counted repeats per arm, runs 2-4; the last two arms are mostly empty replies that used their whole output allowance. Corrected 2026-10-02 after Evaluator round 1 on the Increment 2 review: the first version summed the discarded standby runs (`-1`) as well, giving 13,017 / 12,935 for GLM and 15,465 / 17,324 for Sonnet; the shares moved by at most one point, Sonnet 15% to 14%). The
  loop's prompts are small by construction (a results table, the idea texts, an API example): about 1,000 to 2,000
  input tokens per call. Output tokens, and within them the models' hidden reasoning, are 50% to 97% of the tokens
  and 77% to 99% of the generator cost. A perfect context technique that removed all input would save at most about
  14% to 23% of a bill of $0.002 to $0.05 per run.
- **Decision:** (Chris, 2026-10-02, by approving `trades_decided_2` on the proposal as written) (a), plain LangGraph state with small prompts built
  by the stage (as now). Do not build (b) for Increment 2: its ceiling here is a fraction of a cent per run, and it
  adds a REPL process next to a sandbox that already isolates code.
- **Reverse if:** (1) Increment 3's literature stage puts long papers in the prompt, so input dominates (measure the
  input share again there; this is where the prompt-as-variable pattern should be tested first); (2) a run's prompts
  grow past a fixed size (say 20,000 input tokens per call); (3) the REPL idea is wanted for another reason, to let
  the model test code as it writes it, which is a separate design question about the sandbox, not a cost trick.

## T8 — App delivery and bring-your-own-key (open, decide in Increment 5)

- **Options:** (a) local app: the user runs VERA on their own machine with
  a web UI on localhost and their key in their own environment; (b) hosted
  demo: a public site where the visitor connects their own OpenRouter
  account or pastes a key held only in their browser session; (c) both,
  local as the product and hosted as a demo.
- **Criteria:** who pays (model calls, but also hosting and the sandbox
  compute that runs experiments, which BYOK does not cover), key safety
  (APP-C-01/02), ease of first use from the landing page, UI quality,
  effort, Windows support.
- **Leaning:** (c), with (a) first. A hosted demo runs only the literature
  stage, or experiments under a hard per-visitor compute cap, because BYOK
  moves model spend to the visitor but not server compute. Confirm
  OpenRouter's account-connection flow (OAuth with PKCE) when this trade
  is run.
- **Reverse if:** hosting cost per visitor can be bounded near zero, then a
  full hosted app; or a local install proves too hard for the intended
  users, then invest in packaging.

## T9 — Generator model(s) for the loop's producers (decided 2026-10-02, Increment 2)

- **Options (arms):** (A) GLM-5.3 Flash for every stage; (B) GLM for ideas and code with Claude Sonnet 5.5 writing the
  report; (C) MiMo-V2.6-Pro for every stage; (D) DeepSeek V4.1 Flash for every stage; (E) Sonnet 5.5 for every stage
  (the quality reference).
- **Criteria:** whether the experiment code works, whether the run completes and its audit is not red, cost, wall time,
  independence from the judge (the loop's questions go to GLM, so a GLM generator is graded by its own model family).
- **Test (`scripts/run_loop.py --arm ... --from-run smoke-007`, `scripts/reaudit_runs.py`, `scripts/summarize_arms.py`):**
  every run starts at the ideas stage from the same recorded baseline (smoke-007), asks for 3 ideas, implements the 2
  best (one retry each), writes the report and is audited. Three repeats per arm (MiMo with a 20,000-token allowance:
  one, the second repeat stopped early); identical settings for all (`reasoning: {effort: minimal}`, 8,000 output
  tokens, temperature 0.7); every report re-audited with the same final audit code. A first wave of five runs was
  discarded: the machine entered standby for 39 minutes mid-run, so valid experiments were recorded as timed out; the
  runner now holds a keep-awake request (`vera/keepawake.py`), and the discarded runs' ledgers are kept. Small N:
  directional. Raw results: `data/results/generator_comparison.json`.
- **Scores:** (cost is the run ledger's billed total; "first try" counts the 6 selected ideas per arm that ran validly
  on the first attempt; "audit" is the final audit result of each repeat that produced a report):

  | Arm | First try | Valid at all | Runs with a valid experiment | Audit of those | Mean cost | Wall per run |
  |---|---|---|---|---|---|---|
  | A GLM-5.3 Flash | 3/6 | 6/6 | 3/3 | green, green, **red** | $0.0019 | 530-933 s |
  | B GLM + Sonnet write-up | 4/6 | 6/6 | 3/3 | amber, green, green | $0.0172 | 585-853 s |
  | C MiMo-V2.6-Pro | 0/6 | 0/6 | 0/3 | none | $0.0286 | 999-1,072 s |
  | C' MiMo, 20,000 tokens | 0/2 | 0/2 | 0/1 | none | $0.0682 | 2,616 s |
  | D DeepSeek V4.1 Flash | 1/6 | 2/6 | 1/3 | green | $0.0161 | 748-1,742 s |
  | E Sonnet 5.5 | **6/6** | 6/6 | 3/3 | green, amber, green | $0.0492 | **541-682 s** (mean 591 s; A's mean is 694 s, its fastest run 530 s) |

  Where the cost goes (means): Sonnet spends $0.0056 on ideas, $0.0277 on code and $0.0156 on the report; in B the
  report is 89% of the cost ($0.0152, against $0.0004 if GLM wrote it).
- **Findings.**
  - **No arm improved on TreeHFD.** Across the 10 comparison runs that produced a valid experiment (the other 6 produced none) no idea beat the baseline on every dataset (the best cases
    improved one dataset and worsened the other). The generator choice changes reliability and cost, not whether the
    loop finds a better method on this problem; that is the loop's research quality, to be measured against
    ScientistTwo in Increment 4.
  - **MiMo-Pro and DeepSeek-Flash fail on code at these settings**: their replies came back empty after using the
    whole 8,000-token allowance (MiMo in every attempt, DeepSeek in most), because `effort: minimal` does not bound
    their reasoning on a code task, though it did for GLM (about 130 reasoning tokens on the probe) and Sonnet. Even
    20,000 tokens did not rescue MiMo (calls took about 13 minutes each). A different setting might fix them; this
    test cannot say.
  - **Sonnet implemented every idea first try** and had the shortest mean wall time (fewer retries; one GLM run, 530 s, was faster than any Sonnet run); GLM needed a retry on half
    its ideas.
  - **The audit found a real fault in a GLM report** ("runtime increased +~10% on both datasets", where the results
    give about +9% and +6% for one idea and +25% for the other): a loose approximation matching no real number.
    It also failed two papers falsely before the audit was fixed (a method-section design threshold counted as a
    result); those were re-audited with the final code.
  - **Cost is no longer the constraint.** Sonnet throughout costs about $0.05 per run, about 110 times less than the
    Increment 1 estimate (about $5.7), which assumed reasoning-heavy output. The $20 ceiling allows several hundred
    such runs.
  - **Independence.** With a Sonnet generator, nothing the loop produces is graded by its own model family (the judge
    path is Jev and GLM); with A and B, GLM writes ideas and code and also scores them.
- **Decision:** (Chris, 2026-10-02, by approving `trades_decided_2` on the proposal as written) **E, Sonnet 5.5 for every stage**, for the Increment 2
  complete run and for building Increment 3: the only arm with a clean first-try record, the shortest mean wall time, no
  generator/judge overlap, at a cost of cents. GLM-5.3 Flash (A) stays the documented low-cost option for the app's
  bring-your-own-key users (Increment 5), at a bill about 25 times lower and with more retries and a loose-number
  tendency. MiMo-Pro and DeepSeek-Flash are not used at these settings.
- **Reverse if:** (1) Sonnet's price or availability changes so that a run costs more than a few percent of the
  ceiling; (2) a setting change (a different reasoning control, a larger allowance with a bounded effort) lets MiMo or
  DeepSeek match Sonnet's first-try rate at a lower cost; (3) Increment 4's comparison shows ideas, not code, are
  where quality is decided: then test an ideation model separately; (4) the judge path moves to the same family as the
  generator, restoring the overlap this decision avoided.

## T10 — Where a problem's baseline comes from (open, decide in Increment 3)

- **Options:** (a) a harness per problem written by hand (what Increment 2 did
  for TreeHFD: `docker/sandbox-treehfd/harness.py`); (b) a model-written baseline
  script run in the sandbox, with the baseline gate unchanged (the Increment 2
  SPEC's original wording); (c) a hybrid: a thin generic harness (data loading,
  seeds, the metric and the validity checks) with the model writing only the
  adapter that calls the parent's code.
- **Criteria:** whether a second parent problem (Increment 4) and later user
  topics can be supported without hand work each time, validity of the reproduced
  baseline (the gate must not accept a wrong one), effort, and sandbox safety.
- **Evidence to collect (Increment 3):** how many candidate parents the literature
  stage finds for topics (a) and (b), how many have public code that runs in the
  sandbox, how long wrapping each by hand takes, and whether a model-written or
  hybrid baseline reproduces a known baseline within its registered tolerance.
- **Scores / Decision / Reverse if:** to be written at `trades_decided_3`.
