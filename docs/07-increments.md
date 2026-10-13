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

Result (docs/reviews/incr-5.md): a local app takes a topic to an audited, downloadable literature review on the user's own key; it ran end to end on real topics and its first live runs found two
defects that tests had not. T8 decided (local only); a static read-only showcase is published on GitHub Pages. **MOE-4 is not shown**: the one walkthrough was the builder. Review quality did not
demonstrably improve (the blind human scores averaged 4.27 over three reviews, the independent scorer's 2.93), and the independent scorer found defects in reviews that had passed a green audit.
Experiments are not started from the app. The review passed the Evaluator on round 2 (7.8).

## Increment 6 — From a review to a paper (scoped 2026-10-11; complete 2026-10-12)

Scope, gates and caps proposed in SPEC.md (2026-10-11); `incr6_scoped` is Chris's approval of them.

A "Make a paper from this review" button on a finished review: the paper stage widens the evidence (more papers read in
full, more passages per paper; no new search), writes a review paper (abstract, introduction, method from the run's
files, findings by theme with every claim quoted, threats to validity), and adds labelled interpretation sections
(discussion, conclusions, research agenda) whose every statement names the verified claims it rests on and is judged by
a component other than its writer to follow from them (decided by Chris 2026-10-11). The audit says what a green light
covers on a paper; the inference check is measured on a seeded set frozen before its test run. No frozen audit file is
changed.
Exit: three papers made through the app from real reviews within their caps, each audited; the inference check's
detection and false-positive rates reported; both scorers' blind scores for each paper beside its review.

Result (docs/reviews/incr-6.md): three papers made through the app by Chris with his own key ($0.53 to $0.77 each, all green); both scorers
preferred the paper to its review in five of six judgements (independent mean 3.17, Chris 3.94). The inference check caught 48 of 48 planted
faults, but the faults were blatant and written by the check's author; in the live papers the external review and the independent scorer found
cited claims saying more than their quotes, wrong uncited synthesis and overreaching interpretation under green audits. No frozen file changed.

## Increment 7 — Check what the green light does not (proposed 2026-10-13)

Scope, gates and caps proposed in SPEC.md (2026-10-13); `incr7_scoped` is Chris's approval of them.

Increment 6's papers audited green while cited claims said more than their quotes, uncited synthesis sentences were wrong,
interpretation overreached and repeated quotes read as corroboration (docs/reviews/incr-6.md). This increment gives every
sentence of an evidence section a status (claim, synthesis, transition), checks synthesis like interpretation and transitions for
facts, adds a judge question on whether a claim says more than its quote, and cheap rules (agreement needs two sources; absence
statements belong to the record; "X and colleagues" names a source; a quote that leans on context is widened; one quote, one claim
id). The audit lists every sentence. A targeted search looks up works the paper names but did not retrieve. The checks are measured
on real text from the Increment 6 papers, labelled by Chris and frozen before the test run, old checks beside new. No frozen audit
file is changed; the review and the paper share the new checks.
Exit: the real-case results reported for old and new checks; the three Increment 6 papers re-audited; two papers made through the
app with the new checks, each audited; the independent scorer's defect counts for them beside Increment 6's.

## Increment 8 — Optional: P1 on external papers (was Increment 6 until 2026-10-11, Increment 7 until 2026-10-13)

The auditor on other people's papers: PDF ingest, claim extraction,
leakage checks, re-runs, seeded-fault dev/test sets, a batch audit of the
ScientistTwo corpus, and the portfolio papers (judge benchmark; independent
audit of an AI-generated corpus). Increments 2-5 are done; the labelled synthesis section became Increment 6 (Chris, 2026-10-11), and checking every sentence became Increment 7
(proposed 2026-10-13). Whether to take this up, or an independent walkthrough or experiments in the app first, is the owner's decision (candidates in docs/reviews/incr-5.md).
