# CONTRACT — VERA

Scope contract for Meridian's `confirmed` gate. Short by design: the detail
lives in `docs/`, and this file must not contradict it. If they disagree,
`docs/` wins and this file gets fixed.

## Purpose

Make AI-generated research **verifiable** and **affordable**:

- **P2 Judge library** — cheap-by-default judging of bounded decisions with
  LLM escalation and a cost/latency/confidence ledger.
- **P1 Integrity auditor** — checks a paper's citations, numeric claims,
  method–code alignment, leakage, and novelty, built on P2.
- **P3 Budgeted research agent** — a ScientistTwo-style loop under a hard
  budget, gated by P2 and audited by P1.

Build order: P2 → P1 → P3. Details: [docs/01-conops.md](docs/01-conops.md).

## Users

Agent builders (P2), reviewers and researchers adopting methods (P1),
independent researchers and small labs (P3). See ConOps §2.

## Scope

**Current increment: Increment 0 — know your data** ([docs/07-increments.md](docs/07-increments.md)).
Only Increment 0 work is in scope until its review (`docs/reviews/incr-0.md`)
confirms Increment 1. [SPEC.md](SPEC.md) lists the Increment 0 deliverables.

In scope for the project as a whole: the three layers above, their data
contracts ([docs/03-interfaces.md](docs/03-interfaces.md)), and the
verification plan ([docs/06-verification-plan.md](docs/06-verification-plan.md)).

## Deployment (where it runs and publishes)

Runs on Chris's Windows workstation, with optional on-demand cloud GPU and
model APIs within the monthly spend ceiling. Publishes code and results to
the public GitHub repo, papers to arXiv or workshops, and a public results
table for the batch audit (ConOps S3), never the corpus PDFs themselves.

## Out of scope

- Hosting a public multi-user service.
- Non-ML research domains, wet-lab work, or proprietary data.
- Judging long-form open-ended quality (P2 targets bounded decisions).
- Re-hosting or committing corpus PDFs (evaluation use only; `data/raw/` is git-ignored).
- Building a general "ScientistTwo clone": P3 is limited to 2 parent problems (risk R6).

## Acceptance criteria

Project-level measures of effectiveness (ConOps §6):

- **MOE-1** Auditor catches planted faults a human reviewer would care about
  (per-type detection and false-positive rates, requirement AUD-P-01).
- **MOE-2** Judge library cuts judge cost substantially with negligible
  decision-quality loss (threshold curve, JDG-P-01).
- **MOE-3** Research agent achieves a meaningful fraction of ScientistTwo's
  gain on the same parent problem at a small fraction of its cost (RSH-P-02).

The numeric targets behind these (JDG-P, AUD-P, RSH-P) are deliberately TBD
until baseline data exists (docs/02); each increment review sets the ones its
data supports. Increment 0 exit criteria are in [SPEC.md](SPEC.md). Every requirement due in
the current increment with verification method **T** has a test named
`test_<REQ_ID>_…` (checked by `tools/checks/check_traceability.py`).

## Constraints

- Monthly spend ceiling: see ConOps §4 (must be set before `confirmed` passes).
- Python 3.11+, `uv`, Pydantic v2, pytest. Schemas follow docs/03 exactly.
- No self-grading: a component never issues the verdict on its own artifact.
- Personal project: no employer data or systems.
