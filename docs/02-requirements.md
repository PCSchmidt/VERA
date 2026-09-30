# 02 — Requirements

Version 0.2 · Draft (0.2, 2026-09-30, Increment 0 review: RSH-P-02 set to 2; AUD-F-05 scoped to code the checker can access)

ID format: `<AREA>-<TYPE>-<NN>`. Areas: `FND` foundation, `JDG` judge library
(P2), `AUD` auditor (P1), `RSH` research agent (P3). Types: `F` functional,
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
| JDG-P-01 | At default threshold, agreement with the reference judge shall be ≥ **TBD** [95%] at ≤ **TBD** [25%] of reference cost. | A | 1 |
| JDG-P-02 | Cheap-path p50 latency ≤ **TBD** [1 s]. | A | 1 |
| JDG-P-03 | Repeated-run verdict flip rate ≤ **TBD** [2%] for the cheap path. | A | 1 |

## P1 — Integrity auditor

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| AUD-F-01 | Ingest a paper PDF (and optionally a repo URL) and produce an `AuditReport`. | T | 3 |
| AUD-F-02 | Extract numeric claims with location (section, table, page). | T | 3 |
| AUD-F-03 | Flag every reference that cannot be matched in a bibliographic source (e.g. Crossref, arXiv, Semantic Scholar). | T (seeded) | 2–3 |
| AUD-F-04 | Check each numeric claim for internal consistency (text vs. tables vs. figures) and, when logs exist, against logged outputs. | T (seeded) | 2–3 |
| AUD-F-05 | Check method–code alignment: each method component described in the paper maps to code, and vice versa. Scope: papers whose code is available to the checker (VERA's own loop outputs; parent repositories as reference). Not applied to the ScientistTwo corpus, which publishes no generated code (Increment 0 review). | T (seeded) | 4 |
| AUD-F-06 | Detect specification violations / leakage patterns (test-set use in training or tuning, metric changes, baseline misconfiguration). | T (seeded) | 4 |
| AUD-F-07 | Assess novelty: retrieve closest prior work and judge whether the core method is materially distinct. | A (gold set) | 4 |
| AUD-F-08 | Optionally re-run reported experiments in the sandbox within a per-audit budget. | D | 4 |
| AUD-F-09 | Every finding shall link to its evidence (quote location, source record, code path, log line). | I | 2 |
| AUD-P-01 | Detection rate on seeded faults ≥ **TBD** [90%] per check type; false-positive rate ≤ **TBD** [10%]. | T | 3–4 |
| AUD-P-02 | Non-rerun audit cost ≤ **TBD** [$1] and wall time ≤ **TBD** [15 min] per paper. | A | 3 |

## P3 — Research agent

| ID | Requirement | Verify | Incr |
|----|-------------|--------|------|
| RSH-F-01 | Accept a problem spec (parent paper + baseline code), output guidance (e.g. target format, length, emphasis, constraints), and a `Budget`. | T | 2 |
| RSH-F-02 | Reproduce the baseline on a subset before testing any idea. | T | 2 |
| RSH-F-03 | Every stage transition shall be gated by a `Verdict` from a component other than the producer (no self-grading). | T, I | 2 |
| RSH-F-04 | Run ablations on the best idea before write-up. | D | 5 |
| RSH-F-05 | Pass the final write-up through the P1 auditor (minimal in Increment 2: citations + numbers vs run logs); failing audits block "success". | T | 2 |
| RSH-F-06 | On budget exhaustion, stop and emit a best-so-far report stating the stop reason. | T | 2 |
| RSH-F-07 | The write-up shall follow the run's output guidance; the final gate checks it. | T | 2 |
| RSH-P-01 | A run shall never exceed its configured budget. | T | 2 |
| RSH-P-02 | Report cost/quality results on ≥ **2** parent problems also attempted by ScientistTwo (set at the Increment 0 review; matches R6's limit of 2 problems before Increment 5). | A | 5 |

## Traceability

Tests reference requirement IDs in their names. A requirement is "verified"
when its test passes in CI or its analysis is written up in `docs/results/`.
