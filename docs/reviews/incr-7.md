# Increment 7 review: check what the green light does not

Written 2026-10-14 by Claude Code, from build notes kept while the increment ran (2026-10-13). This review is the evidence
for `incr7_review`. Plain about what was not shown.

## Outcome

Increment 6's three papers audited green while a careful reader found cited claims that said more than their quotes,
wrong uncited sentences, overreaching interpretation and repeated quotes read as corroboration. This increment gave every
sentence of a review or a paper's evidence sections a recorded status (claim, synthesis or transition), a check for each,
and an audit that re-checks every sentence. It also adds a targeted search for works a paper names. The review and the
paper share the new checks. No frozen file changed.

What the evidence says:

- **On real text, the Increment 6 checks flagged none of the faulty items; the new checks flag most.** On the frozen
  real-case test split (90 items from Increment 6's P2 and P3), old checks flagged 0 of 21 items labelled faulty; the new
  checks flagged 15 of 21 (claims 4 of 5, claim-free sentences 11 of 14, interpretation statements 0 of 2), and flagged 14
  of 69 sound items, against 2 of 69 for the old checks. The reference labels are a model's (ChatGPT's), not a person's.
- **Re-audited, all three Increment 6 papers turn from green to red** (22 to 33 failures each).
- **Papers made with the new checks are red on 2 and 3 items.** Each failing claim passed the same judge question at write
  time: the cheap path's two judges (Jev and GLM) disagree on the new questions near the confidence threshold (the two
  failing statements' write-time verdicts are not stored, so for them this is inferred). A red
  light here means one judge said no, not yet that the text is wrong.
- **A careful reader still finds about as many claim-level defects** (4 and 5 of 51 claims in the two new papers, against 3
  to 6 in Increment 6's three papers; N2 has more than P3, its nearest topic), and some defects of kinds the new checks pass. The new claim check did not close the gap the
  increment was opened for.

Who did what: Claude Code built and ran the offline work and the measurement. Chris approved `incr7_scoped` and
`rubric7_scored` in his own terminal; `incr7_review` is his to approve. **An OpenAI assistant (ChatGPT/Codex) working for Chris did the other
human steps**: it chose the test split's reference labels, ran the re-audits and made both papers with Chris's key, drafted
the paper notes (Chris edited them), approved `realcase_labelled` and `paper_rerun` in Chris's name (the gate records say "approved by Chris Schmidt" for
both, which does not show who ran the command), and was the first rubric scorer. Increment 7 therefore has **no human labels and no human scores**. Each is recorded under the name of who
did it (see "Deviations").

## Exit criteria (docs/07, SPEC)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| The real-case results reported for old and new checks | Yes, against a model's labels, not Chris's | `data/results/realcase_incr7_test.json`; "The real-case measurement" |
| The three Increment 6 papers re-audited | Yes | `data/paper_rerun/reaudit/*/audit_report.json` |
| Two papers made through the app with the new checks, each audited | Yes (both red); made by the OpenAI assistant with Chris's key, not by Chris as the SPEC said | `data/paper_rerun/{discuss-the-evolution-of-prompting-guv8,rlm-vs-clm-2}/` |
| The independent scorer's defect counts beside Increment 6's | Yes; Increment 6's counts are the notes of a different scorer instance | `data/results/rubric7_evaluator.json`, `rubric6_evaluator.json` |

## Each feature's acceptance criteria (SPEC)

| Feature (gate) | Acceptance criterion | Met? | Evidence |
| --- | --- | --- | --- |
| Schemas 0.13 | Round-trip, each raising rule raises, old documents load, schema version 0.13 | Yes | `tests/test_sentence_schemas.py` (10 cases); `gate-schema-version.sh` |
| Sentence status (`sentence_checks_ready`) | Offline tests: P1's "two studies disagree" removed; P3's absence sentence removed; "Shao and colleagues" caught; a "However, this ..." quote widened and re-verified; a repeated quote shares one id; a transition stating a fact repaired or removed; a claim adding a model name removed; a synthesis whose premise was removed repaired then removed; no self-grading; the review's tests still pass | Yes, except "shares one id" (a repeat is marked `same_quote_as`; see "Deviations"); two Increment 3/6 test expectations updated for the new checks | `tests/test_sentence_checks.py` (15); `check_carry7.py --part sentences` |
| The audit lists every sentence (`audit_sentences_ready`) | A factual claim-free sentence, an unsupported synthesis and an overstated claim reported; old documents audited; headless tests of the synthesis marking in light, dark, narrow; PDF appendix and light wording | Partly: the headless DOM test of the synthesis marking runs in one layout only; light, dark and narrow are screenshots (fixture text, as in Increment 6), not tests | `tests/test_sentence_audit.py` (8), `test_app_ui.py`; `docs/screenshots/paper-*.png` |
| Real-case set (`realcase_labelled`, `checks_measured`) | Labels by Chris, dated before the hash; hash predates the one test run; old and new results on every item | Partly: **labels by an OpenAI assistant, not Chris**; the freeze and the single test run as specified | `data/realcase/`, `data/results/realcase_hash_incr7.json` |
| Targeted search (`coverage_search_ready`) | Offline: a named work looked up once, found works join the evidence with new ids, a miss stated in threats, at most 3 lookups, nothing named means no lookup | Yes, offline; **no live lookup happened** (in the one live paper that named a work, it was already a source, R17) | `tests/test_coverage.py` (5); `paper/coverage.json` of N2 |
| Papers made again (`paper_rerun`) | Three re-audit reports and two new papers, each within its cap, each audited | Yes; run by the assistant | `check_paper_rerun.py` |
| Rubric (`rubric7_scored`) | Both score files; first scorer earlier and attributed; the independent scorer lists defects by id | Yes, with the first scorer an OpenAI assistant, not Chris | `check_rubric7.py` |
| Review (`incr7_review`) | Overhead entry for each day a gate passed; traceability; Evaluator passes | Overhead and traceability pass (32 requirements); Evaluator below | `check_dogfood.py`, `check_traceability.py` |

## What was built

- **Schemas 0.13** (docs/03 first): `SentenceRecord` (id, section, text, kind, claims, premises, verdicts, status, reason);
  `LiteratureSection.sentences` and `PaperDocument.sentences`; `ClaimLink.same_quote_as`; `Finding.check` "sentence".
- **`vera/literature/sentence_checks.py`** (new): the writer's `SENTENCE_RULE` (each sentence has a ref; a claim-free one
  declares "transition" or "synthesis" with premise refs), `parse_typed` beside the frozen parser, five rules without a
  model (agreement needs premises from two sources; absence statements removed from evidence sections; "X and colleagues"
  names a source; a quote opening with a back-reference is widened to the sentence before it, or fails; a repeated quote
  is marked and counted once), two judge questions (`claim.within_quote`, `sentence.no_fact`), and
  `check_statement` (Increment 6's rules, the two new rules, and the clause-by-clause inference question).
- **`verify_sentences`** (shared by the review and the paper) now checks claim-free sentences after the claims settle:
  a synthesis whose premise was removed, that names one source as several, or that the judge says does not follow is
  repaired once, then removed; a transition the judge says states a fact likewise. Every drafted sentence's outcome is
  logged and stored (`sentences.jsonl` for a review, `paper.json` for a paper). Review claims now carry ids.
- **`vera/audit/sentences.py`** (new): re-checks every sentence of reviews and papers; documents made before 0.13 are
  split into sentences and a factual claim-free sentence is checked as a synthesis of its section's claims (a warning if
  it follows, a failure if it does not). Interpretation statements are re-checked with `check_statement`.
- **Reader and PDF**: synthesis sentences boxed with premise links; an audit list of synthesis and removed sentences;
  PDF Appendix D (synthesis and removed sentences); Appendix B marks a repeated quote; the light's wording names what green
  covers when the sentence audit ran (older audits keep their wording); the run page and PDF say which spend they show.
- **`vera/literature/coverage.py`** (new, RSH-F-16): works named in the question or emphasis (a quoted title, with its
  first author when an author line follows; an arXiv id; "Name et al."), looked up (at most 3) when not already a source;
  found works read first into the paper's evidence (`paper/added_records.jsonl`); the threats section says what was
  searched for and the outcome. The review's files are not changed.
- **Measurement and records**: `scripts/build_realcase_set.py`, `record_realcase_labels.py`, `measure_realcase.py`,
  `reaudit_incr6.py`, `set_aside_paper.py`, `record_paper_rerun.py`, `record_rubric7.py`; checks
  `tools/checks/check_carry7.py` (parts sentences, realcase, audit, measured, coverage), `check_paper_rerun.py`,
  `check_rubric7.py`. 794 tests pass (`docs/results/incr7_test_run.txt`; 753 at Increment 6).

## The real-case measurement

Items are real text from Increment 6's papers, not written by the checks' author: cited claims with their quotes,
claim-free evidence sentences with their section's claims, and kept interpretation statements with their premises. Split
by paper: dev is P1 (50 items, labelled by Claude Code from the external review and the scorer's notes, and its own
reading), test is P2 and P3 (90 items: every item the external review or the scorer named, plus a seeded random sample,
shuffled, with no mark of which were named). Faulty = says more than its quote or needs outside context (claims); does not
follow or contradicts (sentences); overreaches (statements).

**Dev, used to tune** (`realcase_incr7_dev_r1.json`, then `realcase_incr7_dev.json`): the first run caught 1 of 6
overreaching statements, and the back-reference rule fired on "However, there may be ...". Two changes, on dev only: the
rule dropped "there" and "here"; the interpretation question was reworded clause by clause (`sentence_checks.follows_strict`,
keeping the id `paper.inference_follows`). Second dev run: claims 6 of 6 faulty flagged (3 of 14 sound), sentences 6 of 6
(4 of 9), statements 5 of 6 (1 of 9). Tuning stopped there: the dev labels are the checks' author's.

**Test, once, after the freeze** (frozen 2026-10-13T16:52Z: items, labels and the source of all seven check files; run at
17:05Z; `realcase_incr7_test.json`), against ChatGPT's labels, Wilson 95% intervals:

| Item type (faulty / sound) | Old checks flag faulty | New checks flag faulty | Old flag sound | New flag sound |
| --- | --- | --- | --- | --- |
| Claims (5 / 35) | 0 of 5 (0-43%) | 4 of 5 (38-96%) | 1 of 35 (1-14%) | 7 of 35 (10-36%) |
| Claim-free sentences (14 / 12) | 0 of 14 (0-21%) | 11 of 14 (52-92%) | 0 of 12 (0-24%) | 4 of 12 (14-61%) |
| Interpretation statements (2 / 22) | 0 of 2 (0-66%) | 0 of 2 (0-66%) | 1 of 22 (1-22%) | 3 of 22 (5-33%) |

"Old" is what Increment 6's green light rested on, run on the same items with the same judge path: for claims the
passage-support and quote-alone questions and the connective and back-reference rules; for sentences the source-name
screen; for statements Increment 6's inference check. Spend: dev $0.0071, test $0.0076, $0.0147 of the $1 cap.

Read with care:

- The faulty counts are small (5, 14, 2) and the intervals wide. The statements result rests on 2 faulty items and says
  nothing either way.
- **The labeller and the Increment 6 scorer disagree.** ChatGPT labelled P2 C39, C42, C46 and P3 C20 sound; the Increment 6
  scorer had named them faulty. The new checks flagged C39, C42 and C20 (here counted as false positives) and not C46,
  which under the scorer's reading they miss. The one claim labelled faulty that the new checks missed is P3 C48.
- Three sentences the labeller called faulty the new audit passed with a warning ("follows, names no premises").
- The labeller had written the external review that named some of these defects; whether it opened `items.jsonl`, which
  marks the named items, is not known.

## Papers made again (`paper_rerun`)

| Paper | Audit before | Under the Increment 7 audit | Failures |
| --- | --- | --- | --- |
| P1, as made in Increment 6 (re-audited) | green | red | 27 sentence, 6 inference |
| P2, as made in Increment 6 (re-audited) | green | red | 21 sentence, 4 inference |
| P3, as made in Increment 6 (re-audited) | green | red | 19 sentence, 3 inference |
| N1: P2's paper made again, same request; $0.676 of $1.00; 40 minutes | | red | 1 claim (C2), 1 statement (I8) |
| N2: a paper from the `rlm-vs-clm-2` review, emphasis naming "Context Language Models"; $0.613 of $1.00; 14.5 minutes | | red | 2 claims (C3, C51), 1 statement (I2) |

Re-audits $0.0267 of their $0.50 cap (903 judge calls, about $0.009 a paper, from the ledger: the reports' own
`total_cost_usd` undercounts, at about $0.001 a paper; 204 to 261 seconds each), on temporary copies
of the live runs (the runs' own audits are untouched). At write time N1 removed 13 of 78 drafted sentences and N2 12 of 77.

**The cost of the extra checks, per paper** (from each run's ledger, from the paper's start; the judge figure includes the
paper's audit):

| Paper | Total | Writer (`p3.paper.write`) | Interpretation | Judges (`p2.cheap_path`) | Writer calls | Judge calls | Wall time (N1 and N2 ran at the same time) | Audit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Increment 6 P2 | $0.562 | $0.497 | $0.055 | $0.0095 | 15 | 260 | 8 min | 76 s |
| N1 (P2 made again, same review and request) | $0.676 | $0.604 | $0.057 | $0.016 | 29 | 687 | 40 min | 196 s |
| Increment 6 P3 (`rlm-vs-clm-3`) | $0.525 | $0.464 | $0.054 | $0.0074 | 14 | 231 | 7 min | 70 s |
| N2 (`rlm-vs-clm-2`, a different review on a similar topic) | $0.613 | $0.530 | $0.072 | $0.011 | 22 | 460 | 14.5 min | 131 s |

On the one like-for-like pair (N1 against P2) the checks added $0.114 (20%): $0.107 of it is the writer, which made 29
calls against 15. The code makes a second repair call in a section only when a claim-free sentence there fails its check;
that this accounts for the extra calls is inferred from the code and the counts, not traced call by call. The new judge
questions added about $0.0065 (687 calls against 260). The audit takes two and a half times as long. N1 and N2 were started
at the same moment (18:36:41Z) and ran side by side, so N1's 40 minutes include waiting on shared services and are not a
clean measure of the checks' time. N2 against P3 is not like for like (another
review), so it bounds nothing; it is shown for scale.

**Why N1 and N2 are red: the judge disagreed with itself.** Each failing claim passed the same question at write time and
failed it in the audit. The cheap path routes a call to Jev or GLM, and they disagree on `claim.within_quote` near the
0.7 confidence threshold: N1 S2 (C2) got Jev "no" at 0.84, was repaired, passed on GLM "yes" at 0.85, and failed on Jev
"no" at 0.71 in the audit; N2 S4 (C3) passed on GLM "yes" at 0.95 and failed on Jev "no" at 0.72; N2 S76 (C51) passed on
Jev "yes" at 0.71 and failed on GLM "no" at 0.98. The two failing statements (N1 I8, N2 I2) passed the same
clause-by-clause check at write time (`paper_interpret` uses `sentence_checks.check_statement`), but their write-time
verdicts are not stored (`inferences.jsonl` keeps `verdicts: []`, as in Increment 6), so for them the disagreement is
inferred, not shown. The new questions
were never benchmarked against the reference judge, as Increment 1's were (JDG-P-01). The independent scorer also flagged
N2 C51, so not every such red is noise.

**A live bug, fixed during the runs** by the assistant: a verdict the paper reused from the review's cache carried the
review's producer id (`p3.synthesize`), which the paper's `StageResult` refused. The fix stamps the paper stage's producer
on the reused verdict (`synthesis_stage._judge`), with a regression test. Claude Code reviewed it after the fact; the
judge is still the cheap path, never the writer, and the full suite passes.

## Rubric scores and defects (`rubric7_scored`)

First scorer: an OpenAI assistant (recorded as "OpenAI Codex", at Chris's request), blind, 21:19Z. Independent scorer: a
fresh Claude agent, kept from the first scores, the external review, the audits and the build notes, which read every
kept claim against its quote, every synthesis against its premises, every transition and every statement.

| Paper | First (OpenAI) | Independent (Claude) | Prefers (first / independent) |
| --- | --- | --- | --- |
| N1 | 4 4 3 5 4 3 | 3 3 4 4 4 4 | paper / paper |
| N2 | 4 4 3 5 5 3 | 2 3 3 4 3 3 | paper / review |

Criteria: answers the question, coverage, correctness, reproducibility, honesty, interpretation follows. 3 of 12 cells equal.

| Defects listed by the independent scorer | N1 (51 claims) | N2 (51 claims) | Increment 6: P1 (55) / P2 (59) / P3 (57), scorer's notes |
| --- | --- | --- | --- |
| Claims saying more than, or leaning on context outside, their quotes | 4 (C7, C9, C42, C44) | 5 (C20, C22, C33, C47, C51) | 4 (C14, C28, C41, C53) / 6 (C25, C31, C39, C40, C42, C46) / 3 (C20, C25, C48) |
| Synthesis sentences that do not follow | 1 (S70) | 1 (S36) | no sentence records then; uncited sentences named: P1 3, P2 1, P3 2 |
| Transitions that state or promise something unsupported | 0 | 2 (S16, S56) | (counted in the row above) |
| Interpretation statements that overreach | 3 (I5, I6, I10) | 2 (I7, I17) | P1 2 (I3, I8) / P2 2 (I7, I17) / P3 1 (I3) |

Claim-level defects per paper are about the same as in Increment 6 (4 and 5 against 3 to 6; N2 has more than P3, its
nearest topic). Different scorer instances, two papers, one reading each: not a measurement.

The scorer preferred N2's review to its paper: the checks removed the statements on latency and trace reuse, so the paper
answers less of its question, and it repeats the 35% SCR figure five times.

## What the checks still miss

From the scorer's defects, each passed by the new checks:

- **Claims that say a little more than their quotes** (N1 C9 drops "during extended coding sessions"; N2 C33 adds "applied
  zero-shot"; N1 C44 gives a cited work's view to the survey citing it). `claim.within_quote` passes many of these.
- **A transition about the paper itself** ("a small CPU-scale experiment accompanies the analysis", N2 S16; a promise to
  take up trace reuse, S56): `sentence.no_fact` counts a statement about the paper as stating no fact about the literature,
  so a promise the paper does not keep passes.
- **Several sources from one** in words the agreement rule does not list ("sources list", N1 I6).
- **A synthesis that adds a contrast** its premises do not make (N1 S70, "different registers").
- **Two judges that disagree** on the same item (above), so the light can change between write and audit.

## Spend, overhead, independence

| Cap (SPEC) | Spent | Source |
| --- | --- | --- |
| $1 debugging and smoke runs | $0 in model calls (all development offline) | ledgers |
| $1 real-case measurement | $0.0147 | `data/ledger/realcase_incr7_*.jsonl` |
| $0.50 re-audits | $0.0267 | `data/ledger/reaudit_incr7.jsonl` |
| $2 papers (cap $1.00 each) | $1.289 (N1 $0.676, N2 $0.613) | the runs' ledgers, less each review's spend |
| $5 increment | $1.331 in all ledgers since `incr6_review` | ledgers |

Overhead: 2 hours logged for 2026-10-13 (`check_dogfood.py` passes). Same-model overlap: the writer, the checks' author,
the dev labeller and the independent scorer are Claude models; the judges are GLM and Jev; the reference labels and the
first scores are an OpenAI model's.

## Deviations from the SPEC

- **No human labels or scores.** The SPEC had Chris label the test split and score first. An OpenAI assistant did both at
  his request. The labels were first recorded as "Chris"; when Chris said an assistant had chosen them, the file was
  corrected to name it ("ChatGPT (OpenAI)"), and Chris decided to keep them as the reference rather than relabel. The
  rubric file names "OpenAI Codex". The same assistant approved `realcase_labelled` and `paper_rerun` in Chris's name, and
  drafted the paper notes, which Chris edited (marked in `record.json`).
- **New rules in a new module** (decided by Claude Code during the build and reported to Chris after `sentence_checks_ready`, not asked
  beforehand; decision 6's "stop and ask" covers the Increment 5 frozen files, which were not touched). The SPEC put "X and colleagues" in `anchoring.names_a_source_without_a_claim` and the
  agreement rule beside `inference.py`. Those files, with `synthesis.py`, were hashed before Increment 6's inference test
  run; changing them would make that result unreproducible. The rules are in `sentence_checks.py`, used everywhere the old
  ones were, and `check_carry7.py` blocks if the Increment 6 hashes stop holding.
- **The interpretation question was reworded in the new module** (`follows_strict`), with the same id; Increment 6's
  wording is unchanged in `inference.py`.
- **"One quote, one claim id" became a mark.** A repeated quote keeps its own claim id and gets `same_quote_as` (added to
  0.13): a claim's text is its sentence, and the reader matches claims to sentences by position, so a shared id would put
  claims on the wrong sentences. Repeats are counted once and marked in Appendix B.
- **Reviews lose "what is not established" sentences**, which the frozen draft prompt still invites; the review's
  retrieval note says what retrieval did not find. Two earlier tests' expectations were updated for the new checks.
- **The targeted search ran no live lookup**: the one live paper naming a work already had it as a source.
- **Screenshots** show the UI tests' fixture paper, as in Increment 6.

## Next SPEC (candidates, in my order)

1. **Benchmark the new judge questions against the reference judge** (`claim.within_quote`, `sentence.no_fact`, the
   clause-by-clause inference question), as Increment 1 did for the first questions; fix the routing so the write step and
   the audit ask the same judge, or require agreement, so the light does not change between them.
2. **Close the misses above**: claim-level additions (a stricter or second claim check, measured), statements about the
   paper itself, a wider agreement vocabulary, contrasts a synthesis adds.
3. **A person labels and scores.** Every reference in this increment is a model's; a human-labelled set, even small, is the
   missing measurement.
4. Carried: the reader-facing cost of the checks (N2 answers less of its question than its review); Increment 8 (the auditor
   on external papers).

## Independent Evaluator

Verdicts in `.meridian/evaluator/incr7_review-verdict*.json`.

**Round 1** (warn, 7.2; completeness 6.5, quality 7.5, consistency 7.5, spec adherence 7): every figure it checked matched the
files. Gaps: the SPEC's "cost of the extra checks per paper" given for N1 only, in one sentence; "Chris approved this review"
written before he had; the red explanation extended to statements whose write-time verdicts are not stored; P2 C46 left out
of the labeller/scorer disagreement; only Increment 6's P2 in the defect comparison; the audit feature marked met though its
headless test runs in one layout; no statement whether Chris was asked before the rules moved module; the gate records'
approver not explained; papers "made through the app" without saying by whom. Verdict kept in
`incr7_review-verdict-r1.json`. After it, each was corrected in the text above (the cost table; the approval wording; the
red explanation limited to claims, with N2 C3 added; C46; all three Increment 6 papers; "Partly"; the module decision; the
gate records; the exit row).

**Round 2** (pass, 8.3; completeness 8.5, quality 8.5, consistency 7.5, spec adherence 8): all ten round-1 gaps fixed and
the new figures verified against the ledgers and run files. Verdict kept in `incr7_review-verdict.json`.

## After the review (2026-10-14; not evaluated)

Round 2's five non-blocking notes, corrected after its verdict: the Outcome's two summary bullets brought in line with the
corrected sections (claims only for the judge disagreement; all three Increment 6 papers for the defect comparison); the
cost table says N1 and N2 ran at the same time, so N1's wall time is not a clean measure; the re-audit cost is said to come
from the ledger (the reports' `total_cost_usd` undercounts); the explanation of the extra writer calls is marked as inferred.

`incr7_review` passed on 2026-10-14 (approved by Chris in his own terminal): traceability (32 requirements), dogfood and the
Evaluator (pass, 8.3); the test hook ran 781 passed and 13 skipped (Docker was not running, so the sandbox and harness tests
skipped; all 794 passed earlier that day with Docker up, `docs/results/incr7_test_run.txt`).
