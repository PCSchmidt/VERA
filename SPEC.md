# SPEC — VERA, Increment 0 (know your data)

## Overview

Current-increment features only, in build order. Each `##` below becomes a
tracked feature (`scripts/features-init.sh`); do not add `###` headings.
Source: [docs/07-increments.md](docs/07-increments.md) Increment 0. Field
definitions: [data/README.md](data/README.md). Rewrite this file at each
increment review.

Who does what: Claude Code does the build and data work. Chris approves the
human gates, verifies the inventory spot-check, and scores the parser trade.

## Repo scaffold and v0.1 schemas

`uv` project (Python 3.11+), pytest, ruff; package `vera/` with `schemas/`,
`backends/`, `ledger/`. All docs/03 models (now v0.2) in Pydantic v2, including
`Budget.charge()` raising `BudgetExceeded` when any limit would be crossed.
`JudgeBackend` is a `Protocol` and has no round-trip test.

**Acceptance:** every docs/03 `BaseModel` round-trips (model → JSON → model) in
a test; `Verdict` with `judge_id == producer_id` raises; `Budget.charge()`
raises on each limit; `vera/schemas/version.py` contains a literal
`SCHEMA_VERSION = "X.Y"` equal to the docs/03 version
(`tools/checks/check_schema_version.py`); ruff and pytest pass.
**Gate:** `scaffold_ready`.

## Corpus discovery

`scripts/discover_corpus.py` enumerates **every generated paper the
ScientistTwo site lists** (source: <https://scientist-two.github.io/>), with domain, sub-domain, and method name. Prefer a published listing
or data file over page source or network requests; rate-limit and respect
robots.txt. Writes `data/corpus_discovery.json` and seeds one inventory row
per paper.

**Acceptance:** `corpus_discovery.json` records the source, the site's stated
count, the discovered count, and an explanation whenever they differ
(`tools/checks/check_discovery.py`).
**Gate:** `corpus_fetched`.

## Corpus download with provenance

`scripts/fetch_corpus.py` downloads generated-paper PDFs to
`data/raw/scientisttwo/` and appends one record per file to
`data/provenance.jsonl`:
`{"path", "url", "retrieved": "YYYY-MM-DD", "sha256"}` (data/README.md).

**Acceptance (FND-C-02):** every file under `data/raw/` has a record whose
hash matches the file, and nothing under `data/raw/` is tracked by git
(`tools/checks/check_provenance.py`). Test `test_FND_C_02_…` exercises the
provenance writer against a local file, **with no network access**, so the
test suite stays deterministic at every later gate.
**Gate:** `corpus_fetched`.

## Parent papers and code availability

For each generated paper: the human parent paper (title, venue, arXiv id or
DOI) and code URLs for both generated and parent work. Download parent-paper
PDFs to `data/raw/parents/` with provenance records, since the compute
estimate reads their setup sections.

**Acceptance:** filled in `data/corpus_inventory.csv`. Code URL columns hold a
URL, `none` (checked, no public code), or `unknown` (not determined), so the
code-availability rate can be computed.
**Gate:** `inventory_verified`.

## Compute estimates and P3 candidates

`compute_class` per **parent problem** (`cpu`, `single_gpu`, `multi_gpu`,
`unknown`) from the parent paper's experimental setup; rows sharing a parent
problem share the value. Flag 2–3 `cpu` or `single_gpu` parent problems as
P3 candidates.

**Acceptance:** every row has an allowed `compute_class` and
`candidate_for_p3`; 2–3 distinct parent problems are `yes`, all cpu or
single_gpu (`tools/checks/check_inventory.py`).
**Gate:** `inventory_verified`.

## Inventory verified by spot-check

The inventory is mostly agent-filled, so it's checked by a human, not by the
agent that filled it. `tools/checks/check_inventory.py --sample 10` draws a
seeded random sample into `data/inventory_spotcheck.csv`; Chris checks each
sampled row against its sources and records `correct` or `incorrect` with a
note.

**Acceptance:** no blank cells, template rows, or values outside the data
dictionary; `gen_sha256` values match provenance; every sampled row has a
verdict (`tools/checks/check_inventory.py`). **Target error rate ≤ 10%**
(set 2026-09-29; revisable at the increment review); above it, fix the process and
re-sample only the rows filled after the fix. The measured rate goes in the
Increment 0 review.
**Gate:** `inventory_verified` (human approval after the check passes).

## PDF parser decision

Trade T3: Claude Code parses 10 corpus papers with 2–3 parsers and tabulates
the output; Chris scores it by hand.

- **Reference lists:** per paper, references extracted correctly ÷ references
  in the PDF (Chris counts).
- **Tables:** for 1–2 tables per paper, cells extracted correctly ÷ cells.
- Also record Windows setup effort (e.g. GROBID needs Java or Docker), time per
  paper, and spend for any LLM-based option (within the monthly ceiling).

**Acceptance:** T3 in docs/04 is marked decided, with a **Scores:** line, a
**Decision:** line, and a **Reverse if:** line
(`tools/checks/check_trade_decided.py T3`).
**Gate:** `parser_decided`.

## Increment 0 review

Write `docs/reviews/incr-0.md` against the exit criteria in docs/07. It must:

- state each exit criterion as met or not met, with evidence;
- report the spot-check error rate and the code-availability rate (generated
  and parent, counting `none` and `unknown` separately);
- **decide whether P1 v1 includes method–code checks** (AUD-F-05) from the
  code-availability rate, and update risk R1;
- set only the TBDs the inventory informs: **RSH-P-02** (number of parent
  problems). JDG-P and AUD-P targets stay TBD until the Increment 1–2
  benchmarks; don't invent them;
- confirm Increment 1 and note what changes in the next SPEC.

**Acceptance:** the review passes the independent Evaluator (`run-evaluator.sh`).
**Gate:** `incr0_review`.
