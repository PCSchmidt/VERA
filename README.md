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
| P3 | **Budgeted research agent** | Meridian extended into a ScientistTwo-style loop (ideas → subset experiments → ablations → write-up) under a hard budget. Uses P2 for every critic gate and P1 as the final gate. | Independent researchers and small labs |

Numbering follows the original discussion. **Build order:** P2 first (cheap
critics make a cheap loop possible), then a thin end-to-end P3 loop on one
problem (Increment 2) gated by P2 critics with a minimal P1 as its final gate.
P1 and P3 then deepen together. The headline product is P3: a
ScientistTwo-style research loop at a small fraction of the cost, whose
every step is checked by something other than the step that produced it.

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

## Docs

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Working instructions for Claude Code in this repo |
| `docs/01-conops.md` | Users, scenarios, operating envelope |
| `docs/02-requirements.md` | Requirements with verification methods |
| `docs/03-interfaces.md` | Core schemas v0.7 (the contracts) |
| `docs/04-trade-studies.md` | Design decisions (T3 decided; T1, T2 in Increment 1) |
| `docs/05-risk-register.md` | Top risks and mitigations |
| `docs/06-verification-plan.md` | V&V strategy incl. seeded-fault testing |
| `docs/07-increments.md` | Increment plan with exit criteria; Increment 0 task list |
| `docs/meridian-dogfood.md` | Findings about Meridian, the build harness, from building VERA |
| `data/corpus_inventory.csv` | Corpus inventory: 86 generated papers and their parents (see `data/README.md`) |
| `data/benchmark/` | Increment 1 judge benchmark: split, test hash, label checks (items rebuild locally; see `data/README.md`) |
| `docs/reviews/` | Increment reviews (`incr-0.md`) |

## Status

Increment 0 (know your data) complete 2026-09-30: corpus of 86 ScientistTwo
papers mapped to their parents, parser chosen (T3), Increment 2 problem
chosen (TreeHFD); see `docs/reviews/incr-0.md`.

Increment 1 (P2 minimum viable judge, `SPEC.md`) is in progress. Built so
far: ledger and metered calls, judge parsing, router, five backends through
OpenRouter and TypeSafe's API (smoke run: 50 calls, $0.04), LangGraph
helpers with checkpoint/resume, and a 179-item benchmark labelled by
construction. Next: Chris's label check, then the benchmark run and the T1/T2
decisions. Progress: `bash scripts/gate-engine.sh current`.

## License

MIT (see `LICENSE`) for VERA's code and docs. It does not cover the ScientistTwo papers or any other third-party material VERA evaluates; those are never committed (`data/raw/` is git-ignored).
