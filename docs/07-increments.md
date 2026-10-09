# 07 — Increments

Each increment ends with a short written review (a lightweight SRR/PDR/CDR)
in `docs/reviews/incr-N.md`: what was done, exit criteria met or not, risks
updated, next increment confirmed.

**Re-planned 2026-10-01 (Chris, direction B):** the product is topic → paper
with an app and bring-your-own-key. Increment 2 is unchanged (it builds the
experiment engine). Increments 3-5 now build the topic front end, paper
quality and the app; the auditor (P1) shrinks to the loop's final gate, and
auditing external papers moves to Increment 6 (optional). The plan before
this change is in git history.

## Increment 0 — Spike: know your data (≈2 weeks) — complete 2026-09-30

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
- 2–3 candidate CPU/single-GPU parent problems identified; **one chosen
  for the Increment 2 loop** (prefer experiments that finish in minutes).
- Schemas implemented (docs/03, v0.1 → v0.3) with passing tests.
- Parser chosen.
- Monthly spend ceiling set.

Build order (decided 2026-09-29): P2's cheap critics first, because they are
what make a cheap loop possible; then a **thin end-to-end loop** on one
problem, so the product works early and every later increment improves a
working pipeline. P1 grows up as the loop's final gate.

## Increment 1 — P2 minimum viable judge — complete 2026-10-01

Router, two backends, ledger, LangGraph helpers, benchmark harness on one
judging task drawn from the loop's gate decisions (e.g. "idea worth a subset
run?", "result beats baseline?"). Decide T1 (cheap backend) and T2 (runtime).
Exit: first cost-vs-agreement threshold curve; JDG-P targets set from data;
measured per-call costs used to estimate one loop run against the spend
ceiling.

## Increment 2 — Thin loop on one parent problem — complete 2026-10-02

The product, crude but end to end, on the one CPU-scale problem chosen in
Increment 0 (**TreeHFD**, Benard, NeurIPS 2025, arXiv 2510.24815; fallback:
credal ambiguity sets; see docs/reviews/incr-0.md): problem spec + output guidance + `Budget` → reproduce baseline on
a subset → generate and screen a few ideas → run the best on the subset →
write-up → final gate. Every stage transition is a P2 critic `Verdict` from a
component other than the producer. The final gate is a **minimal P1**:
citation existence and numeric consistency of the write-up against the run's
own logs, with evidence links. Agent-generated code runs only in the sandbox
(decide T4). Decide T7 (context management).
Exit: one complete run inside its budget, with a per-stage cost ledger and an
audit report on its own paper; an honest write-up of what the crude loop got
right and wrong.

Result (docs/reviews/incr-2.md): `loop-001` ran complete for $0.052 (Sonnet 5.5
for every stage) and was audited green; it was a negative result. T4 (local
Docker), T5 (Crossref + arXiv), T6 (ledger only), T7 (plain state), T9 (Sonnet
5.5) decided; the judge re-test on the loop's real decisions gave 97.4% (95% CI
91.0-99.3), so T1's reverse-if did not fire.

## Increment 3 — Topic front end and literature stage (complete 2026-10-03)

Scope, gates and caps proposed in SPEC.md (2026-10-02); `incr3_scoped` is Chris's approval of them.

From a topic to a scoped question and a literature review: topic scoping
(proposed question, shown for the user's confirmation), retrieval from a
bibliographic source (decide T5), reading with the T3 parsers, synthesis
with every citation verified (AUD-F-03 on the loop's own text), and, for
empirical questions, choosing a CPU-scale parent problem and baseline. Apply
the context-management decision (T7) where the literature is long.
Exit: three topics taken to a scoped question and a literature section with
verified citations; cost per topic measured; one of them carried through
the Increment 2 loop end to end.

## Increment 4 — Paper quality and the measured comparison — complete 2026-10-05

Scope, gates and caps proposed in SPEC.md (2026-10-03); `incr4_scoped` is Chris's approval of them.

Paper-shaped write-up (abstract, related work, method, results with
figures, limitations, references) following the output guidance; ablations
(RSH-F-04); method–code alignment on the loop's own code (AUD-F-05);
novelty of the loop's idea against the retrieved literature (AUD-F-07); a
second parent problem, and cost/quality against ScientistTwo on both
(RSH-P-02, MOE-3).
Exit: two complete runs compared with ScientistTwo; an honest account of
where the write-ups fall short of an academic paper.

## Increment 5 — App: UI/UX and bring-your-own-key — complete 2026-10-09 (MOE-4 not shown: the walkthrough was the builder)

Scope, gates and caps proposed in SPEC.md (2026-10-06); `incr5_scoped` is Chris's approval of them.

An attractive, functional interface (decide T8): a landing page that
explains bring-your-own-key and typical costs in plain words; connect a key;
start a run from a topic with guidance and budget; watch progress, stage
verdicts and spend live (the ledger); read the paper with evidence links;
stop or resume a run. No maintainer key in any shipped artifact.
Exit: a new user completes S4 through the app with their own key (MOE-4).

## Increment 6 — Optional: P1 on external papers

The auditor on other people's papers: PDF ingest, claim extraction,
leakage checks, re-runs, seeded-fault dev/test sets, a batch audit of the
ScientistTwo corpus, and the portfolio papers (judge benchmark; independent
audit of an AI-generated corpus). Taken up only if Increments 2-5 are done.
