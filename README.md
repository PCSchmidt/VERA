# VERA — Verifiable, Economical Research Agents

> Working name. Rename freely; nothing depends on it.

**Thesis:** make AI-generated research *verifiable* and *affordable*.

Autonomous research agents now write papers that clear automated review bars
(e.g. [ScientistTwo](https://scientist-two.github.io/), Google Cloud AI
Research: 86 generated papers, ~$3,800 and 2–3 days per task, as stated on
the site when retrieved 2026-09-29). Two
gaps follow: nobody independent checks whether those papers are true, and
almost nobody can afford to run such systems. VERA addresses both with three
layered projects.

## The three projects

| # | Project | What it is | Primary users |
|---|---------|------------|---------------|
| P2 | **Judge library** | Cheap-by-default judging: split a judgment into atomic questions, answer with a cheap backend (typed decision model / small model), escalate to an LLM below a confidence threshold. Logs cost, latency, confidence for every decision. | Anyone building agents that route, gate, grade, or approve |
| P1 | **Integrity auditor** | Takes a paper (+ repo if available) and produces an audit: citations, numeric claims, method–code alignment, spec violations / leakage, novelty. Built on P2. | Reviewers, workshop organizers, researchers adopting published methods |
| P3 | **Budgeted research agent** | Topic in, paper-shaped write-up out: scoping, literature review with verified citations, and a ScientistTwo-style experiment loop (ideas → subset experiments → ablations → write-up) on CPU-scale problems, under a hard budget. P2 gates every stage; P1 is the final gate. Delivered through an app where users bring their own model key. | Independent researchers, students, small labs |

Numbering follows the original discussion. **Build order:** P2 first (cheap
critics make a cheap loop possible), then a thin end-to-end P3 loop on one
problem (Increment 2) gated by P2 critics with a minimal P1 as its final gate,
then the topic front end and literature stage, paper quality, and the app
(Increments 3-5). The headline product is P3: research from a topic to a
paper-shaped write-up at a small fraction of ScientistTwo's cost, whose
every step is checked by something other than the step that produced it.
Users bring their own model key; VERA never spends the maintainer's.

## Architecture (layers)

```
┌──────────────────────────────────────────────────────────┐
│ P3  Research agent   experiment loop · budget · write-up │
├──────────────────────────────────────────────────────────┤
│ P1  Integrity auditor  claim extraction · checks · report│
├──────────────────────────────────────────────────────────┤
│ P2  Judge library   question split · cheap-first router  │
│                     · LLM escalation · calibration log   │
├──────────────────────────────────────────────────────────┤
│ Foundation  durable runtime (LangGraph) · sandbox ·      │
│             cost/trace ledger · paper corpus             │
└──────────────────────────────────────────────────────────┘
```

Layers connect through **data contracts** (see `docs/03-interfaces.md`), not
shared internals. Every judgment anywhere in the system is a `Verdict`.

## Try it: the local app

VERA runs on your own computer with **your own** OpenRouter key and your own money. The maintainer pays nothing and has no
access to your key or your runs; the key is held in the program's memory and is never written to a file, a log or a run record.

You need Python 3.11 or later and [uv](https://docs.astral.sh/uv/). Then:

```
git clone https://github.com/PCSchmidt/VERA.git
cd VERA
uv sync
uv run vera-app
```

Open http://127.0.0.1:8765, press **Connect my key**, paste an OpenRouter key (get one in your OpenRouter account, under Keys, and
add a small credit), and start a run. VERA proposes a question for you to confirm, then searches, reads, writes a review with each
claim tied to a quote, audits it and shows you the audit. You set a spending cap on every run; VERA stops before passing it.

Optional: Docker, with the GROBID image running on port 8070 (`docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.2`; on WSL2 add
`-e JAVA_TOOL_OPTIONS=-XX:-UseContainerSupport`), lets VERA read full texts; without it, it reads abstracts and says so. A `SEMANTIC_SCHOLAR_API_KEY` or `OPENALEX_API_KEY` in a `.env` file
adds paper-search sources. Experiments (a parent paper's code re-run in a sandbox) are not started from the app yet; see `docs/`.

## Docs

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Working instructions for Claude Code in this repo |
| `docs/01-conops.md` | Users, scenarios, operating envelope |
| `docs/02-requirements.md` | Requirements with verification methods |
| `docs/03-interfaces.md` | Core schemas v0.7 (the contracts) |
| `docs/04-trade-studies.md` | Design decisions (T1, T2, T3 decided; T4-T8 open) |
| `docs/05-risk-register.md` | Top risks and mitigations |
| `docs/06-verification-plan.md` | V&V strategy incl. seeded-fault testing |
| `docs/07-increments.md` | Increment plan with exit criteria; Increment 0 task list |
| `docs/meridian-dogfood.md` | Findings about Meridian, the build harness, from building VERA |
| `data/corpus_inventory.csv` | Corpus inventory: 86 generated papers and their parents (see `data/README.md`) |
| `data/benchmark/` | Increment 1 judge benchmark: split, test hash, label checks (items rebuild locally; see `data/README.md`) |
| `docs/reviews/` | Increment reviews (`incr-0.md`, `incr-1.md`) |

## Status

Increment 0 (know your data) complete 2026-09-30: corpus of 86 ScientistTwo
papers mapped to their parents, parser chosen (T3), Increment 2 problem
chosen (TreeHFD); see `docs/reviews/incr-0.md`.

Increment 1 (P2 minimum viable judge) built the ledger, judge parsing,
router, six backends (OpenRouter, TypeSafe Jev, a local model through
Ollama), LangGraph helpers with checkpoint/resume, and a 179-item benchmark
labelled by construction. The benchmark run (6,095 verdicts, $1.61) decided
T1: Jev escalating to GLM-5.3 Flash agrees with the reference judge at
about 1-2% of its cost (`docs/figures/threshold_curve.png`). The product
direction is now topic to paper with an app and bring-your-own-key
(docs/07). Review: `docs/reviews/incr-1.md`. Progress:
`bash scripts/gate-engine.sh current`.

## License

MIT (see `LICENSE`) for VERA's code and docs. It does not cover the ScientistTwo papers or any other third-party material VERA evaluates; those are never committed (`data/raw/` is git-ignored).
