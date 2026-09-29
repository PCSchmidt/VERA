# 01 — Concept of Operations

Version 0.1 · Draft

## 1. Problem

Autonomous research agents can now produce papers that pass automated review.
ScientistTwo reports 86 papers beating human state-of-the-art on 107 problems
drawn from accepted NeurIPS/ICLR/ICML papers, at ~$3,800 and 2–3 days per task.
Its integrity was verified by its own authors. Two needs are unmet:

1. **Independent verification** — readers cannot cheaply tell whether an
   AI-generated (or any) paper's claims, citations, and code hold up.
2. **Affordability** — the cost puts autonomous research out of reach for
   independent researchers and small labs.

A cross-cutting enabler: most judgments inside these systems are small,
bounded decisions that are currently made by expensive, non-deterministic
LLM calls.

## 2. Users

| User | Need | Project |
|------|------|---------|
| Agent builder | Cheaper, consistent, observable judge/gate decisions | P2 |
| Reviewer / workshop organizer | Fast first-pass trust check on submissions | P1 |
| Researcher adopting a method | "Does this actually work as described?" | P1 |
| Independent researcher / small lab | Run an autonomous research loop within a fixed budget | P3 |
| Chris (portfolio) | Demonstrable, measured systems + papers | all |

## 3. Operational scenarios

**S1 — Gate a decision (P2).** An agent needs to decide "is this output
grounded in the source?" It sends a `Question` + state to the judge. A cheap
backend answers with confidence 0.93 → accepted in <1 s. A different case
returns 0.55 → escalated to an LLM judge. Both decisions appear in the ledger
with cost and latency.

**S2 — Audit a paper (P1).** A reviewer submits a PDF and a repo URL. The
auditor extracts claims and references, runs checks, and returns a report
with a red/amber/green summary and linked evidence in ≤15 min for ≤ $1
(targets TBD in requirements). Experiment re-runs are optional and
budget-gated.

**S3 — Batch audit (P1).** Run the auditor over the 86 ScientistTwo papers
and a sample of their parent papers; produce a public results table.

**S4 — Budgeted research run (P3).** A researcher selects a parent problem and
sets a budget ("$30, 6 h"). The agent reproduces the baseline on a subset,
screens ideas, runs ablations, drafts a write-up, and passes it through the
auditor. On budget exhaustion it stops and reports best-so-far honestly.

**S5 — Benchmark judges (P2).** Run the judge benchmark across backends and
thresholds; publish agreement, calibration, consistency, cost, latency curves.

## 4. Operating envelope (initial)

- Single developer, local Windows workstation + optional cloud GPU on demand.
- Model access via API (frontier + cheap tiers) and optional local models.
- Monthly spend ceiling: **TBD** (suggest setting one before Increment 1).
- Inputs: PDFs, public Git repos. Outputs: JSON reports + rendered HTML/MD.

## 5. Out of scope (for now)

- Hosting a public multi-user service.
- Non-ML research domains requiring wet-lab or proprietary data.
- Judging long-form open-ended quality (P2 targets bounded decisions; LLM
  escalation handles the rest).

## 6. Measures of effectiveness (what users care about)

- MOE-1: Auditor catches planted faults a human reviewer would care about.
- MOE-2: Judge library cuts judge cost substantially with negligible
  decision-quality loss.
- MOE-3: Research agent achieves a meaningful fraction of ScientistTwo's gain
  on the same parent problem at a small fraction of its cost.
