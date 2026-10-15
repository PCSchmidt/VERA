# 02 — Requirements

Version 0.11 · Draft (0.2, 2026-09-30, Increment 0 review: RSH-P-02 set to 2; AUD-F-05 scoped to code the checker can access. 0.3, 2026-10-01: JDG-P-01..03 set from the Increment 1 benchmark; direction B: topic-to-paper and app requirements added, external-paper auditing moved to Increment 6. 0.4, 2026-10-02, Increment 2 review: measurements recorded beside AUD-P-01 and AUD-P-02; no target value changed. 0.5, 2026-10-02, Increment 3 SPEC: AUD-F-10 added, claim-to-source support check. 0.6, 2026-10-09, Increment 5 review: APP-F-03 (a downloadable PDF with its evidence) and APP-C-03 (the server answers only this computer) added; both were built and tested in Increment 5. 0.7, 2026-10-11, Increment 6 SPEC: RSH-F-12 to RSH-F-14, AUD-F-11 and APP-F-04 added (a review paper made from a finished review, with labelled, judge-checked interpretation); external-paper auditing (AUD-F-01, -02, -06, -08, AUD-P-01, -02) renumbered to Increment 7. 0.8, 2026-10-13, Increment 7 SPEC: RSH-F-15, RSH-F-16 and AUD-F-12 added (every sentence of an evidence section has a checked status; a targeted search for works a paper names; the audit lists every sentence); external-paper auditing renumbered to Increment 8. 0.9, 2026-10-14, Increment 8 SPEC: JDG-F-07, JDG-P-04 and AUD-F-13 added (one judge route per question, the new questions measured against the reference, a judge disagreement reported as such); external-paper auditing renumbered to Increment 9. 0.10, 2026-10-14, Increment 9 SPEC: AUD-F-14 and RSH-F-17 added (a failure needs a confident no, an unsure judge is a warning; the write step confirms a cheap no with the reference); external-paper auditing renumbered to Increment 10. 0.11, 2026-10-15, Increment 10 SPEC (close-out): no new requirement; external-paper auditing renumbered to Increment 11 and marked not planned)

ID format: `<AREA>-<TYPE>-<NN>`. Areas: `FND` foundation, `JDG` judge library
(P2), `AUD` auditor (P1), `RSH` research agent (P3), `APP` app. Types: `F` functional,
`P` performance, `C` constraint.

Verification methods: **T** test · **A** analysis · **I** inspection ·
**D** demonstration.

Values marked **TBD** are set once the data that informs them exists:
inventory-driven values at the end of Increment 0 (e.g. RSH-P-02), judge
and auditor performance targets from the Increment 1–2 benchmarks.
Suggested starting values are in brackets.

## Foundation

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| FND-F-01 | Every model call shall write a ledger record with backend, model, input/output tokens, cost (USD), latency (ms), and trace ID. | T | 1 |
| FND-F-02 | Graph runs shall checkpoint after every node and resume from the last checkpoint after a crash. | T | 1 |
| FND-F-03 | Third-party or agent-generated code shall execute only inside the sandbox, with no network access unless explicitly granted per run. | T, I | 2 |
| FND-C-01 | No vendor model SDK shall be imported outside the `backends/` package. | I (lint rule) | 1 |
| FND-C-02 | Downloaded corpus files shall have provenance (URL, retrieval date, SHA-256) recorded. | T | 0 |

## P2 — Judge library

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| JDG-F-01 | The library shall accept a `Question` + state and return a `Verdict` for Choice, Score, and Boolean question types. | T | 1 |
| JDG-F-02 | The router shall try backends in configured cost order and escalate when confidence < threshold. | T | 1 |
| JDG-F-03 | The escalation threshold shall be configurable per question type and per call. | T | 1 |
| JDG-F-04 | The library shall support at least two backends at v0.1: one cheap (decision model or small local model) and one frontier LLM. | D | 1 |
| JDG-F-05 | The library shall expose LangGraph node and conditional-edge helpers. | D | 1 |
| JDG-F-06 | The benchmark harness shall report agreement, calibration (ECE), consistency across N repeats, cost, and latency per backend and threshold. | T | 1 |
| JDG-P-01 | The decided cheap path (T1: Jev → GLM-5.3 Flash at threshold 0.7; `loop.*` questions to GLM) shall agree with the reference judge on ≥ **97%** of verdicts at ≤ **5%** of reference cost. Measured 2026-10-01 (offline router replay, test split): 100% at 1.8%; Jev → GLM for every question 97.6% at 1.3%. Re-tested 2026-10-02 on the loop's real gate decisions: 97.4% (95% CI 91.0-99.3, 77 items) at 0.95% of the reference's cost per item; met on the point estimate only. | A | 1 |
| JDG-P-02 | Cheap-path p50 latency ≤ **0.5 s** (p95 ≤ 1.5 s), for questions on the default path. Loop-gate questions (`loop.*`), routed straight to GLM because they are few per run and nobody waits on them, have no latency target; their latency is reported. Measured (test split): default path p50 0.19 s, p95 0.36 s; loop gates p50 1.6 s, p95 8.6 s (Chris, 2026-10-01). | A | 1 |
| JDG-P-03 | Repeated-run verdict flip rate (items whose answer is not the same on every repeat) ≤ **2%** for the cheap path. Measured: decided path 0% (0/115 items on replay); Jev 1.7%, GLM 0.9%. | A | 1 |
| JDG-F-07 | The cheap path shall route a question by a per-question table when it has an entry (the backends that may answer it, in order), the same wherever the question is asked, and record on each verdict the backend that answered. | T | 8 |
| JDG-P-04 | Each judge question a green light rests on that was added after Increment 1 (`claim.within_quote`, `sentence.no_fact`, the clause-by-clause `paper.inference_follows`) shall be measured against the reference judge on a frozen set of real material, and its route shall meet JDG-P-01's agreement and JDG-P-03's flip-rate bars, or the review shall say it does not. | A | 8 |

## P1 — Integrity auditor

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| AUD-F-01 | Ingest a paper PDF (and optionally a repo URL) and produce an `AuditReport`. | T | 11 |
| AUD-F-02 | Extract numeric claims with location (section, table, page). | T | 11 |
| AUD-F-03 | Flag every reference that cannot be matched in a bibliographic source (e.g. Crossref, arXiv, Semantic Scholar). | T (seeded) | 2–3 |
| AUD-F-04 | Check each numeric claim for internal consistency (text vs. tables vs. figures) and, when logs exist, against logged outputs. | T (seeded) | 2–3 |
| AUD-F-05 | Check method–code alignment: each method component described in the paper maps to code, and vice versa. Scope: papers whose code is available to the checker (VERA's own loop outputs; parent repositories as reference). Not applied to the ScientistTwo corpus, which publishes no generated code (Increment 0 review). | T (seeded) | 4 |
| AUD-F-06 | Detect specification violations / leakage patterns (test-set use in training or tuning, metric changes, baseline misconfiguration). | T (seeded) | 11 |
| AUD-F-07 | Assess novelty: retrieve closest prior work and judge whether the core method is materially distinct (first applied to the loop's own idea). | A (gold set) | 4 |
| AUD-F-08 | Optionally re-run reported experiments in the sandbox within a per-audit budget. | D | 11 |
| AUD-F-09 | Every finding shall link to its evidence (quote location, source record, code path, log line). | I | 2 |
| AUD-F-10 | Every claim a document attributes to a retrieved source shall be checked against that source's text; an unsupported claim is a finding that carries the quote and the source passage as evidence. | T (seeded) | 3 |
| AUD-F-11 | In a paper, every interpretation statement shall name existing verified claims as its premises and be re-checked by the audit (deterministic rules and a judge on whether it follows); the audit result shall state that interpretation is judged, not quote-checked. | T (seeded) | 6 |
| AUD-F-12 | The audit of a review or a paper shall list every sentence of its evidence sections with its status and re-check each: claims (including whether a claim says more than its quote), synthesis (judged to follow from the claims it names) and transitions (no factual content); documents made before sentence statuses existed are audited by splitting them into sentences. | T | 7 |
| AUD-F-13 | When the audit's verdict on a sentence or statement contradicts the verdict recorded when it was written, the audit shall report a judge disagreement (a warning), not a failure; a failure needs a confident no in the audit and no confident yes at write time. | T | 8 |
| AUD-F-14 | A sentence or statement shall fail the audit only on a confident no from the judge of record (the reference where it was asked); an answer below the confidence threshold, either way, shall be reported as unsettled (a warning), not as a failure or a pass. | T | 9 |
| AUD-P-01 | Detection rate on seeded faults ≥ **TBD** [90%] per check type; false-positive rate ≤ **TBD** [10%]. Increment 2 measured (not a target): 17/18 on the test split, 0 false fails on 3 controls; mostly deterministic faults from two source runs, audit changed after the first test run, so it does not support a value (docs/reviews/incr-2.md). | T | 11 |
| AUD-P-02 | Non-rerun audit cost ≤ **TBD** [$1] and wall time ≤ **TBD** [15 min] per paper. Increment 2 measured (not a target): $0.00012 and about 1 s (`audit_report.json` `wall_seconds`) on the loop's own 674-word paper with 22 claims; external papers (Increment 6) are longer, so this does not support a value. | A | 11 |

## P3 — Research agent

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| RSH-F-01 | Accept a problem spec (parent paper + baseline code), output guidance (e.g. target format, length, emphasis, constraints), and a `Budget`. | T | 2 |
| RSH-F-02 | Reproduce the baseline on a subset before testing any idea. | T | 2 |
| RSH-F-03 | Every stage transition shall be gated by a `Verdict` from a component other than the producer (no self-grading). | T, I | 2 |
| RSH-F-04 | Run ablations on the best idea before write-up. | D | 4 |
| RSH-F-05 | Pass the final write-up through the P1 auditor (minimal in Increment 2: citations + numbers vs run logs); failing audits block "success". | T | 2 |
| RSH-F-06 | On budget exhaustion, stop and emit a best-so-far report stating the stop reason. | T | 2 |
| RSH-F-07 | The write-up shall follow the run's output guidance; the final gate checks it. | T | 2 |
| RSH-P-01 | A run shall never exceed its configured budget. | T | 2 |
| RSH-F-08 | Accept a research topic and propose a scoped research question (with why it is researchable and whether it is empirical), shown to the user for confirmation before any further spend beyond scoping. | T | 3 |
| RSH-F-09 | Produce a literature review section from retrieved sources, in which every citation resolves to a real record and every claim attributed to a source links to it. | T (seeded) | 3 |
| RSH-F-10 | For an empirical question, select a CPU-scale parent problem and baseline from the literature, or say why none fits and write a non-empirical paper instead. | D | 3 |
| RSH-F-11 | Produce a paper-shaped write-up (abstract, related work, method, results, limitations, references) that follows the output guidance. | D | 4 |
| RSH-F-12 | On request, turn a finished literature review into a review paper (abstract, introduction, method, findings by theme, threats to validity, references) in which every attribution is a verified claim and the method and threats sections are written from the run's own files, not by a model. | T | 6 |
| RSH-F-13 | A paper may contain interpretation sections (discussion, conclusions, research agenda), labelled as such and written from the verified claims only; every statement names the claims it rests on and is kept only if a component other than its writer judges that it follows from them. | T | 6 |
| RSH-F-14 | Before writing a paper, widen the evidence (more papers read in full, more passages per paper) without changing the review's passages or claims. | T | 6 |
| RSH-F-15 | Every sentence of an evidence section (review or paper) shall have a status: a claim sentence carrying verified claims, a synthesis naming the claims it rests on and judged by a component other than its writer to follow from them, or a transition stating no fact; a sentence failing its check is repaired once, then removed. | T | 7 |
| RSH-F-16 | When a paper's emphasis or question names a work not among the run's sources, look it up (at most 3 lookups), add its passages if found, and state in the threats section what was searched for and whether it was found. | T | 7 |
| RSH-F-17 | When writing, a confident no from a cheap judge on a question the audit confirms with the reference shall be confirmed with the reference before the sentence or statement is repaired or removed; one the reference accepts is kept, with both verdicts stored. | T | 9 |
| RSH-P-02 | Report cost/quality results on ≥ **2** parent problems also attempted by ScientistTwo (set at the Increment 0 review; R6 keeps the measured comparison at 2 problems; the second problem comes in Increment 4 since the direction-B re-plan). | A | 4 |

## App

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| APP-F-01 | The app shall let a user start a run from a topic with output guidance and a budget, watch stage progress, verdicts and spend live, stop or resume it, and read the result with evidence links. | D | 5 |
| APP-F-02 | Bring-your-own-key: every model call uses the user's own key, entered or connected from a landing page that explains in plain words whose key and money are used and what a run typically costs. | D, I | 5 |
| APP-C-01 | No maintainer API key shall be present in the repository, in any build or deployed artifact, or in logs; the app shall never fall back to one. | T, I | 5 |
| APP-C-02 | A user's key shall stay on the user's side (their machine or browser session): not written to VERA's logs, ledger or repository, and not stored server-side by a hosted deployment. | T, I | 5 |
| APP-F-03 | The app shall let a user download a review or paper as a PDF that carries its text, tables and figures, the audit result and, for every claim, its source and exact quote. | D | 5 |
| APP-C-03 | The app's server shall answer only requests addressed to this computer (host and origin), refuse cross-origin writes, and load nothing from outside the machine. | T | 5 |
| APP-F-04 | The app shall offer, on a finished review whose audit did not fail, a button that makes a review paper from it under its own cap, and show the paper beside the review, on screen and as a PDF, with interpretation visibly marked. | T | 6 |

## Traceability

Tests reference requirement IDs in their names. A requirement is "verified"
when its test passes in CI or its analysis is written up in `docs/results/`.
