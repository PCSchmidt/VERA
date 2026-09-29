# 07 — Increments

Each increment ends with a short written review (a lightweight SRR/PDR/CDR)
in `docs/reviews/incr-N.md`: what was done, exit criteria met or not, risks
updated, next increment confirmed.

## Increment 0 — Spike: know your data (≈2 weeks) ← CURRENT

Goal: answer "what data do we actually have?" before building anything.

Tasks (suggested order for Claude Code):

1. **Repo setup.** `uv init`, Python 3.11+, pytest, ruff, `.gitignore`
   (including `data/raw/`), package skeleton `vera/` with `schemas/`,
   `backends/`, `ledger/`. Implement the v0.1 schemas from
   `03-interfaces.md` as Pydantic models, with round-trip tests.
2. **Corpus discovery.** Work out how the ScientistTwo site lists its papers.
   Prefer a published listing or data file; fall back to the page source or
   network requests only if none exists. Write `scripts/discover_corpus.py` to enumerate all
   generated papers with domain, sub-domain, and method name.
3. **Download with provenance.** `scripts/fetch_corpus.py` downloads PDFs to
   `data/raw/scientisttwo/`, recording URL, retrieval date, SHA-256
   (FND-C-02). Be polite: rate-limit, respect robots.txt.
4. **Parent-paper mapping.** For each generated paper, identify the human
   parent paper (from the generated paper's text: baseline method and
   citation). Record title, venue, arXiv/DOI, and code URL if any.
5. **Code availability.** Check whether generated-paper code and parent-paper
   code are public. Record URLs.
6. **Compute estimate.** For each parent problem, estimate experiment cost
   (CPU / single GPU / multi-GPU) from the paper's setup section.
7. **Fill `data/corpus_inventory.csv`.**
8. **PDF parser trade (T3).** Parse 10 papers with 2–3 parsers; score
   reference-list and table extraction by hand; record the decision in
   `04-trade-studies.md`.
9. **Set TBD targets** in `02-requirements.md` where the inventory informs them.
10. **Update the risk register** (especially R1).

**Exit criteria**
- Inventory complete for all generated papers (unknowns marked, not blank).
- Code-availability rate known → decide whether P1 v1 includes method–code checks.
- 2–3 candidate CPU/single-GPU parent problems identified for P3.
- Schemas implemented (docs/03, v0.1 → v0.2) with passing tests.
- Parser chosen.
- Monthly spend ceiling set.

## Increment 1 — P2 minimum viable judge

Router, two backends, ledger, LangGraph helpers, benchmark harness on one
judging task. Exit: first cost-vs-agreement threshold curve; JDG-P targets
set from data.

## Increment 2 — P1 citations + numeric consistency

Ingest, claim extraction, citation check, numeric consistency, report
rendering, seeded-fault dev/test sets. Exit: detection rate measured on the
test split; first batch audit of the corpus.

## Increment 3 — P1 remaining checks + first paper

Method–code, spec/leakage, novelty, optional re-run. Write Paper 1
(judge benchmark / cost–quality of judges) or Paper 2 (independent audit
of an AI-generated research corpus). Exit: draft on arXiv or workshop-ready.

## Increment 4 — P3 on one parent problem

Budgeted loop on one CPU-scale parent problem; compare against
ScientistTwo's result. Exit: cost/quality point published; decide whether
to do a second problem.
