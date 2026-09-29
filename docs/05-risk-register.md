# 05 — Risk register

Likelihood (L) and impact (I): 1 low – 3 high. Score = L × I. Review monthly.

| ID | Risk | L | I | Score | Mitigation | Trigger / watch |
|----|------|---|---|-------|------------|-----------------|
| R1 | Codebases for the 86 papers aren't public, limiting method–code and re-run checks | 2 | 3 | 6 | Increment 0 inventory settles this. Fall back to citation, numeric-consistency and novelty checks, plus parent-paper repos. | Inventory shows <25% code availability |
| R2 | Time competes with JHU coursework and work | 3 | 2 | 6 | Small increments with hard exit criteria; P2 is useful on its own if P1/P3 slip. | Two increments slip in a row |
| R3 | Judge benchmark lacks ground-truth labels | 2 | 2 | 4 | Seeded faults (labels come free) plus a small hand-labeled gold set; reference-judge agreement as a secondary signal. | Gold set < 20 items by end of Incr 1 |
| R4 | Jev pricing, API, or terms change | 2 | 2 | 4 | `JudgeBackend` abstraction; keep a local-model backend working at all times. | Terms forbid published comparisons |
| R5 | Re-running experiments is too expensive | 2 | 2 | 4 | Re-runs optional and budget-gated; choose CPU-scale parent problems for P3. | Any single re-run > per-audit budget |
| R6 | Scope creep (the thin loop grows into a full ScientistTwo clone) | 2 | 3 | 6 | Increment 2 loop is one problem and crude by design; its gates are P2 critics and a minimal P1; at most 2 problems before the Increment 5 review; the harness and measurements stay the deliverable. | Increment 2 work goes beyond its exit criteria, or a second problem starts before Increment 5 |
| R7 | Copyright / redistribution of corpus PDFs | 1 | 2 | 2 | Evaluation use only; store locally, never re-host; publish findings and links. | — |
| R8 | Publishing critical audit findings about named authors' work | 2 | 2 | 4 | Report aggregate results; state methods and error rates; contact authors before publishing paper-specific failures. | First "red" audit on a named paper |
| R9 | Conflict with employer outside-work / IP terms | 1 | 3 | 3 | Check the agreement before publishing; personal hardware and accounts only. | Before first public release |
| R10 | Loop runs don't fit the $20/month spend ceiling | 2 | 2 | 4 | Minutes-long CPU-scale experiments; hard `Budget`; cheap critics gate expensive calls; estimate one run's cost from Increment 1 measurements; raise the ceiling for run months deliberately, not by overrun. | Projected cost of one loop run > 50% of the monthly ceiling |
