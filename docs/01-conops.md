# 01 — Concept of Operations

Version 0.2 · Draft (0.2, 2026-10-01: product direction B, decided by Chris: a topic goes in, a
paper-shaped write-up comes out; app with bring-your-own-key)

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
| Independent researcher, student, small lab | Turn a research topic into a paper-shaped write-up (literature review, experiments where the topic allows, honest results) for tens of dollars, using their own model key | P3 + app |
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

**S4 — Topic to paper (P3, the headline product).** A researcher opens the
app, connects their own model key, enters a topic ("explainability of tree
ensembles under correlated features"), gives output guidance (target format,
length, emphasis, constraints) and a budget ("$30, 6 h"). VERA scopes the
topic into a researchable question and shows it for confirmation, surveys
the literature (retrieval, reading, synthesis with verified citations), and,
where the question is empirical and a CPU-scale baseline exists, picks a
parent problem, reproduces the baseline on a subset, screens ideas and runs
the best with ablations. It drafts a paper-shaped write-up and passes it
through the auditor (citations, numbers against the run's own logs). The
user watches progress and spend live. On budget exhaustion it stops and
reports best-so-far honestly. Where the topic is not empirical, the output
is a literature-and-analysis paper without experiments.

**S4a — Chosen parent problem (P3, the measured comparison).** As S4, but the
user names a parent problem directly (as ScientistTwo does); used to
compare cost and quality with ScientistTwo on the same problems (MOE-3).

**S6 — First visit (app).** A visitor reads the landing page, which says in
plain words that VERA uses the visitor's own model key and budget, never the
maintainer's, and what a run typically costs. They connect a key (or the
local app reads it from their environment) and start a run.

**S5 — Benchmark judges (P2).** Run the judge benchmark across backends and
thresholds; publish agreement, calibration, consistency, cost, latency curves.

## 4. Operating envelope (initial)

- Single developer, local Windows workstation + optional cloud GPU on demand.
- Model access via API (frontier + cheap tiers) and optional local models.
- Monthly spend ceiling: **$20.00** (set 2026-09-29; confirmed for Increment 2 at the Increment 1
  review, 2026-10-01; revisit at each increment review).
  Months with loop runs (Increment 2 onward) may need a deliberate, temporary
  increase, set from the Increment 1 cost measurements (risk R10).
- Model access for spend under that ceiling: one OpenRouter API key, with
  cheap, capable models as defaults (e.g. MiMo-V2.6-Pro, GLM-5.3 Flash,
  DeepSeek V4.1 Flash), chosen with the OpenRouter rankings
  (<https://openrouter.ai/rankings#benchmarks>) and confirmed by VERA's own
  benchmarks. The key lives in a git-ignored `.env`.
- Inputs: PDFs, public Git repos. Outputs: JSON reports + rendered HTML/MD.

## 5. Out of scope (for now)

- Paying for other people's runs. VERA runs with the user's own model key
  (bring-your-own-key); no maintainer key ships in the repo or any deployed
  artifact. Whether a hosted demo exists, and how its compute is capped, is
  trade T8.
- Non-ML research domains requiring wet-lab or proprietary data.
- Judging long-form open-ended quality (P2 targets bounded decisions; LLM
  escalation handles the rest).

## 6. Measures of effectiveness (what users care about)

- MOE-1: Auditor catches planted faults a human reviewer would care about.
- MOE-2: Judge library cuts judge cost substantially with negligible
  decision-quality loss.
- MOE-3: Research agent achieves a meaningful fraction of ScientistTwo's gain
  on the same parent problem at a small fraction of its cost.
- MOE-4: A new user goes from a topic to a paper-shaped write-up through the
  app, with their own key, inside the budget they set, and judges the
  result worth reading.
