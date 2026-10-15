# Increment 10 review: close-out

Written 2026-10-15 by Claude Code. This review is the evidence for `incr10_review`, the last planned gate. Plain about what was
not shown.

## Outcome

Chris decided on 2026-10-15 to close the work out (see "Why the work stopped here" in the
[retrospective](retrospective.md)). This increment did three things and nothing else: it completed the one behaviour
Increment 9's SPEC promised and did not build, it stated once what VERA's light means, and it wrote down how the work closed.
During the increment Chris also asked for every markdown document to be updated and aligned, and for the README to follow
the style and flow of his recent portfolio projects; that was done as part of the close-out documents.

- **The reference's write-time answer now sticks in the audit.** When the write step asked the reference judge about a
  sentence or statement and the text is unchanged, the audit reuses that answer instead of asking again. Re-read offline on
  Increment 9's two papers, with no model call: N1 turns from red to amber (C41, an unsure write-time "no" at 0.62 that the
  audit's second draw had made a failure, becomes unsettled); N2 is unchanged (its two failures were never put to the
  reference at write time; that is the blind spot this fix does not address).
- **The light, once.** The README's "What the audit light means" defines green, amber and red, item by item, from the code's
  rules, and what no colour means; the reader's and the PDF's wording were aligned with it. The increment reviews are dated
  records and keep the wording of their time.
- **The record closed.** A retrospective of Increments 0 to 10; the increments plan marked closed with a not-planned list, each
  item with the reason it was left and what would justify reopening it; the other documents brought up to the close.

No model spend: every result in this increment came from files already on disk.

## Exit criteria (docs/07, SPEC)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| The sticky answer tested and shown offline on the Increment 9 papers | Yes | `tests/test_sticky.py` (5); `data/results/sticky10.json` |
| The canonical light in the README | Yes | README, "What the audit light means" |
| The retrospective | Yes | [retrospective.md](retrospective.md) |
| The plan marked closed with the not-planned list | Yes | [docs/07-increments.md](../07-increments.md), "Not planned" |

## Each feature's acceptance criteria (SPEC)

| Feature (gate) | Acceptance criterion | Met? | Evidence |
| --- | --- | --- | --- |
| Sticky answer (`sticky_answer_ready`) | A stored confident yes is reused and the reference not called; a stored unsure answer is reused and the item unsettled; changed text is confirmed afresh; no stored answer means Increment 9's behaviour; the offline re-read recorded; RSH-F-17 tests grow; freezes hold | Yes, with limits: the tests exercise the paper's audit only (the review's audit uses the same lookup on `sentences.jsonl`, untested); "no stored answer" rests on the Increment 9 suite; "changed text" is tested at the lookup, not through a full audit | `tests/test_sticky.py`; `check_carry10.py --part sticky` (11 RSH-F-17 tests) |
| Close-out documents (`closeout_docs_ready`) | The README's light section names each colour and item; the retrospective has its sections and its figures trace to the review files; docs/07 marks the work closed with the not-planned list | Yes; the check confirms the sections exist, not that figures trace: the tracing was done by hand and the Evaluator found the total spend untraced (fixed, see "Independent Evaluator") | `check_carry10.py --part docs` |
| Review (`incr10_review`) | Overhead for each day a gate passed; traceability; Evaluator passes | Traceability passes (36 requirements); **an overhead entry for 2026-10-15 recorded after `incr9_review` passed (18:01Z) is still needed**: the day's earlier entry belongs to Increment 9's window; Evaluator below | `check_dogfood.py` |

## What was built

- **`vera/audit/sticky.py`** (new): indexes the reference verdicts stored on a document's sentences and statements by question
  and item text, and reads the item text back from the judge's material (`Claim: …` for `claim.within_quote`, `Statement: …`
  for `paper.inference_follows`). `vera/app/pipeline.py`'s audit asker looks there before calling the reference; both audits
  (review and paper) do. `vera/audit/sentences.py` and `sentence_checks.py` were not edited (hashed for Increment 7).
- **`scripts/reread10.py`**: the offline re-read of the Increment 9 papers (`data/results/sticky10.json`).
- **`tools/checks/check_carry10.py`** (parts sticky, docs). 823 tests pass and 13 skip without Docker
  (`docs/results/incr10_test_run.txt`; 818 at Increment 9).

## The documents, aligned

| Document | Change |
| --- | --- |
| `README.md` | Rewritten to the structure of the recent portfolio READMEs (status with the headline, plain-language overview with who it is for and why, at a glance, architecture, quickstart, approach, motivation, method, the light, results, limitations, known gaps against the original roadmap, operational notes, glossary, license, author), brought to the close |
| `docs/reviews/retrospective.md` | New: the whole project in two pages |
| `docs/07-increments.md` | Marked closed; Increment 10's result; the not-planned list |
| `docs/01-conops.md` | v0.4: S4b (the review paper); where each MOE stands at the close |
| `docs/04-trade-studies.md` | T11 (judging the sentence checks, Increment 8); fourteen garbled characters in older headings repaired (an encoding error from an earlier edit) |
| `docs/05-risk-register.md` | R3, R6 (scope creep, occurred and closed out), R12 brought up to date; R15 (judges below their bar) and R16 (human steps done by an assistant) added |
| `docs/06-verification-plan.md` | §8, as built for Increments 6 to 10 |
| `docs/meridian-dogfood.md` | Findings from Increments 6 to 10, overhead at the close |
| `data/README.md` | The data folders of Increments 6 to 10 |
| `docs/02-requirements.md` | v0.11: external-paper auditing (AUD-F-01, -02, -06, -08, AUD-P-01, -02) moved to Increment 11, not planned |
| `CONTRACT.md` | Scope at the close |
| `vera/app/static/app.js`, `vera/app/pdf.py` | The reader's and the PDF's definition of green and of a judge disagreement aligned with the README |
| `CLAUDE.md` | The project's closed status; working notes learned in Increments 6 to 10 |
| `MERIDIAN.md` | Regenerated from `.meridian/gates.yaml` |

The increment reviews (0 to 9) and the result files are dated records and were left as written. Every relative link in the
changed documents was checked to resolve.

## Spend

$0 against the $0.50 cap: no model call was made in this increment. The project's total is $16.05 of model spend over 16 days
(`data/results/spend_total.json`).

## Deviations from the SPEC

- **The documents went beyond the SPEC's three items**, at Chris's request during the increment: every current markdown document
  was brought up to the close and the README rewritten to the style of the recent portfolio projects.
- **No smoke audit with the real judges was run**; the fix was shown on stored verdicts only.
- **The "changed text" case** is tested at the lookup, not through a full audit.

## Closing statement

VERA ends as a working local app and pipeline that takes a topic to a quoted, sentence-checked literature review and review
paper on the user's own key, with an audit that says what it checked and what it could not. Its measured limits are stated in
the README and the retrospective. The work is closed; anything further starts from the not-planned list with a new decision.

## Independent Evaluator

Verdicts in `.meridian/evaluator/incr10_review-verdict*.json`.

**Round 1** (warn, 6.8; completeness 8, quality 7, consistency 6, spec adherence 6.5): the sticky answer and most figures checked
out, but the README's light section contradicted the code (an overruled "no" was called green; an unsure cheap judge on a claim was
said to need a question the reference does not confirm), the reader still defined green narrowly, the $15.78 total traced to no
file (the deduplicated ledgers give $16.05), a per-type interval was attributed to all types, T1 to T10 should read T1 to T11, the
verification plan overstated a test, the sticky tests' limits were not stated, two changed documents were missing from the table,
and the reviewer's path claimed every gate complete. Verdict kept in `incr10_review-verdict-r1.json`. After it: the light section
rewritten from `disagreement.outcome`, `pipeline._asker` and `sentences.check_entry`; the reader's and the PDF's wording aligned;
`scripts/spend_total.py` and `data/results/spend_total.json` derive the total ($16.05), used in the README, the retrospective and
this review; the other points corrected in place.

**Round 2** (pass, 8.4; completeness 9, quality 8, consistency 8.5, spec adherence 8): all ten round-1 gaps fixed and checked.
After it: the test run re-captured on the final tree (`docs/results/incr10_test_run.txt`), and the retrospective says the spend
total reproduces on the owner's machine only. Verdict kept in `incr10_review-verdict.json`.

`incr10_review` passed on 2026-10-15 (approved by Chris in his own terminal): 823 tests passed and 13 skipped (Docker not
running), traceability (36 requirements), dogfood (2 hours logged for 2026-10-15 after `incr9_review`) and the Evaluator (pass,
8.4). The project is closed.
