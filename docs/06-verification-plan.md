# 06 — Verification & validation plan

**Verification** = did we build it right (meets requirements).
**Validation** = did we build the right thing (users find it useful).

## 1. Seeded-fault testing (primary method for P1)

Take real papers and plant known faults. Detection is then measured without
expert labeling. Build the fault set in `data/seeded/` with a manifest.

| Fault type | How to plant | Checks exercised |
|-----------|--------------|------------------|
| Fabricated citation | Add plausible fake references (real-looking authors/venues) | AUD-F-03 |
| Wrong citation attribution | Cite a real paper for a claim it doesn't make | AUD-F-03 (stretch) |
| Numeric mismatch | Change a number in text so it disagrees with its table; alter a table value vs. a log | AUD-F-04 |
| Method–code drift | Describe a component the code lacks, or remove a component from code | AUD-F-05 |
| Leakage | Modify code to tune on the test split or use test data in training | AUD-F-06 |
| Relabeled prior work | Rewrite a known published method's description under a new name | AUD-F-07 |

Manifest schema: `paper_id, fault_id, fault_type, location, description`.
Report per-type detection rate and false-positive rate on unseeded controls.

## 2. Gold set (validation)

20–30 papers audited by hand (start with 10 in Increment 2). Mix of
ScientistTwo papers and their parent papers. Used to check that findings
match what a careful human reviewer would flag, and for novelty (AUD-F-07),
where seeding is weaker.

## 3. Judge benchmark (P2)

- Tasks (Increment 1, `data/benchmark/`): the loop's gate decisions on
  generated TreeHFD result tables (beats baseline? best method? how many
  beat it?), numeric consistency of claims about corpus tables, and
  citation presence in corpus reference lists. Labels come from how each
  item was built (risk R3); Chris checks a seeded sample per task.
- Split: dev (tuning) and test (reporting), about 1:2 by source unit, with
  the test split's SHA-256 recorded before any backend sees it (§5).
- Reference: a frontier LLM (Claude Sonnet 5.5) alongside the labels.
- Metrics: agreement with labels and with the reference, ECE, flip rate
  over repeats (N = 10 cheap, 3 reference), cost, latency, escalation rate
  as a function of threshold.
- Output: threshold sweep plot (cost vs. agreement) — the core result.

## 4. Research agent (P3)

- Budget compliance tests (inject cost to force exhaustion).
- No-self-grading tests (producer_id ≠ judge_id enforced).
- Outcome: on each chosen parent problem, gain over baseline vs. cost,
  compared with ScientistTwo's published gain and ~$3.8k cost.

## 5. Independence

The evaluation data and the thresholds are fixed before a result is
reported. Don't tune the auditor on the same seeded set used to report its
detection rate — split seeded faults into dev and test.

## 6. User validation

Before calling P1 "done", have 2–3 people (e.g. JHU classmates) audit a
paper with and without the tool and say whether the report changed their
judgment.

## 7. As built (through Increment 5, 2026-10-09)

What the plan became, with where each result is recorded:

- **Seeded faults (§1).** Three sets were built, v1 (Increment 2), v2 (Increment 3) and v3 (Increment 4), under `data/seeded/`, `data/seeded_v2/`, `data/seeded_v3/`, each split dev and test by source
  with the test hash recorded first and the audit's source frozen by hash before its one test run (`check_seeded_v3.py`). The v3 test caught 50 of 52 planted faults and failed 3 of 6 unmodified controls
  (`docs/results/audit_v3_results.md`; v2: `seeded_v2.md`). The freeze was broken once, after the Increment 4 test runs, and the review says so.
- **Gold sets (§2).** A novelty gold set (`data/novelty_gold/`: published methods relabelled against unrelated ones, plus the loop's ideas) and a claim benchmark (`data/claim_bench/`: constructed and real claims,
  labelled by an AI helper, with a human re-label sample). A set of hand-audited papers (§2) was not built in these increments.
- **Judge benchmark and re-tests (§3).** The Increment 1 benchmark (`data/benchmark/`) and three re-tests on the loop's real gate decisions (`data/retest/`, `retest3/`, `retest5/`: 77, 24 and 150 items); the last is
  mostly perturbed items and says so.
- **Research agent (§4).** Budget and no-self-grading tests in the suite; the ScientistTwo comparison was made under a protocol hashed before the numbers were read (`docs/results/comparison_table.md`): not met.
- **Independence (§5).** Test sets are split and hashed first; the human's rubric scores are recorded blind and earlier than the independent scorer's (`check_rubric.py`, `check_rubric5.py`); provenance caveats are
  stated in the reviews. Every increment's review is passed by a fresh Evaluator with all verdicts kept.
- **The app (Increment 5).** Key safety is tested adversarially (a provider that echoes the key; a counterpart test removes the redaction and shows the leak), the server's host and origin rules, the pages in a
  headless browser against fixture runs, the PDF's text, tables and figures, and the static showcase build. No independent person has used it.
- **User validation (§6).** Not yet done with independent people. One walkthrough was recorded (`data/walkthrough/`), by the builder from a clean clone, and is marked not independent.

## 8. As built (Increments 6 to 10, 2026-10-11 to 2026-10-15; final)

- **Inference check (Increment 6).** A seeded set of 108 items (`data/seeded_inference/`), frozen before its one test run, caught 48 of
  48 judge-layer faults with 0 of 12 controls failed; the faults were written by the check's author and were blatant, which the review
  says limits what the result shows (`data/results/inference_incr6_*.json`).
- **Real-case set (Increment 7).** 140 items of real text from Increment 6's papers (`data/realcase/`), split by paper, hashed with
  their labels and the checks' source before the one test run: the old checks flagged 0 of 21 faulty items, the new ones 15. The test
  labels were chosen by an OpenAI assistant at Chris's request, not by Chris (`data/results/realcase_incr7_test.json`).
- **Judge set (Increment 8).** 275 items asking the new judge questions exactly as the pipeline asks them (`data/judge8/`), frozen
  before the one test run; the reference (Claude Sonnet 5.5) is the label; no cheap route met the 97% bar; a 45-item sample was
  labelled by an assistant to check the reference itself (`data/results/judge8_test*.json`).
- **Offline re-reads (Increments 9 and 10).** Rule changes were measured without model calls on the verdicts stored in earlier
  audits (`data/results/reread9.json`, `sticky10.json`). A test re-runs Increment 9's re-read from the stored files; Increment 10's
test checks the recorded result, and its script matches items by id rather than through the audit's text lookup.
- **Papers made again (Increments 7 and 9).** Each change was shown on one or two papers made once; no run-to-run variance was
  measured, and the reviews say a single run cannot separate a change from variance.
- **User validation (§6).** Still not done: no independent person has used the app, and no person labelled a set after Increment 6.
