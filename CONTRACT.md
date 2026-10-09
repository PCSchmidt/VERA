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
- **P3 Budgeted research agent** — topic in, paper-shaped write-up out: a
  ScientistTwo-style loop under a hard budget, with a literature stage,
  gated by P2 and audited by P1, delivered through an app where users bring
  their own model key.

Headline product: P3, research from a topic to a paper-shaped write-up at a
small fraction of ScientistTwo's cost, with P2 critics gating every stage
and P1 as the final gate (direction B, decided by Chris 2026-10-01). Build
order: P2 first, a thin P3 loop on one problem in Increment 2, then the
topic front end, paper quality and the app (docs/07). Details:
[docs/01-conops.md](docs/01-conops.md).

## Users

Agent builders (P2), reviewers and researchers adopting methods (P1),
independent researchers and small labs (P3). See ConOps §2.

## Scope

**Increments 0 to 5 are complete** ([docs/reviews/incr-0.md](docs/reviews/incr-0.md), [incr-1](docs/reviews/incr-1.md), [incr-2](docs/reviews/incr-2.md),
[incr-3](docs/reviews/incr-3.md), [incr-4](docs/reviews/incr-4.md), [incr-5](docs/reviews/incr-5.md); Increment 5 passed 2026-10-09 with MOE-4 not shown).
No increment is currently scoped: the next is chosen by the owner from the candidates in the Increment 5 review (an independent walkthrough, a labelled
synthesis section, experiments in the app, Increment 6 on external papers). [SPEC.md](SPEC.md) is the Increment 5 SPEC until the next increment is scoped.

In scope for the project as a whole: the three layers above, their data
contracts ([docs/03-interfaces.md](docs/03-interfaces.md)), and the
verification plan ([docs/06-verification-plan.md](docs/06-verification-plan.md)).

## Deployment (where it runs and publishes)

Runs on Chris's Windows workstation, with optional on-demand cloud GPU and
model APIs within the monthly spend ceiling. Publishes code and results to
the public GitHub repo, papers to arXiv or workshops, and a public results
table for the batch audit (ConOps S3), never the corpus PDFs themselves.

## Out of scope

- Paying for other people's runs: VERA uses the user's own key (BYOK); no
  maintainer key in the repo or any deployed artifact (APP-C-01; hosting is trade T8).
- Non-ML research domains, wet-lab work, or proprietary data.
- Judging long-form open-ended quality (P2 targets bounded decisions).
- Re-hosting or committing corpus PDFs (evaluation use only; `data/raw/` is git-ignored).
- Experiments beyond CPU-scale problems, and a measured ScientistTwo comparison
  on more than 2 parent problems (RSH-P-02, risk R6).

## Acceptance criteria

Project-level measures of effectiveness (ConOps §6):

- **MOE-1** Auditor catches planted faults a human reviewer would care about
  (per-type detection and false-positive rates, requirement AUD-P-01).
- **MOE-2** Judge library cuts judge cost substantially with negligible
  decision-quality loss (threshold curve, JDG-P-01).
- **MOE-3** Research agent achieves a meaningful fraction of ScientistTwo's
  gain on the same parent problem at a small fraction of its cost (RSH-P-02).
- **MOE-4** A new user goes from a topic to a paper-shaped write-up through
  the app, with their own key, inside their budget (APP-F-01/02).

The numeric targets behind these (JDG-P, AUD-P, RSH-P) are deliberately TBD
until baseline data exists (docs/02); each increment review sets the ones its
data supports. The deliverables and acceptance tests of the latest scoped increment are in [SPEC.md](SPEC.md). Every requirement due in
the current increment with verification method **T** has a test named
`test_<REQ_ID>_…` (checked by `tools/checks/check_traceability.py`).

## Constraints

- Monthly spend ceiling: see ConOps §4 (must be set before `confirmed` passes).
- Python 3.11+, `uv`, Pydantic v2, pytest. Schemas follow docs/03 exactly.
- No self-grading: a component never issues the verdict on its own artifact.
- Personal project: no employer data or systems.
