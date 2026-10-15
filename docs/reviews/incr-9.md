# Increment 9 review: an unsure judge is not a verdict

Written 2026-10-15 by Claude Code. This review is the evidence for `incr9_review`. Plain about what was not shown.

## Outcome

Increment 8's audit asked the reference judge (Claude Sonnet 5.5) to confirm a cheap "no" on claims and statements, but the
rule was asymmetric (an unsure reference no let a failure stand, an unsure yes did not overrule) and the reference was never
asked while a paper was written. This increment made the rule symmetric and moved the reference's confirmation into the
write step.

What the evidence says:

- **A red light now rests on a confident no.** Re-read offline under the new rule, Increment 8's five re-audits move 20
  failures to "unsettled" (the 14 resting on a reference no below 0.7 and the 6 on a reference yes below 0.7); no verdict
  changes. The rule is more lenient than Increment 8's, not stricter: a failure now needs a confident no.
- **The two papers made again are not better by this measure.** Compared under the same rule (Increment 7's papers as
  re-audited in Increment 8, re-read under the Increment 9 rule), N1 had no failure (amber) and now has one; N2 had one (C51)
  and now has two. These are single papers, made once each with a model that writes differently every time, audited by
  judges that vary between runs: one run per paper cannot separate the change from run-to-run variance.
- **Each remaining failure rests on a confident reference no**, and they have two causes:
  - **the write step's blind spot** (N2's C22 and C45): the cheap judge said yes at write time, so the reference was not
    asked until the audit, where the cheap judge said no and the reference agreed (0.80, 0.72);
  - **the reference changing its answer** (N1's C41): at write time the cheap judge said no and the reference said no at only
    0.62, so the claim was kept as unsettled; in the audit, on the same text, the reference said no at 0.80 and it failed.
- **What the write-time confirmation did**: the reference overruled one cheap no in each paper (kept without repair); gave
  a confident no on 12 items in N1 and 9 in N2 (14 and 9 verdicts; those items went to repair or removal); and was unsure on 3
  and 2 (kept, recorded as unsettled). The reference cost $0.063 at write time and $0.011 in the audit for N1, and $0.038 and
  $0.020 for N2; the papers cost $0.643 and $0.659 in all.

Who did what: Claude Code built everything, ran the offline re-read and, at Chris's request, made both papers through the
app's API with his key (recorded under its name with an attribution). Chris approved `incr9_scoped` (decisions 1-5 as
proposed: caps, the symmetric rule, the reference in the write step, the papers by whoever he asks, the out-of-scope list)
and `papers9` in his own terminal.

## Exit criteria (docs/07, SPEC)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| The rule tested and its effect on the five re-audits recorded | Yes | `tests/test_unsure.py`; `data/results/reread9.json` |
| The write step confirming with the reference | Yes (review, paper and interpretation) | `vera/literature/confirm.py`; `tests/test_write_confirm.py` |
| The two Increment 7 papers made again and audited, with the confirmations' cost | Yes; made by Claude Code at Chris's request; the new papers do not have fewer failures | `data/papers9/` |

## Each feature's acceptance criteria (SPEC)

| Feature (gate) | Acceptance criterion | Met? | Evidence |
| --- | --- | --- | --- |
| Unsure rule (`unsure_rule_ready`) | Offline tests: confident reference no fails; below 0.7 either way is unsettled; confident yes is a disagreement; a cheap confident no with nothing against it fails; a rule failure fails; the re-read reproduces from the stored files and changes severities only | Yes | `tests/test_unsure.py` (6 functions, 12 cases); `check_carry9.py --part unsure` |
| Write-time confirmation (`write_confirm_ready`) | A cheap no the reference overrules is kept without repair; one it confirms is repaired and re-checked; unsure keeps it as unsettled; no reference means Increment 8's behaviour; review and paper both use it; no self-grading; both judges' verdicts stored | Yes; but the audit re-asks the reference after the write step's answer, and can turn an unsettled item into a failure (see "Deviations") | `tests/test_write_confirm.py` (6); `check_carry9.py --part write` |
| Papers (`papers9`) | Two papers within caps, each audited under the new rule; the record names who made them; write-time confirmations counted from the stored verdicts | Yes | `check_papers9.py` |
| Review (`incr9_review`) | Overhead entry for each day a gate passed; traceability; Evaluator passes | Traceability passes (36 requirements); **overhead for 2026-10-15 not yet logged**; Evaluator below | `check_dogfood.py` |

## What was built

- **`vera/audit/disagreement.py`**: `outcome(audit verdict, reference verdict, write-time verdict)`, the one function that
  settles a judge failure: a confident reference no fails, a confident reference yes is a disagreement, a reference answer
  below 0.7 either way is unsettled; with no reference asked, a confident write-time yes against the audit's confident no
  is a disagreement, and anything else the cheap judge's failure. `reconcile` uses it; disagreements and unsettled items are
  warnings that say which they are, and the audit's note counts both.
- **`scripts/reread9.py`**: the same function applied to the verdicts stored in Increment 8's re-audits, no model call
  (`data/results/reread9.json`).
- **`vera/literature/confirm.py`** and its use in `synthesis_stage.verify_sentences` (claims and synthesis sentences, for the
  review and the paper) and `paper_interpret` (statements): a cheap confident no on `claim.within_quote` or
  `paper.inference_follows` goes to the reference; its answer decides keep, repair or unsettled, and is stored with the
  item. The app gives the write step its reference (`pipeline.real_deps`).
- **Reader and PDF**: unsettled items listed apart from failures and disagreements; the amber wording names both.
- **Records and checks**: `scripts/record_papers9.py`, `set_aside_paper.py --as`; `tools/checks/check_carry9.py`
  (unsure, write), `check_papers9.py`. 818 tests pass and 13 skip without Docker (`docs/results/incr9_test_run.txt`; 799 at
  Increment 8).

## The offline re-read of Increment 8's re-audits

| Paper | Failures before / after | Unsettled after | Light after |
| --- | --- | --- | --- |
| P1 (Increment 6) | 30 / 20 | 10 | red |
| P2 (Increment 6) | 29 / 24 | 5 | red |
| P3 (Increment 6) | 20 / 17 | 3 | red |
| N1 (Increment 7) | 0 / 0 | 0 | amber (1 disagreement) |
| N2 (Increment 7) | 3 / 1 | 2 | red (C51 only) |

Severities only: `scripts/reread9.py` asserts every finding's verdicts are unchanged, and a test re-runs it against the
stored files.

## The two papers made again (`papers9`)

Both from the same reviews and requests as in Increment 7 (N1: 3,000 words, no emphasis; N2: 3,000 words, emphasis naming
"Context Language Models"), cap $1.00 each, made through the app's API on 2026-10-15, with Increment 7's papers set aside as
`runs/<run>/paper_incr7/` (kept). The full texts came from the PDF and parse caches (GROBID was not running; every paper read
in full in Increment 7 was cached).

| | N1, Increment 7 paper: its own audit / re-audited (Incr 8) / re-read (Incr 9 rule) | N1, Increment 9 paper | N2, Increment 7 paper: its own audit / re-audited / re-read | N2, Increment 9 paper |
| --- | --- | --- | --- | --- |
| Failures | 2 / 0 / **0** | **1** (C41) | 3 / 3 / **1** (C51) | **2** (C22, C45) |
| Disagreements, unsettled | - / 1, - / 1, 0 | 1, 1 | - / 0, - / 0, 2 | 0, 3 |
| Light | red / amber / amber | red | red / red / red | red |
| Claims kept | 51 | 57 | 51 | 47 |
| Sentences removed at write time | 13 of 78 | 11 of 84 | 12 of 77 | 15 of 73 |
| Write-time reference: items with a confident no / overruled / unsure | (not asked) | 12 (14 verdicts) / 1 / 3 | (not asked) | 9 / 1 / 2 |
| Reference cost: write time / audit | - | $0.063 / $0.011 | - | $0.038 / $0.020 |
| Paper cost | $0.676 | $0.643 | $0.613 | $0.659 |

Read across the bold figures: under the same rule, N1 went from no failure to one and N2 from one to two. One paper per
review, made once, cannot separate the write step's change from the variance of writing and judging; it does not show the
change made the papers better or worse. No independent scorer read the new papers (as Increment 7's did), so whether the
claims themselves improved is not known.

**The three remaining failures**, from the stored verdicts:

- **N2's C22 (S28) and C45 (S68): the write step's blind spot.** The cheap judge said yes at write time, so the write step
  did not ask the reference; in the audit the cheap judge said no and the reference agreed (0.80, 0.72). Asking the reference
  about every claim at write time would have caught them, at roughly 50 more reference calls a paper (about $0.15 to $0.20).
- **N1's C41 (S61): the reference changing its answer.** At write time the cheap judge said no (GLM, 0.90) and the reference
  said no at 0.62, below the threshold, so the claim was kept as "unsettled at write time". In the audit the reference was
  asked again on the same text and said no at 0.80, so it failed. Asking about every claim would not have changed this; the
  audit re-asking after an unsure write-time answer did.

An unsure answer can also flip direction between calls: N1's S60 got a reference no at 0.62 at write time and a yes at
0.62 in the audit (it is an unsettled warning either way). Both support Next SPEC item 1.

## Spend, overhead, independence

| Cap (SPEC) | Spent | Source |
| --- | --- | --- |
| $0.50 debugging and smoke runs | $0 (all development offline; the re-read made no model call) | ledgers |
| $2 two papers (cap $1.00 each) | $1.302 (N1 $0.643, N2 $0.659; the reference $0.132 of it: write time $0.101, audit $0.031) | the runs' ledgers; the stored verdicts |
| $0.25 audits beyond the papers' caps | $0 (each audit ran inside its paper's cap, by the ledger) | the runs' ledgers |
| $3 increment | $1.302 | ledgers since `incr8_review` |

Each audit report's own `total_cost_usd` ($0.0012 for N1, $0.0010 for N2) leaves out the reference's confirmation calls,
which are on the ledger as `p2.confirm` and on the findings' verdicts ($0.011, $0.020): the report undercounts what the audit
cost. Overhead: not yet logged for 2026-10-15, the day all four Increment 9 gates passed; `check_dogfood.py` blocks this gate
until it is. Same-model overlap: the reference, the builder and the agent that made the papers are Claude models; the cheap
judges are Jev and GLM.

## Deviations from the SPEC

- **The audit re-asks the reference** about a cheap no even when the write step already asked it on the same text (the SPEC
  said it would ask again only if the text changed). The audit's answer decides, so a confident yes or an unsure answer at
  write time can become a failure in the audit: that is what happened to N1's C41 (unsure no at 0.62, then no at 0.80). Not
  implemented because the audit does not know which stored sentence a judge's material belongs to.
- **The audit report's `total_cost_usd` leaves out the confirmation calls** (above).
- **The papers were made by Claude Code** through the app's API, at Chris's request (decision 4), not in the browser.
- **`set_aside_paper.py` gained `--as`**: N1's run already held Increment 6's paper as `paper_incr6`.
- **The $0.25 audit cap was not used**: each audit ran within its paper's own cap.
- **No independent scorer read the new papers**; the comparison is by audit counts on one paper per review.
- **The first draft of this review** compared the new papers with Increment 7's own audits (2 and 3 failures) instead of the
  re-audit the SPEC names, and so called them better; the Evaluator caught it (below). The N1 notes in
  `data/papers9/record.json` carried the same misreading of C41 and were corrected after `papers9` passed.

## Next SPEC (candidates, in my order)

1. **Make the reference's answer stick between write and audit**: when the write step has asked the reference on a text, the
   audit uses that answer unless the text changed (the SPEC's own intent, not built); and decide whether an unsure answer is
   re-asked (once, or by a second strong judge) rather than left to the audit's draw. This addresses N1's C41.
2. **Close the write step's blind spot**: ask the reference about every claim at write time (about $0.15 to $0.20 a paper),
   so the cheap judge's yes is not the last word. This addresses N2's C22 and C45.
3. **Measure, not anecdote**: several papers per review, or the same paper audited repeatedly, to separate a change from
   run-to-run variance; and an independent reading of the claims, as Increment 7 did.
4. Carried: a better yardstick for claims and statements (a person's labels, or a vote of strong judges); Increment 10 (the
   auditor on external papers).

## Independent Evaluator

Verdicts in `.meridian/evaluator/incr9_review-verdict*.json`.

**Round 1** (fail, 5.5; completeness 7, quality 5, consistency 5, spec adherence 5): every figure it checked matched the files,
but two errors were blocking. The review said all three remaining failures were the write step's blind spot; C41 was not
(a write-time cheap no, a reference no at 0.62, then a reference no at 0.80 in the audit). And it compared the new papers
with Increment 7's own audits instead of the re-audit under the same rule, so "fewer failures" was wrong (0 to 1 and 1 to 2),
and "a stricter definition" was backwards. Minor: the write-time and audit reference costs not given apart; "confirmed 14 and
9" counted verdicts, not items; the audit report's total undercounts the confirmation calls; the deviation on re-asking did
not say it can turn an unsure answer into a failure. Verdict kept in `incr9_review-verdict-r1.json`. After it, the Outcome,
the papers table, the failures' explanation, the costs, the deviations and Next SPEC were rewritten, and the N1 notes in
`data/papers9/record.json` corrected.

**Round 2** (pass, 8.4; completeness 9, quality 8, consistency 8.5, spec adherence 8): gaps 1-6 checked against the files and
closed; no new wrong figure. Its optional note (S60's flip) was added after the verdict; the docs/07 heading is updated when the
gate passes. Verdict kept in `incr9_review-verdict.json`.

`incr9_review` passed on 2026-10-15 (approved by Chris in his own terminal): 818 tests passed and 13 skipped (Docker not
running), traceability (36 requirements), dogfood (2 hours logged for 2026-10-15) and the Evaluator (pass, 8.4).
