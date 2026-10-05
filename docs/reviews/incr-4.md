# Increment 4 review: paper quality and the measured comparison

Date: 2026-10-05 · Reviewer: Chris (decisions and human gates) · Author: Claude Code
Gates passed: `incr4_scoped`, `carry_in_ready`, `topics4_chosen`, `protocol_ready`, `lit2_ready`, `writeup2_ready`, `problem2_ready`,
`audit4_ready`, `runs4`; `comparison4` recorded by Chris on 2026-10-05 (see Deviations: it was written into the gate state by hand, not by the
gate engine); `rubric_scored` awaits Chris's approval (its check passes). This review is the evidence for `incr4_review`.

## Outcome

The loop now does the experiment the confirmed question describes, writes a paper with figures from the numbers, and is audited more widely. On
both problems it ran end to end, it **did not improve the parent's baseline**, and the comparison with ScientistTwo does not favour it. In order of how
much each statement should be trusted:

1. **The protocol run answers part of the confirmed tree-explain question, and its pre-registered expectations mostly failed.** TreeHFD against
   TreeSHAP and the true components over six correlations (0 to 0.95), three seeds, five bootstrap refits; the closed-form truth reproduces the
   TreeHFD paper's Table 3 (worst relative difference 1.2e-5, at rho 0 where the table's components are zero; about 1e-14 at the other correlations). TreeHFD's component error is below TreeSHAP's at every correlation above 0 (rho 0.5: 5.99% against 34.0% of the
   signal variance) and about equal at rho 0 (8.52% against 7.94%). Of four expectations written before the run: E1 (TreeHFD below TreeSHAP at every
   rho) **failed** (rho 0); E2 for TreeHFD (error rises with rho) **failed** (the percentage error falls from 8.52% to 2.99%, a scaling effect: the unscaled
   error is flat near 0.21 to 0.24); E3 (TreeHFD rank stability at least 0.8 everywhere) **failed by 0.0004** (0.7996 at rho 0.95); E4 (TreeSHAP's
   components are not functions of their own variables) held. It cannot show anything about random forests, public datasets beyond Airfoil (which has no true
   components) or a second ensemble library.
2. **A second parent problem was taken from a registered target to a reproduced baseline and a loop run**, and the thin-harness route was measured
   on it (T10, below). The by-hand route reproduced the paper's Table 3 (LV within 0.2% on all four metrics, best of five methods); the model-written
   adapter route did not in four attempts.
3. **Neither loop run beat its baseline.** tree-explain: the one idea run (C2) was worse on every dataset (held-out residual 2.79 to 4.72 on Analytical,
   4.73 to 6.38 on Airfoil). credal: both ideas were far worse than LV (MAE 24.6 and 47.4 against 10.7), with spreads near zero that point at a fault the
   run did not diagnose (the paper says so). The ablation stage ran on no run: nothing won; it is demonstrated only with a scripted winner.
4. **Comparison with ScientistTwo:** the gain half of MOE-3 is not met on TreeHFD; on credal the two did not attempt the same problem; ScientistTwo's
   cost is not published, so MOE-3 is not reportable as met on either problem (`docs/results/comparison_table.md`; protocol hashed before the numbers were read).
5. **The v3 audit caught 50 of 52 planted faults in one frozen test run** (96%, 87-99%), and failed 3 of 6 unmodified controls, two of them because the
   papers misstated the reproduction basis (a real defect, now fixed in the write-up facts).
6. **Retrieval did not get demonstrably better.** Fresh topics: 4, 9 and 9 of 10 key papers retrieved (40%, 90%, 90%; 95% intervals 17-69%, 60-98%, 60-98%); the three Increment 3 topics re-run (not independent), against their
   Increment 3 final values: tree-explain 70% to 50%, credal-dro 38% to 62%, llm-judge-numbers 20% to 20%. Pooled over the six re-runs and fresh topics: 34 of 58 (59%, 46-70%). At eight to ten papers per
   topic a change of one query moves a topic by 10 to 20 points, so no improvement from the new queries is shown.

## Exit criteria (docs/07, SPEC)

| Criterion | Status |
|---|---|
| Two complete runs, compared with ScientistTwo | Met as written: `docs/results/runs4/`, `comparison_table.md`; both runs reached their final stage (audits amber); the comparison is not favourable and partly not comparable (above) |
| An honest account of where the write-ups fall short of an academic paper | Below |
| Paper-shaped write-up, figures drawn from results, ablations | Met for shape and figures; ablations demonstrated with a scripted winner only (no real winner) |
| Second parent problem; T10 measured both ways | Met; the adapter route failed (below); T10 decided by Chris |
| Protocol experiments | Met (`protocol_ready`) |
| Audit v3 with a frozen test | Met for the two test runs, which ran on the frozen source; **the audit's source was changed afterwards** (a frozen file, `vera/loop/tables.py`, at 2026-10-04T21:21Z), so the freeze was not kept to the end and `check_seeded_v3.py` now blocks at HEAD (below) |
| Fresh-topic literature runs | Met (three topics, one tabular parent refused) |
| Judge on larger N (T1 reverse-if (1)) | **Not done** (below) |
| Rubric scored blind by a person, claim re-labels | Recorded, with a provenance caveat (below); the approval is Chris's |
| Per-session overhead (check enforced) | **Not met for 2026-10-03** (below) |

## What was built

- **Rule gates** (Increment 3 carry-in): `loop.baseline_reproduced`, `loop.beats_baseline` and `loop.best_method` are decided by the table, with the judge asked
  anyway and its answer kept beside the verdict.
- **Literature v2:** 12 queries over seven angles; a retrieval paragraph in every review; claim anchoring (a deterministic check of editorial connectives,
  `lit.quote_covers_claim` shown the quote and the source's title, the one-assertion prompt rule, and, added after a reader's note, a refusal of claim
  sentences that lean on an earlier one for their subject).
- **Protocol experiments:** `docker/sandbox-treehfd/truth.py` (closed-form HFD, within 1.2e-5 of Table 3), `protocol.py` (TreeSHAP, error against truth, bootstrap
  rank stability), registered and hashed before any run; a `protocol` stage in the loop graph; tables, figures and an audit of every cell.
- **Problem kits** (`vera/loop/problem.py`, `credal.py`): the stages read the active problem's harness, metrics, prompts and baseline gate; the credal harness
  (`docker/sandbox-credal/`, an image of the parent's repository with deviations documented), a thin generic harness, and `run_loop.py --problem credal`.
- **Write-up:** figures drawn from `results.json` with the plotted data written beside the image; reproduction-basis and trend statements; a prose-only word
  limit; an ablation stage; `--retry-from`.
- **Audit v3:** figure data against cells, method-code alignment (AUD-F-05), novelty (AUD-F-07), the reproduction basis, protocol tables.
- Tests: pytest reports 606 passed at the last full run (parametrised cases included); the gates run ruff and the whole suite.

## Fresh topics, retrieval, anchoring

Tables: `docs/results/retrieval_recall_lit2.md`, `retrieval_recall_lit2_old.md`, `lit2_summary.md`. Key papers retrieved before the screen: research-agents-eval 4 of 10,
conformal-shift 9 of 10, tabular-trees-vs-nets 9 of 10; the screen kept 2, 6 and 8. The tabular topic's first two scoped questions were rejected by the judge (not
confident); Chris narrowed the topic's good-question and the third passed on the first try. The tabular **parent was refused** after a bug in my GitHub check
(it did not follow 301 redirects) was fixed: the judge then declined both resolvable repositories on its own reading. A reader's notes on the three fresh reviews
found sentences leaning on an earlier one ("It also reports that this advantage grows"); 12 of 75 earlier claim sentences had the fault; a check and a prompt rule
now refuse it and the three sections were written again from the same evidence (both versions kept). The anchoring check fails 21 of 42 Increment 3 claims
(50%, 36-64%) and 18 of 30 labelled real claims (60%, 42-75%); with the rule the sections end 17, 16 and 11 claims, and all final audits are green. The conformal
review was dense and jargon-heavy; not fixed.

## Protocol run: the answer and its limits

`docs/results/tree_explain_protocol_results.md` and the registration (2026-10-04T13:13:35Z, before any run). Beyond the numbers in Outcome 1: TreeSHAP has
residual error about 0 against the ensemble (it is exact) and is not a function of its own variables at any correlation; TreeHFD is. Rank agreement with the
true importances is between 0.4 and 0.9 for both. The TreeSHAP key bug (it assumed six variables) made its Airfoil cell invalid; fixed and re-run, disclosed in
the report. The protocol ran once in the live loop run and its cells were kept across three write-ups of the same run.

## Judge on larger N (T1 reverse-if (1))

**Not done.** This increment built no new labelled set for the claim-support judge. The only new human-comparable evidence is Chris's twelve re-labels against the
AI helper's labels (10 of 12 agree, 55-95%), which measures the helper's labels, not the judge, and the novelty question's gold set (below). The question stays open and
moves to Increment 5.

## Audit v3: the tests ran on the frozen source; the freeze was broken afterwards

Seeded set v3: 115 items; test 52 planted faults and 6 controls from six source documents not used in development (two protocol runs, two older loop papers, two literature
sections); the audit source was frozen at 2026-10-04T18:56:03Z (hash `2195e928d9ad`) and both test runs (seeded 15:15 and novelty gold, local time) were made on exactly that source, and the recorded results carry that hash. **Afterwards I changed a file
the freeze covers**: `vera/loop/tables.py` is in the audit's frozen file list, and commit `dcfea9a` (2026-10-04T21:21Z, 2.4 hours after the freeze) made `tables.beats` and `tables.best` read the
active problem's primary metric at call time (a bug the credal run hit at its results gate). The change is a default-argument fix that alters nothing for the TreeHFD problem, but the audit source
hash is now `69890a43f1fc…`, not the frozen `2195e928d9ad…`, so `check_seeded_v3.py` and `check_novelty_gold.py` **block at HEAD** with "the audit's source changed after it was frozen"; the
`audit4_ready` gate was passed before the change. The recorded 50 of 52 and 23 of 24 describe the frozen audit; the credal run, the comparison and everything after used the amended one. By the rule
the project set ("any later change spends the test set") the test set is spent for any later audit; I did not re-run it, and the checks are left blocking, not edited. Result and the controls analysis: `docs/results/audit_v3_results.md`. Every v3 fault type was caught on test
(small numbers each); known misses: `reversed_comparison` 3 of 4, `overstated_claim` 1 of 2. **Controls: 3 of 6 failed**: two on the reproduction-basis check (the papers said
in-sample for Analytical where the registered basis is held-out: a real misstatement, caused by a facts line given to the writer), one on the misplaced-number check
(an old paper). Four of six controls also carry a method-code warning, and the tree-explain run's own audit shows the same class: the check judges every sentence of a
Method paragraph that names the idea, including sentences about the protocol, so it raises warnings that are not about the idea. It is a warn by design and was frozen
before the runs. The novelty gold set (24 test pairs by construction) was 23 of 24 correct, which is easy by construction; the ten real loop ideas were labelled by a language
model and adopted by Chris after checking each (all `distinct`; not independent): the judge agrees on 7 of 10. The novelty test was run twice: the first run crashed in the script
that reads the label sheet after judging and before writing any result; no result had been seen before the second.

## Two end-to-end runs

`docs/results/runs4.json`; ledgers `data/ledger/run_runs4-*.jsonl`; papers, results, audits and gates beside each. tree-explain: $0.10, 24 minutes, amber (no fails; the warnings are
the method-code class and judge-unconfirmed comparisons). credal: $0.06, about an hour (the parent's baseline batch), amber. The credal run stopped once with a crash at the
results gate (my bug: the table helpers read the first problem's primary metric); fixed and resumed from its checkpoint, baseline and ideas run once.

## Where the write-ups fall short of an academic paper

- **No statistical tests**; three seeds (tree-explain) and the paper's 100 replications (credal); a single idea per run reached the protocol; no confidence statements beyond the seed spread.
- **Narrow datasets and one model family** (xgboost, 100 trees); the confirmed question also asks about random forests and public-data stability; the paper says it does not address them.
- **The credal paper's experiments do not address its stated research question** (credal against Wasserstein sets under contamination): the only experiment is two failed ideas.
- **Ideas are weak and unscreened by theory**: model-written, and both runs' ideas lost to the baseline; the near-zero spreads on the credal ideas were not diagnosed.
- **Missing baselines**: no other robust-regression methods beyond the parent's own on credal; no other explainers than TreeSHAP on tree-explain.
- **Related work is the verified literature section restated**, which inherits retrieval's recall (40-90% on fresh topics) and the dense, second-hand style the rubric notes.
- **Method-section statements are not all checked**: numbers there are `warn`; the method-code alignment is a lead, not a finding of fact.

## Rubric scores (both scorers)

Eight outputs: L1 to L3 fresh reviews, L4 to L6 re-run reviews, P1 and P2 the papers (`rubric_sheet_4.md`). Order: answers, coverage, correctness, reproducibility, honesty.

| | Chris (recorded 2026-10-05 11:12Z) | Independent scorer (12:18Z, a fresh subagent that did not write the review) |
|---|---|---|
| L1 research-agents-eval | 4 2 4 4 5 | 2 2 4 4 3 |
| L2 conformal-shift | 4 4 4 4 5 | 3 3 4 3 4 |
| L3 tabular-trees-vs-nets | 4 4 4 4 5 | 3 4 4 4 4 |
| L4 tree-explain | 4 2 4 4 5 | 2 2 4 4 4 |
| L5 credal-dro | 3 2 4 4 5 | 2 2 4 4 4 |
| L6 llm-judge-numbers | 3 1 3 4 5 | 3 2 3 4 4 |
| P1 tree-explain paper | 4 3 2 5 5 | 3 3 4 4 4 |
| P2 credal paper | 3 2 2 5 5 | 2 2 4 3 5 |

19 of 40 cells are equal and 34 are within one point. Means (Chris / independent): answers 3.6 / 2.5, coverage 2.5 / 2.5, correctness 3.4 / 3.9, reproducibility 4.3 / 3.8, honesty 5.0 / 4.0.
Coverage is the lowest criterion for both (2.5), and both score five of the eight outputs 2 or lower on it, the criterion T5's added reverse-if (5) reads. They disagree on the papers' correctness (Chris 2; the independent scorer 4, after checking every table cell against `results.json`).
**T5 reverse-if (5) fired by these scores:** Chris scored coverage below 3 on four reviews (L1 2, L4 2, L5 2, L6 1) and the independent scorer on four (L1, L4, L5, L6 at 2); the remedy it names (query generation from the confirmed question, a second keyed source) was partly built (twelve queries over seven angles) and did not lift recall (59% pooled), so a second keyed source remains to be tried.
**Provenance caveat (the review states what it can verify):** all eight entries and the twelve re-labels carry the same minute (11:12Z), and the notes are phrased in a
model's voice citing the recall tables; the message that reported them says the work was assisted by Codex. They are recorded as Chris's blind scores because he reported them as
his; the independent file did not exist when they were written (the script refuses `--blind` otherwise). If Chris's own reading was not behind each cell, the
`rubric_scored` approval should say so.

## T10 decided

Evidence (`docs/04-trade-studies.md`): by hand about 2.9 hours from the registered target to the baseline of record (seven failed or partial runs, each exposing one way the parent's
repository does not run as published), the adapter route not accepted in four attempts ($0.16, about 1.5 hours; two attempts ran the whole parent batch and failed reading its output,
one failed in a second on a settings name it assumed, one in a second editing a read-only installed file), the generic harness 49% of the by-hand one's lines. **Decision (Chris, 2026-10-05):** keep (a) as the default, (c) as an experimental
fallback to keep measuring, (b) rejected; no reverse-if fired.

## Judge and review checks; spend; overhead; same-model overlap

- **Spend.** By the ledger files written since the increment opened, **$3.18** against the $9 cap (the $2 debugging, $6 runs, $1 reference-judge and fresh-topic caps are not tracked
  separately by the ledgers: the two end-to-end runs $0.16; literature-stage runs $2.06 (fresh topics $0.56, their rewrites $0.42, the old topics re-run $0.44, their rewrites $0.63); the three protocol live runs $0.34; the seeded dev and test runs $0.30; the novelty gold set, its generation (two attempts) and runs $0.15; the anchoring measurements $0.005; the adapter trial $0.16; these sum to $3.18). Reference judge spend: none this increment.
  Both end-to-end ledgers equal their recorded spend (`gate-ledger.sh`).
- **Overhead.** Chris gave 5 hours for 2026-10-03, which I recorded on 2026-10-04 (11:27Z); a day is credited by the day an entry is recorded, so **2026-10-03 has no entry** and
  `check_dogfood.py` blocks on that day only (2026-10-04 is covered by the entry recorded that day; 2026-10-05 will need one if a gate passes through the engine that day). This is the Increment 3 lapse again (the entry was not logged at the end of the 10-03 session); the
  check is doing its job. How to treat it is Chris's.
- **Same-model overlap.** Writers are Sonnet 5.5 (literature stages, write-up in the `glm-sonnet` arm, the adapter) and GLM (ideas, experiment code); the cheap judge path is GLM, so in
  the `glm` arm the judge and the code writer are the same model (the audit's judge is never the producer of the text it judges: verdict ids differ). The independent scorer is the
  same family as the writer; the AI helper that labelled 30 real claims is the same family as the reference judge; the novelty labels were produced by a language model.

## Deviations

- `comparison4` was written into `.meridian/gate-state.json` by hand (by Chris, with a language-model assistant) because the gate engine could not run in that shell; the check
  passes (`check_comparison.py`) but the engine's verification and telemetry did not run; the file was rewritten with a byte-order mark and CRLF, which I normalised.
- The credal image departs from the parent's environment (numpy and cvxpy pinned, MOSEK replaced by Clarabel with its MOSEK-only options dropped, the solver cache cleared
  before parallel workers, a template copied, per-configuration files read by the harness): documented in `docs/results/problem2_baseline.md`.
- The retrieval recall v2 file of Increment 3 was overwritten once by mistake and restored; the fresh table is `retrieval_recall_lit2.md`.
- The old topics' re-runs reuse Chris's earlier scope confirmations; the TreeHFD protocol run ran three times (write-up re-runs on the same cells); the tabular topic's scope was re-asked
  after editing its good-question before any retrieval, with the manifest rebuilt.
- The writer's word limit now counts prose only (tables and references excluded).
- The novelty test run was started twice (above).
- `vera/loop/tables.py`, a file the audit freeze covers, was changed after the freeze (above): the freeze was broken after both test runs.

## Carry-overs from the Increment 3 review

Closed: rule-based gates; make the loop answer the confirmed question (protocol); retrieval disclosure in the review text (not retrieval quality); anchoring (with the repair listing what it drops);
audit dataset names; reproduction basis and trend statements; T10 measured; a "no parent" outcome (tabular, credal-dro earlier). Restated: `reversed_comparison` remains the weakest known class
(3 of 4 on test); retrieval recall (59% pooled); the `lit.*` routing on a larger labelled set; Chris's own labels of the novelty ideas; per-session overhead.

## Next SPEC (Increment 5: the app, bring-your-own-key, T9 reverse-if (2) reasoning control)

Carry in: the judge on a larger labelled set with the interval stated (T1 reverse-if (1)); a decision on whether the method-code check should judge only sentences about the idea; credal ideas
that run (a harness check that an idea's spread is not degenerate); a ScientistTwo-comparable run on the credal newsvendor benchmark if the comparison is to be repeated; retrieval
beyond keyword queries (the pooled recall is the number to move); per-session overhead entries.

## Independent Evaluator

Rounds are added below, each by a fresh subagent that did not write this review, with every verdict kept unedited in `.meridian/evaluator/incr4_review-verdict-r<N>.json`.

**Round 1** (fail, 6.2; completeness 8, quality 6, consistency 7, spec adherence 5): the main blocker was the claim that the audit freeze was kept, when `vera/loop/tables.py`, a frozen file, had been changed after the test runs; also the retrieval comparison without the Increment 3 values and intervals, and a spend breakdown that did not sum. All were fixed in the text (Audit v3 section, Outcome 6, spend). Verdict: `incr4_review-verdict-r1.json` (the file keeps the notes; the evaluator's list of checked figures is in the session record).

**Round 2** (pass, 8.3; completeness 8.5, quality 8, consistency 8.5, spec adherence 8.5): no falsified headline number, the freeze event described accurately. Verdict: `incr4_review-verdict-r2.json` and the standing `incr4_review-verdict.json`. After it these points were fixed in the text (the round-2 evaluator saw the version before): the closed-form check's precision (1.2e-5 at rho 0, not 1e-14), the adapter attempts' failure reasons (one on a settings name, one on a read-only file), the fresh-topic spend ($0.56), the overhead days the check blocks on, whether T5's reverse-if (5) fired (it did, by both scorers), the key-paper counts (eight to ten per topic), and the `tables.py` change in `audit_v3_results.md` and the comparison table's idea counts. **Process slip disclosed by the round-2 evaluator:** a search for a hash string returned part of the round-1 verdict file; it says it did not use it and recomputed every figure independently.
