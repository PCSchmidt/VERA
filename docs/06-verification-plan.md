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

- Tasks: atomic questions drawn from the auditor (citation exists? number
  consistent?) plus one general task (e.g. grounded-answer checks).
- Reference: frontier LLM with careful prompting plus gold labels where
  available.
- Metrics: agreement, ECE, flip rate over N=10+ repeats, cost, latency,
  escalation rate as a function of threshold.
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
