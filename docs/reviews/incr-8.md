# Increment 8 review: a judge you can trust on the new questions

Written 2026-10-14 by Claude Code. This review is the evidence for `incr8_review`. Plain about what was not shown.

## Outcome

Increment 7's three new judge questions (`claim.within_quote`, `sentence.no_fact`, and the clause-by-clause wording of
`paper.inference_follows`) had never been measured against the reference judge, and the papers made with them were red
where the cheap path's two judges (Jev and GLM) disagreed between writing and auditing. This increment measured them,
fixed one route per question, and changed what makes a light red.

What the evidence says:

- **No backend meets the bars on any of the three questions.** On the frozen test split, against the reference (Claude
  Sonnet 5.5), the best route, Jev then GLM (the decided path, unchanged), agreed on 89% of claim items, 95% of sentence
  items and 89% of statement items, against JDG-P-01's 97%, and flipped across repeats on 9.7%, 0% and 6.4% of items,
  against JDG-P-03's 2%. **JDG-P-04 is not met.**
- **The yardstick is soft on the two questions that matter most.** The reference flips on 4% of claim and 6% of
  statement items; it agrees with Increment 7's real-case labels on 69% of claims and 75% of statements (100% of
  sentences), and with the assistant's 45 new labels on 11 of 15 claims and 9 of 15 statements.
- **A "no" from the decided path is usually a real no**: the reference also says no on 11 of 13 claim items, 30 of 31
  sentence items and 7 of 9 statement items in the test split.
- **Chris chose** (decision 3, since no route met the bars) to keep Jev then GLM and have the audit confirm a "no" on
  claims and statements with the reference before it can fail; a contradiction between write time and audit, or between
  the cheap judge and the reference, is now amber ("judges disagree"), not red.
- **Re-audited this way**, Increment 6's three papers stay red: of the 70 cheap "no" verdicts the reference was asked
  about, it said no on 61 (48 at confidence 0.7 or more, 13 below) and overruled 4. Increment 7's N1 turns amber (its one
  failing claim was a cheap "no" the reference overruled); N2 stays red on three items: C51, confirmed by the reference
  and also flagged by Increment 7's independent scorer, and two where the reference itself was unsure (no at 0.62, yes at
  0.68).
- **The rule is asymmetric**: any reference no lets a failure stand, even an unsure one, while only a confident reference
  yes overrules. So 14 failures in the re-audits rest on a reference no below 0.7, and 6 on a reference yes below 0.7.

Who did what: Claude Code built everything, ran the measurement and, at Chris's request, the re-audits (recorded under its
name). Chris approved `incr8_scoped` and `reaudit8` in his own terminal, chose the route and the confirmation, and raised
the re-audit cap. **An OpenAI assistant (recorded as OpenAI Codex) labelled the 45-item sample** at Chris's request
(decision 4); there are still no human labels.

## Exit criteria (docs/07, SPEC)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Every new question measured against the reference, with the result stated | Yes; the bars are not met, and this says so | `data/results/judge8_test.json` |
| Each routed | Yes: all three to Jev then GLM (chosen by Chris), with reference confirmation in the audit on two | `vera/judge/cheap_path.py` |
| The five papers re-audited and their reds counted as failures or disagreements | Yes | `data/reaudit8/` |

## Each feature's acceptance criteria (SPEC)

| Feature (gate) | Acceptance criterion | Met? | Evidence |
| --- | --- | --- | --- |
| Judge set (`judge_set_frozen`) | Counts within the SPEC's ranges; split by paper; hash before any test result; items built by the pipeline's own functions (a test rebuilds them) | Yes, with 67 sentence items against "about 80" (the new papers have only 19 kept transitions) | `check_carry8.py --part set`; `tests/test_judge_set8.py` |
| Measurement (`judge_measured`) | One test run after the freeze; every figure per question and backend; spend within $3 | Yes; $1.99 | `check_carry8.py --part measured` |
| Routing and disagreement (`routing_ready`) | Routed questions reach only their route; unrouted keep today's path; write-time yes + audit no is a warn; write-time no + audit no is a fail; statements keep their verdicts; old documents as before; headless test of the disagreement list | Yes; the disagreement list is tested in one layout (DOM), no new screenshots | `tests/test_routes.py`, `test_disagreement.py`, `test_app_ui.py` |
| Re-audits (`reaudit8`) | Five reports with the sentence check and the route table; spend within the cap; the record names who ran it | Yes, within the raised cap ($0.36 of $0.50); run by Claude Code at Chris's request | `check_reaudit8.py` |
| Review (`incr8_review`) | Overhead entry for each day a gate passed; traceability; Evaluator passes | Traceability passes (34 requirements); **overhead for 2026-10-14 not yet logged**; Evaluator below | `check_dogfood.py` |

## What was built

- **`data/judge8/`** (`scripts/build_judge_set8.py`): 275 items, each one of the three questions asked exactly as the
  pipeline asks it (built with `sentence_checks.within_quote`, `no_fact`, `follows_strict`), on the five papers' real
  material: 120 claims, 67 claim-free sentences, 88 statements and synthesis sentences. Dev is P1 and N1 (113 items),
  test is P2, P3 and N2 (162). The test items and the measuring code were hashed (`judge8_hash.json`, 12:57Z) before the
  test run, which ran on that code; `vera/judge/cheap_path.py` was edited afterwards (for `routing_ready`) to add
  `QUESTION_ROUTES` and `CONFIRM_NO`, so it no longer matches that hash, by design.
- **`scripts/measure_judge8.py`**: the reference (2 repeats), Jev alone, GLM alone and the decided path (3 repeats each)
  through the Increment 1 harness, unchanged; per question and backend: agreement with the reference (Wilson 95%), flip
  rate, share below the 0.7 threshold, ECE against the reference, cost and latency, Jev/GLM disagreement, and the bars.
  `scripts/judge8_posthoc.py` reads the stored answers afterwards: the labelled sample, and what a "no" is worth.
- **`vera/judge/cheap_path.py`**: `QUESTION_ROUTES` (JDG-F-07): a question with an entry is answered only by its route,
  wherever it is asked (a user without a Jev key gets GLM); `CONFIRM_NO` and `confirmer`: the reference that confirms a no.
- **`vera/audit/disagreement.py`** (new; `vera/audit/sentences.py` is hashed for Increment 7 and was not edited): a failure
  becomes a "judges disagree" warning when the audit's confident no contradicts the write-time confident yes on the same
  question, or when the reference, asked to confirm the no, gives a confident yes; a confirmed no stays a failure with the
  reference's verdict attached. The app pipeline applies it to both audits and asks the reference
  (`pipeline._asker`).
- **`vera/literature/paper_interpret.py`**: each interpretation statement now stores its write-time verdicts.
- **Reader and PDF**: judge disagreements listed apart from failures; the amber wording says a warning can be one.
- **Gates and checks**: `tools/checks/check_carry8.py` (set, measured, routing), `check_reaudit8.py`; scripts
  `judge8_labels.py`, `reaudit8.py`. 799 tests pass and 13 skip (Docker was not running; they need it)
  (`docs/results/incr8_test_run.txt`; 794 at Increment 7).

## The measurement

**Dev** (P1, N1; 113 items; $0.846): no backend met the bars; the decided path agreed 88%, 96%, 90%. On dev's claims GLM
alone agreed slightly better (43 of 48 against 42): the decided path is the best route on the test split, not on every split. Question wording could
not be tuned on dev as the SPEC allowed: the wording is in `sentence_checks.py`, hashed for Increment 7's real-case
measurement, which decision 6 keeps unchanged.

**Test, once** (P2, P3, N2; 162 items; run 16:53Z, after the freeze and after the labels; $1.14). Agreement with the
reference, Wilson 95%; flip rate across repeats:

| Question (items) | Jev | GLM | Decided (Jev, then GLM below 0.7) | Decided flips | Reference flips | Jev and GLM disagree |
| --- | --- | --- | --- | --- | --- | --- |
| `claim.within_quote` (72) | 79% (68-87) | 86% (76-92) | **89% (80-94)** | 9.7% | 4.2% | 12.5% |
| `sentence.no_fact` (43) | 93% (81-98) | 93% (81-98) | **95% (85-99)** | 0% | 2.3% | 14.0% |
| `paper.inference_follows` (47) | 77% (63-86) | 87% (75-94) | **89% (77-95)** | 6.4% | 6.4% | 23.4% |

Each backend against the flip bar (2%), with its share of verdicts below the 0.7 threshold, ECE against the reference and
p50 latency (claims / sentences / statements):

| Backend | Flip rate | Below 0.7 | ECE | p50 latency (ms) |
| --- | --- | --- | --- | --- |
| Jev | 4.2% / **0%** / **0%** | 53% / 9% / 56% | 0.14 / 0.11 / 0.09 | 149 / 147 / 152 |
| GLM | 9.7% / 4.7% / 10.6% | 0% / 1% / 1% | 0.09 / 0.03 / 0.04 | 2922 / 3058 / 3995 |
| Decided | 9.7% / **0%** / 6.4% | 2% / 0% / 1% | 0.12 / 0.08 / 0.06 | 1306 / 152 / 2213 |
| Reference | 4.2% / 2.3% / 6.4% | 19% / 3% / 20% | 0.16 / 0.12 / 0.19 | 2342 / 1565 / 3581 |

Jev alone meets the flip bar on sentences and statements but fails the agreement bar on all three (79%, 93%, 77%); the
decided path meets it on sentences only. Jev is unsure (below 0.7) on about half of claim and statement verdicts, so the
decided path often escalated to GLM. Cost per verdict: Jev $0.00002, GLM $0.00002 to $0.00004, the reference $0.002 to
$0.005.

**The yardstick** (`judge8_test_posthoc.json`): on the 45 labelled items (15 per question), the reference matched the labels
on 11, 15 and 9; GLM on 14, 14 and 7; the decided path on 12, 15 and 7. The labels were blind to every backend's answer on
these items: they were recorded at 15:01Z, before the test run (16:53Z) produced any answer on the test split, and the
recorder refuses once a test run exists; the labeller stated, in its report that Chris pasted into the build session, that it did not open the result files (not
verifiable from the repo; dev results existed, on other items). Against Increment 7's real-case labels, where items
overlap, the reference agreed on 11 of 16 claims, 18 of 18 sentences and 18 of 24 statements. Neither label set is a
person's (both are OpenAI assistants').

**What a "no" is worth**: of the items the decided path answers no, the reference also says no on 11 of 13 claims, 30 of 31
sentences and 7 of 9 statements; it finds 11 of the reference's 17 claim no's, 30 of 31 and 7 of 10.

## The routes chosen, and why

No backend met both bars, so by decision 3 the options went to Chris: keep the decided path; keep it and confirm the
audit's no with the reference; or GLM alone everywhere. He chose the second. The route table therefore names Jev then GLM
for all three questions (the behaviour before this increment, now explicit and testable), and the audit asks the reference
to confirm a no on `claim.within_quote` and `paper.inference_follows`. `sentence.no_fact` is not confirmed: its no's agree
with the reference 30 of 31 times. The write step is unchanged: it does not consult the reference.

## The five papers re-audited (`reaudit8`)

Run by Claude Code at Chris's request with his keys, on temporary copies of the live runs; before is Increment 7's audit.

| Paper | Before | After | Failures before / after | Disagreements | Reference said no (0.7 or more / below) | Said yes below 0.7 (failure stands) | Said yes, so overruled |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 (Increment 6) | red | red | 33 / 30 | 2 | 14 / 7 | 3 | 2 |
| P2 (Increment 6) | red | red | 25 / 29 | 1 | 23 / 4 | 1 | 1 |
| P3 (Increment 6) | red | red | 22 / 20 | 1 | 11 / 2 | 1 | 1 |
| N1 (Increment 7) | red | **amber** | 2 / 0 | 1 | 0 / 0 | 0 | 1 |
| N2 (Increment 7) | red | red | 3 / 3 | 0 | 1 / 1 | 1 | 0 |

- On the Increment 6 papers the reference said no to 61 of the 70 cheap no's it was asked about, 48 of them at 0.7 or
  more: most of their reds are failures the reference also sees, though 13 rest on a reference no below 0.7. P2's failures rose from 25 to 29 between two audits of the same text: the cheap judges' answers vary.
- N1's failing claim C3 (Jev no at 0.72) was overruled by the reference (yes at 0.88) and is now a disagreement; its failing
  statement I8 is now a "judge unsure" warning (GLM no at 0.60).
- N2: C51 is a confirmed failure (GLM no at 0.98, reference no at 0.93), and Increment 7's independent scorer also flagged
  it. On C3 the reference said no at 0.62 and on I2 yes at 0.68, both below 0.7: by the rule as built, only a confident
  reference yes makes a disagreement, so an unsure reference leaves the failure standing. Six findings across the five
  papers have a reference yes below 0.7 and still fail (the table's "said yes below 0.7" column).
- Spend $0.3595 of the raised $0.50: 74 reference calls, most of the cost. For a paper made with Increment 7's checks, the
  confirmation is 1 to 3 calls, a cent or so.

## Spend, overhead, independence

| Cap (SPEC) | Spent | Source |
| --- | --- | --- |
| $0.50 debugging and smoke runs | $0 (all development offline) | ledgers |
| $3 judge benchmark | $1.989 (dev $0.846, test $1.144) | `data/ledger/judge8_*.jsonl` |
| $0.25 re-audits, raised to $0.50 by Chris | $0.3595 | `data/ledger/reaudit8.jsonl` |
| $5 increment | $2.349 | ledgers since `incr7_review` |

Overhead: not yet logged for 2026-10-14, when every Increment 8 gate passed; `check_dogfood.py` blocks this gate until
it is. Same-model overlap: the reference judge, the builder and the agent that ran the re-audits are Claude models; the
cheap judges are Jev and GLM; the labels are an OpenAI assistant's.

## Deviations from the SPEC

- **The labels are an assistant's, not a person's** (decision 4, Chris's choice). Its save garbled the sheet's encoding (a
  byte-order mark, Windows line ends, UTF-8 read as cp1252); Claude Code checked that no item text changed beyond that,
  kept the file as saved (`label_sheet_as_filled.md`), copied its 45 letters by item onto the sheet as built and ran the
  recorder. The name "OpenAI Codex" is taken from the assistant's Increment 7 rubric record; the labels file says so.
- **The measurement script does not read the labels**: it was frozen before they existed. Their comparison is computed
  afterwards from the stored answers (`judge8_posthoc.py`), with no model call.
- **No question wording was tuned on dev**: the wording is hashed for Increment 7 (decision 6).
- **67 sentence items, not about 80.**
- **Items are not `BenchmarkItem`s**: that type needs a known label and one of four task names; the items go through the
  unchanged harness as plain objects, with the reference's answer as the label.
- **The re-audit cap was raised** from $0.25 to $0.50 by Chris, once the confirmation step made about 76 reference calls
  necessary.
- **The re-audits were run by Claude Code**, at Chris's request (the SPEC said Chris, or whoever he asks, named in the
  record).
- **The disagreement rule lives in a new module** applied by the pipeline, not in `vera/audit/sentences.py` (hashed for
  Increment 7).
- **JDG-P-04 is not met**: no route meets JDG-P-01 and JDG-P-03 on any of the three questions.

## Next SPEC (candidates, in my order)

1. **Decide what an unsure reference means**, both ways: today an unsure reference no lets a failure stand (14 in the
   re-audits) and an unsure yes does too (6), and the reference answers below 0.7 on 19% of its claim and 20% of its statement
   verdicts; and whether the write step should consult the reference too, so the writer
   repairs what the reference rejects instead of the audit finding it later (N2's two remaining reds).
2. **A better yardstick for claims and statements**: the reference agrees with the labels on 69 to 75% of them; a person's
   labels (still none), or a vote of strong judges, before any further tuning.
3. **Carried from Increment 7**: claim-level additions the checks miss, statements about the paper itself, more agreement
   wording; the reader-facing cost of the checks.
4. Increment 9: the auditor on external papers.

## Independent Evaluator

Verdicts in `.meridian/evaluator/incr8_review-verdict*.json`.

**Round 1** (warn, 7.3; completeness 7, quality 7.5, consistency 7, spec adherence 7.5): every figure it checked matched the
files. Gaps: "the reference confirmed 61 of 70" hid 13 reference no's below 0.7, and the rule's asymmetry (any reference no
confirms; only a confident yes overrules) was not stated; the measurement table gave flip rates for the decided path only,
and no ECE or latency; the decided path called the best route without saying GLM was better on dev's claims; the labels'
blindness not stated; the routing file's change after the hash not stated; the overhead entry for 2026-10-14 missing (known).
Verdict kept in `incr8_review-verdict-r1.json`. After it, each text gap was corrected above (the split and the asymmetry,
in the Outcome, the re-audit table and Next SPEC; a per-backend table; the dev line; the labels' blindness and its basis;
the hash note).

**Round 2** (pass, 8.5; completeness, quality, consistency and spec adherence 8.5 each): the round-1 fixes checked against
the files. Verdict kept in `incr8_review-verdict.json`.

## After the review (2026-10-14; not evaluated)

Round 2's three wording notes, corrected after its verdict: the labeller's statement that it did not open the result files
is cited as its report in the build session, not verifiable from the repo; the reference's below-0.7 share is of verdicts,
not items; the re-audit bullet names its table column.

`incr8_review` passed on 2026-10-14 (approved by Chris in his own terminal): 799 tests passed and 13 skipped (Docker not
running), traceability (34 requirements), dogfood (2 hours logged for 2026-10-14) and the Evaluator (pass, 8.5).
