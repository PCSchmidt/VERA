# Audit v3: what the one test run of each set showed (2026-10-04)

The audit's source was frozen at 2026-10-04T18:56:03Z (sha256 `2195e928d9ad…`, `scripts/freeze_audit_v3.py`) after development on the dev
splits; both test sets were run on exactly that source. Rates are reported, not gated.

## Seeded faults, test split (`data/seeded_v3/results_test.json`)

52 planted faults and 6 unmodified controls, from 6 source documents none of which was used in development (protocol-live-1 and -2,
topic-a-loop-2 and -3, and the literature sections of conformal-shift and research-agents-eval). Cost $0.13.

| | Red (a `fail` finding; for method-code faults, a method-code warning) | 95% interval |
|---|---|---|
| All 52 planted faults | 50 of 52 (96%) | 87-99% |
| the 28 plain (deterministic) faults | 28 of 28 | 88-100% |
| the 24 subtle faults | 22 of 24 (92%) | 74-98% |
| papers (40) / literature sections (12) | 39 of 40 / 11 of 12 | |

New v3 fault types, all caught: `method_code_missing_step` 4/4, `method_code_undescribed` 4/4, `figure_altered` 2/2,
`reproduction_basis_wrong` 3/3 (small numbers: each is two to four items). The known misses were reported again and not tuned for:
`reversed_comparison` 3 of 4 (the miss is in topic-a-loop-3, flagged amber), `overstated_claim` 1 of 2 (a literature section
passed green), `misattributed_number` 4 of 4 this time (it was a miss in v2).

**Controls: 3 of 6 failed**, which is the weak side of this result.
- Two of them (protocol-live-1 and -2) fail on the reproduction-basis check, and the audit is right: the papers say the baseline was
  reproduced on in-sample rows for the Analytical dataset, the registered target compares held-out rows there. The cause is a
  write-up defect, not an audit error: the facts line given to the writer states the in-sample convention for every dataset
  alike. This is fixed for the Increment 4 runs (the facts state the registered basis per dataset); the controls are counted as false
  fails because that is how the set defines them, and the review says the audit caught a real misstatement.
- One (topic-a-loop-2, an old paper) fails the misplaced-number check: a number written in a sentence about one method and dataset
  that is a value of another. Plausibly a real confusion in that paper; not examined cell by cell.
- Beyond the three, 4 of 6 controls carry a method-code warning (the alignment judge reading code against prose raised a warn on
  an unmodified paper): the check is a lead for a person, which is why it is a warn and not a fail.

Development, for comparison (51 faults, the frozen audit not yet): 48 of 51 red, 2 false fails on 6 controls.

## Novelty gold set, test split (`data/novelty_gold/results_test.json`)

24 test pairs by construction (12 relabelled published methods, 12 unrelated pairs), cost under a cent. The audit's novelty
question said "not distinct" on the relabelled pair 11 of 12 times (92%, 65-99%) and "distinct" on the unrelated pair 12 of 12
(100%, 76-100%); none unsure. These pairs are easy (a paraphrase of the same paper against an unrelated topic), so this shows the
question can tell a relabelled method from an unrelated one, not that it separates a real new variation from a close prior method.
Against the ten real loop ideas, the judge agrees with the model-produced labels (adopted by Chris after checking each, all
`distinct`: see `labels_provenance.md`) on 7 of 10 (40-89%); the three it differs on are not shown to be wrong by that, since the
labels are all one value and not an independent human's.

## Disclosed

- **The freeze was broken after these runs:** `vera/loop/tables.py`, a file the freeze covers, was changed at 2026-10-04T21:21Z (a default-argument fix found on the credal run). The numbers above describe the frozen audit (hash `2195e928d9ad`); `check_seeded_v3.py` and `check_novelty_gold.py` block at HEAD for that reason. See `docs/reviews/incr-4.md`.
- The novelty test run was started twice. The first run (ledger `run_noveltygold-test-1`) judged all pairs and then crashed in the
  script reading the label sheet (a column name), before writing or printing any result; the script was fixed (not an audit file) and
  the run repeated. No test result had been seen before the second run.
- The dev set was developed on until the freeze; the three audit changes made while developing (the audit reads protocol tables,
  counts the baseline's in-sample values as known, and the basis check) are all before the freeze.
