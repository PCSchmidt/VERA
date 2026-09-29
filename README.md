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

Numbering follows the original discussion; **build order is P2 → P1 → P3.**

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
| `docs/03-interfaces.md` | Core schemas v0.1 (the contracts) |
| `docs/04-trade-studies.md` | Open design decisions |
| `docs/05-risk-register.md` | Top risks and mitigations |
| `docs/06-verification-plan.md` | V&V strategy incl. seeded-fault testing |
| `docs/07-increments.md` | Increment plan with exit criteria; Increment 0 task list |
| `data/corpus_inventory.csv` | Template for the Increment 0 corpus inventory |

## Status

Increment 0 (spike): not started.
