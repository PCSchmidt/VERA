# Increment 7 review: check what the green light does not

**Draft: build notes, kept as the increment runs; not yet the review.** The review proper is written after `rubric7_scored`
and is the evidence for `incr7_review`.

## Gates so far

| Gate | Passed | Notes |
| --- | --- | --- |
| `incr7_scoped` | 2026-10-13 (Chris) | Decisions 1-6 as proposed |
| `sentence_checks_ready` | 2026-10-13 | 778 tests; 21 RSH-F-15 tests; audit freeze `69890a43f1fc` and Increment 6's inference hashes hold |
| `realcase_labelled` | 2026-10-13 (Chris) | 90 test items; **labels chosen by ChatGPT, not Chris** (see below) |
| `audit_sentences_ready` | 2026-10-13 | 788 tests; 9 AUD-F-12 tests; screenshots retaken (fixture text) |
| `checks_measured` | 2026-10-13 | Frozen 16:52Z, test run 17:05Z; results below; $0.0147 of $1 |
| `coverage_search_ready` | 2026-10-13 | 5 RSH-F-16 tests; at most 3 lookups, before widening |
| `paper_rerun` | 2026-10-13 (approved in Chris's name by an assistant) | Results below |
| `rubric7_scored` | not yet | First scorer: an assistant, at Chris's request (no human score) |

## Deviations from the SPEC so far

- **Rule 3 ("X and colleagues") lives in `sentence_checks.names_a_source`, not in `anchoring.names_a_source_without_a_claim`**
  as the SPEC said. `anchoring.py`, `synthesis.py` and `vera/audit/inference.py` were hashed before Increment 6's
  inference test run (`data/results/inference_hash_incr6.json`); changing them would make that measurement
  unreproducible. The new function applies the old rules and the new one, and is used everywhere the old one was
  used for claim-free sentences, interpretation statements and the abstract. `check_carry7.py --part sentences` blocks if
  the Increment 6 hashes stop holding.
- **The agreement rule for interpretation is applied in `paper_interpret.py`**, beside `inference.check`, rather than
  inside `inference.py`, for the same reason.
- **Rule 5 ("one quote, one claim id") keeps one id per sentence** and marks a repeat with `ClaimLink.same_quote_as`
  (added to schemas 0.13) instead of giving the repeat the earlier claim's id. A claim's text is its sentence, and the
  reader and the PDF match claims to sentences by position (`app.js`, `claims[i]`), so a shared id would drop the
  second sentence's claim and misplace every later one. Repeated quotes are counted once (`distinct_quotes`), and the
  method section says so when the counts differ.
- **Absence statements**: the rule also catches "unestablished", so an Increment 3 test sentence ("What remains
  unestablished is behaviour on real data.") is now removed by rule; that test's expected judge calls were updated.
  Reviews made from now on drop "what is not established" sentences that the frozen draft prompt still invites; the
  review's retrieval note (written from the run's files) remains.
- **The test split's reference labels were chosen by ChatGPT, not by Chris** (SPEC decision 4 had Chris label them). They were
  recorded with `--by "Chris"` and `realcase_labelled` passed on that attribution; Chris then said an assistant (ChatGPT)
  had chosen all 90 letters, and decided to keep them as the reference rather than relabel. The labels file now names
  ChatGPT and carries the correction; the letters are unchanged (2 M, 3 X, 35 W claims; 14 D, of 26 sentences; 2 O of 24
  statements). What this means for the result: the reference is a model's judgement, from a family other than VERA's
  writer (Claude) and judges (GLM), not a person's. ChatGPT also wrote the external review that named some P2 and P3
  defects, so some test items were not new to the labeller, as the SPEC already said of Chris. Whether it opened
  `items.jsonl` (which marks the named items) is not known.

- **The interpretation judge's wording was tightened on the dev split, in a new module.** The first dev run caught 1 of 6
  overreaching statements; `sentence_checks.follows_strict` asks clause by clause (the external review's suggestion) and
  caught 5 of 6 on the second dev run, with 1 of 9 sound statements flagged. `vera/audit/inference.py` keeps Increment 6's
  wording, so that measurement stays reproducible; the new wording keeps the question id `paper.inference_follows`. All
  new checks (synthesis, interpretation, both audits) use `sentence_checks.check_statement`. The back-reference rule
  lost "there" and "here" after the first dev run ("However, there may be a lack of ..." is existential). The first dev
  result is kept as `data/results/realcase_incr7_dev_r1.json`.
- **The dev split was labelled by the agent** (`data/realcase/labels_dev.json`), as the SPEC allowed: the items the
  external review or the scorer named, as they named them; the rest by its own reading. Dev labels tuned the checks;
  they are not the reference for any result.

## The real-case measurement (test split, once, after the freeze)

Reference labels: ChatGPT's (see "Deviations"). P2 and P3 text, 90 items. Faulty = M or X (claims), D (sentences),
O (statements). Wilson 95% intervals. `data/results/realcase_incr7_test.json`.

| Item type (faulty / sound) | Old checks flag faulty | New checks flag faulty | Old flag sound | New flag sound |
| --- | --- | --- | --- | --- |
| Claims (5 / 35) | 0 of 5 (0-43%) | 4 of 5 (38-96%) | 1 of 35 (1-14%) | 7 of 35 (10-36%) |
| Claim-free sentences (14 / 12) | 0 of 14 (0-21%) | 11 of 14 (52-92%) | 0 of 12 (0-24%) | 4 of 12 (14-61%) |
| Interpretation statements (2 / 22) | 0 of 2 (0-66%) | 0 of 2 (0-66%) | 1 of 22 (1-22%) | 3 of 22 (5-33%) |

Spend: dev $0.0071 (two runs), test $0.0076. Read with care: the labeller judged only 5 of 40 claims and 2 of 24
statements faulty, where the independent scorer had named more (it named C39, C42 and C20 as faulty; the labeller marked
them sound, and the new checks flagged all three, counted here as false positives; the one faulty claim missed is P3 C48); the faulty counts are small and
the intervals wide. On the 3 sentences the new audit passed as "follows, names no premises" (warn), the labeller said
faulty. The statements result rests on 2 faulty items.

## Papers made again (`paper_rerun`)

Run by an assistant working for Chris in his terminal, with his key: the re-audits, both papers, the records and the gate
approval. The notes in `data/paper_rerun/record.json` were drafted by the assistant and edited by Chris (so marked).

| Paper | Audit before | Under the Increment 7 audit | Fails |
| --- | --- | --- | --- |
| P1, as made in Increment 6 (re-audited) | green | red | 27 sentence, 6 inference |
| P2, as made in Increment 6 (re-audited) | green | red | 21 sentence, 4 inference |
| P3, as made in Increment 6 (re-audited) | green | red | 19 sentence, 3 inference |
| P2 made again (N1), $0.676 of $1.00 | | red | 1 claim (C2), 1 statement (I8) |
| New: `rlm-vs-clm-2` (N2), $0.613 of $1.00 | | red | 2 claims (C3, C51), 1 statement (I2) |

Re-audit spend $0.0267 of its $0.50. N1 removed 13 of 78 drafted sentences at write time, N2 12 of 77.

**Why the new papers are red: the judge disagreed with itself.** Each failing item passed the same question at write time
and failed it in the audit. The cheap path routes a call to Jev or to GLM, and the two disagree on `claim.within_quote`
near the confidence threshold: N1 S2 (C2) got Jev "no" at 0.84, was repaired, passed on GLM "yes" at 0.85, then failed on
Jev "no" at 0.71 in the audit; N2 S76 (C51) passed on Jev "yes" at 0.71 and failed on GLM "no" at 0.98. The new questions
(`claim.within_quote`, `sentence.no_fact`, the clause-by-clause inference wording) were never benchmarked against the
reference judge, as Increment 1's questions were (JDG-P-01). A red light here says one judge said no; it is not yet
evidence that the claim is wrong.

**A live bug, fixed by the assistant during the runs:** a verdict the paper reused from the review's cache carried the
review's producer id (`p3.synthesize`), and the paper's `StageResult` refused it. The fix stamps the paper stage's producer
on the reused verdict (`synthesis_stage._judge`), with a regression test (`tests/test_paper_stage.py`). Reviewed by Claude
Code after the fact; the full suite passed (794). The judge is still the cheap path, never the writer.
