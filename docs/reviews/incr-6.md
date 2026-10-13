# Increment 6 review: from a review to a paper

Date: 2026-10-12 · Reviewer: Chris (decisions and human gates) · Author: Claude Code
Gates passed: `incr6_scoped` (Chris, through the engine, 2026-10-11), `evidence_ready`, `paper_stage_ready`, `inference_set_frozen`,
`inference_measured`, `app_paper_ready` (automated, 2026-10-11), `paper_demo` and `rubric6_scored` (Chris, through the engine,
2026-10-12). This review is the evidence for `incr6_review`.

## Outcome

A finished literature review can now be turned, from a button in the app, into a review paper (2,532 to 2,722 words of prose, below the
3,000-word target; see "The three papers"): wider reading, an
introduction and findings sections in which every cited sentence carries a quote, method and threats sections written from the run's files,
and labelled interpretation sections (discussion, conclusions, research agenda) whose statements name their premises and are judged by a
model other than their writer. Three papers were made through the app by Chris with his own key, each audited green; the first went over the SPEC's $0.75
per-paper cap (see "Spend").
In order of how much each statement should be trusted:

1. **Built and tested.** The paper stage, its interpretation stage and audit, the button, the reader and the PDF exist, with 753 tests
   (`docs/results/incr6_test_run.txt`) and gates for each part. No audit file frozen at Increment 5 was changed (hash `69890a43f1fc`, checked
   at every gate).
2. **The papers are longer and wider than the reviews they came from, and both scorers preferred the paper in five of six judgements.** Each
   rests on 55 to 59 claims from 16 to 27 sources (the reviews: 15 to 21 claims), with 15 papers read in full (the reviews: 6).
3. **A green audit on a paper is a floor, and a lower one than on a review.** An external review (ChatGPT, commissioned by Chris) and the
   independent scorer found, in papers that passed green: cited claims that say more than their quotes, uncited synthesis sentences that are
   wrong, interpretation statements that overreach, and quotes that lean on context outside them. The measured inference check (48 of 48
   planted faults caught) does not describe this: its faults were blatant and written by the agent that wrote the check.
4. **The first live paper exposed a cost bug** (repair prompts carried every passage of the paper), fixed and covered by a test the same day.

## Exit criteria (docs/07, SPEC)

| Criterion | Met? | Evidence |
| --- | --- | --- |
| Three papers made through the app from real reviews, within their caps, each audited | Yes, with a qualification: P1 went over the SPEC's $0.75 per-paper cap before its cap was raised (see "Spend") | `data/paper_demo/` (record and copied files), `check_paper_demo.py`: $0.774, $0.562, $0.525 of $1.00 caps; all green |
| The inference check's detection and false-positive rates reported | Yes, with a strong qualification | `data/results/inference_incr6_test.json`; see "The inference check" |
| Both scorers' blind scores for each paper beside its review | Yes | `data/results/rubric6_chris.json` (before), `rubric6_evaluator.json` (after); `check_rubric6.py` |
| No frozen audit file changed | Yes | `check_carry6.py` at every automated gate |

## Each feature's acceptance criteria (SPEC)

| Feature (gate) | Acceptance criterion | Met? | Evidence |
| --- | --- | --- | --- |
| Schemas 0.12 | Round-trip tests, each raising rule tested, `check_schema_version` at 0.12 | Yes | `tests/test_paper_schemas.py`; `gate-schema-version.sh` |
| Wider evidence (`evidence_ready`) | Superset with unchanged ids; at most 15 full texts and 10 passages each; failures fall back and are reported; no re-fetch; no frozen file changed; RSH-F-14 tests | Yes | `tests/test_paper_evidence.py`; `check_carry6.py --part evidence`; on the live run 16 of 16 review claims re-verified |
| Paper stage (`paper_stage_ready`) | Planted faults removed as in the review; record sections hold no model text and only file numbers; too little evidence stops; no self-grading; RSH-F-12 tests | Yes | `tests/test_paper_stage.py`, `test_paper_pipeline.py`; `check_carry6.py --part paper` |
| Interpretation and inference check (`inference_set_frozen`, `inference_measured`) | Every deterministic rule tested; removal on a no or unsure verdict; the writer never sees a passage; set hashed before the test run; rates reported whatever they are; RSH-F-13 and AUD-F-11 tests | Yes, with the qualification under "The inference check" | `tests/test_paper_interpret.py`; `data/results/inference_*` |
| App (`app_paper_ready`) | Endpoint refusals; own cap; stop and resume; key scan with the new routes; headless tests of button, tabs and box in light, dark, narrow; PDF label and appendices; APP-F-04 tests | Yes, except that the screenshots show a fixture (see "Deviations") | `tests/test_app_paper.py`, `test_app_ui.py`; `gate-app-secrets.sh`; `check_carry6.py --part app` |
| Static showcase (APP-F-04) | Button hidden when `window.VERA_STATIC` is set; both modes in step | Hidden and tested (`test_APP_F_04_the_front_end_offers_the_paper_and_hides_it_in_the_static_showcase`); **no paper was added to the showcase** (publishing is Chris's decision) | `vera/app/static/app.js` |
| Papers from real reviews (`paper_demo`) | Three records within their caps, each with an audit report, spend read from the ledger | Yes, with two deviations: P1 over the SPEC's per-paper cap; `record.json` holds notes, not the figures (see "Deviations") | `check_paper_demo.py` |
| Rubric (`rubric6_scored`) | Both score files; Chris earlier and attributed; not a copy | Yes | `check_rubric6.py` |
| Review (`incr6_review`) | Overhead entry for each day a gate passed; traceability; Evaluator passes | Traceability passes (29 requirements); **the overhead check blocks** until Chris logs 2026-10-11 and 2026-10-12; Evaluator below | `check_dogfood.py`, `check_traceability.py` |

## What was built

| Part | Where | Requirement |
| --- | --- | --- |
| Schemas 0.12: `PaperSection`, `Inference`, `PaperRequest`, `PaperDocument`; `ClaimLink.id`; `Finding.check` "inference"; stages "paper", "interpret" | `vera/schemas/paper.py`, docs/03 | RSH-F-12, RSH-F-13 |
| Wider evidence: up to 15 kept papers in full, 10 passages each, a superset of the review's passages with unchanged ids; no new search | `vera/literature/paper_evidence.py` | RSH-F-14 |
| Paper stage: outline (themes the evidence supports), evidence sections through the review's own checks (now one shared `verify_sentences`), method and threats sections from the run's files | `vera/literature/paper.py`, `paper_stage.py`, `synthesis_stage.py` | RSH-F-12 |
| Interpretation: written from verified claims only (the writer never sees a passage); deterministic rules, then `paper.inference_follows`; one repair; removed statements kept on record; abstract checked the same way, else a plain one | `vera/literature/paper_interpret.py`, `vera/audit/inference.py` (new, not frozen) | RSH-F-13 |
| Paper audit: the frozen literature audit on the paper, then every kept statement re-checked | `vera/app/pipeline.py` `run_paper_audit` | AUD-F-11 |
| App: button and form, live view with stop and resume (and a raised cap on resume), Review and Paper tabs, interpretation boxed with premise links, PDF with Appendix C | `vera/app/` | APP-F-04 |

The paper runs after the review's last node in the same run (`extend_run`), so nothing the review did is repeated and its spend stays on
record; the paper has its own cap on top. On the first real run, the widening step alone took the agent-traces review from 6 papers in full and
65 passages to 15 and 185, with all 16 review claims still verifiable against the larger set, at no model cost.

## The three papers

| Paper | Paper cost | Audit | Prose words (all body tokens) | Claims (sources) | Claims removed by the checks | Statements kept |
| --- | --- | --- | --- | --- | --- | --- |
| P1 agent traces (`how-much-useable-information-about-6x3n`) | $0.774 (about $0.21 to $0.25 of it the repair bug) | green | 2,617 (3,331) | 55 (27) | 3 of 58 | 17 of 17 |
| P2 prompting to harness (`discuss-the-evolution-of-prompting-guv8`) | $0.562 | green | 2,722 (3,358) | 59 (18) | 6 of 65 | 17 of 17 |
| P3 RLM and CLM (`rlm-vs-clm-3`) | $0.525 | green | 2,532 (3,221) | 57 (16) | 3 of 60 | 16 of 17 |

Prose words are the summary, evidence and interpretation sections split on whitespace; the SPEC's length excludes the record
sections (method, threats), so all three fall short of the 3,000-word target by 278 to 468 words. The figure in brackets counts every word
token of `paper.md` before the references, including citation markers, headings and the record sections.

Chris's notes (`data/paper_demo/record.json`): P1 "a useful, transparent exploratory review, but it needs revision before being treated as
authoritative"; P2 "a strong paper-shaped synthesis ... though some uncited synthesis sentences still overstate how settled the boundaries
are"; P3 "honest evidence gaps, but the named CLM target and production-coding evidence remain too thin for a confident bottom-line comparison".
The P2 and P3 notes were first recorded as a placeholder ("...") and replaced with these after `paper_demo` had passed; the check accepted the
placeholder at the time and now refuses one (fewer than 20 characters or no letters).

## Live runs and the defects they found

1. **Repair prompts held every passage of the paper.** The first paper stopped at its $0.75 cap with $0.55 spent: the review's repair prompt,
   reused for the paper, listed all 185 widened passages (about 65,000 input tokens, $0.13 per repair). Fixed: a repair is shown the passages
   its section was drafted from and is still checked against all of them (`verify_sentences(repair_passages=...)`, test
   `test_RSH_F_12_a_repair_shows_the_sections_own_passages_not_the_whole_paper`). The two later papers cost $0.56 and $0.53.
2. **A paper stopped at its budget could not be resumed with a higher cap**, though the message said that was what it needed. Fixed: the resume
   takes a raised cap (never a lower one), and the form's default cap became $1.00 at Chris's request.
3. **The live view stopped polling once a paper had stopped**, so a resumed paper looked frozen. Fixed: it polls while open and repaints only on
   a change.
4. **One full-suite run had a failing headless-browser page test** that passed on rerun, while the app and a paper worker were running on the
   same machine (the suite took 9 minutes instead of 2.5). Recorded as a timing flake, not investigated further.

## The inference check: what 48 of 48 means

The seeded set (`data/seeded_inference/`, 108 items, built by `scripts/build_inference_set.py`) has hand-written controls (cautious readings of
real claims from nine committed reviews) and faults made from them: reversed, overstated, an added fact, an irrelevant premise (judge layer),
and a named source or an unsupported number (rules layer). Split by review; the dev split was run once (all caught, $0.0006) and the question's
wording was not changed; the test split and the check's source were hashed (`data/results/inference_hash_incr6.json`) before the one test run.

| Test split (72 items) | Result | Wilson 95% |
| --- | --- | --- |
| Judge-layer faults caught | 48 of 48 | 93% to 100% |
| Controls wrongly failed | 0 of 12 | 0% to 24% |
| of which reversed / overstated / added fact / irrelevant premise | 12 / 12 / 12 / 12 of 12 each | 76% to 100% each |
| Rules-layer faults caught (named source 6 of 6, unsupported number 6 of 6) | 12 of 12 | 76% to 100% (61% to 100% each) |
| Spend (dev and test) | $0.0018 of the $1 cap | |

One of the 48 judge-layer faults (an irrelevant premise whose text names a system only its own review mentions) was caught by the
name rule before it reached the judge, so the judge itself decided 47.

**This does not show the check catches real overreach.** The same agent wrote the check, the controls and the faults; the faults are blatant
("PROVES", "always", an invented clinical trial). In the three live papers, 50 of 51 drafted statements were kept, and both the external review
and the independent scorer found kept statements that overreach (P1 I3, I8, I1, I15; P2 I7 and I17 contradict each other on the same claims).
The false-positive interval rests on 12 controls. The next test set should be built from these real cases, by someone other than the check's
author.

## What the green audits missed

Found by the external review (`docs/results/incr6_external_review.md`, ChatGPT, of P1 only, commissioned by Chris; checked against all three
papers in its appendix) and by the independent scorer (all three papers, every claim read against its quote):

| Defect | Where (examples) | Why the checks passed it |
| --- | --- | --- |
| **A cited claim says more than its quote** (the classification of P1 C28 and P3 C48 is the author's, from reading each against its quote; the scorer's file lists them as leaning on context) | P2 C25, C31 ("calls this a structured form of context engineering"; the quote does not, and the phrase carries P2's abstract); P1 C28 adds "GPT-3.5-turbo"; P2 C42, C46, C39, C40; P3 C48. The scorer's recorded notes (`rubric6_evaluator.json`) name 4, 6 and 3 such claims: P1 C14, C28, C41, C53 and P3 C20, C25, C48
as leaning on context outside their quotes; P2 C25, C31, C46, C42, C39, C40 as saying more than their quotes | The passage-support judge and the quote-alone judge both said yes. This is the defect class VERA's main promise is about, and the cheap judge is not catching it at this rate |
| **An uncited synthesis sentence is wrong** | P1 "The two studies therefore disagree..." (both cited sentences are one source; the disagreement is with C54, later); P3 "no passage covers recursive language models on cost" (contradicts C5, C15); P2 "Another paper, by contrast..." (no source) | Claim-free sentences are only screened for naming a source; 23 to 33 per paper are not checked at all, and the audit enumerates cited sentences only |
| **A claim-free sentence names a source** | P3 "...by Shao and colleagues" | The source-name rule catches `[Rn]`, bare `R12`, "et al." and author-year, not "X and colleagues" |
| **A quote leans on context outside it** | P1 C41 ("However, this patch may be overfitting."), C53; P3 C20, C25; 3, 6 and 3 quotes per paper open with a demonstrative | The quote-alone judge passed them |
| **Interpretation overreaches** | See the inference check | The judge accepts statements that mostly restate claims, and some that add a step |
| **Repeated quotes read as corroboration** | 3, 10 and 14 claims reuse a quote already used | Nothing counts distinct propositions |
| **Coverage gaps not flagged** | P2's question asks for practitioner literature, almost none present; P3 never retrieved the Context Language Models paper (Shao et al.) that Chris named in the paper's emphasis (it says so) | Retrieval was not repeated for the paper (SPEC decision 4); the threats section says the search was not repeated but cannot say what it missed |

The external review also noted the run page showing $0.94 against the PDF's $0.77: the page shows the whole run (review $0.16 and paper
$0.77). Not a defect in the figures; the page should say which it shows.

## Rubric scores (both scorers)

Chris scored first and blind (`rubric6_chris.json`, 19:03Z); the independent scorer, a fresh Claude agent told not to open Chris's scores, his
notes or the external review, scored afterwards (`rubric6_evaluator.json`, 19:11Z). Criteria: answers the question, coverage, correctness,
reproducibility, honesty, interpretation follows from evidence; 1 to 5.

| Paper | Chris | Independent | Prefers (Chris / independent) |
| --- | --- | --- | --- |
| P1 | 4 3 3 4 5 3 (helped by the ChatGPT external review) | 3 3 3 4 4 3 | paper / paper |
| P2 | 5 4 4 4 5 4 | 3 2 2 4 3 3 | paper / same |
| P3 | 4 3 3 4 5 4 | 3 2 3 4 4 4 | paper / paper |

The SPEC asked for each paper to be scored beside the review it came from. Both scorers read the review and gave a preference, but **the
three source reviews were not themselves scored on this rubric**, so there is no score-for-score comparison of paper against review; the
preference is the only comparison.

8 of 18 cells are equal, and Chris is at or above the independent scorer in every cell, as in Increment 5. Means: Chris 3.94, independent 3.17.
The largest gap is P2 (Chris's highest, the scorer's lowest), driven by the C25/C31 misstatement and the missing practitioner literature, which
the scorer found by reading every claim against its quote. Coverage and correctness are the lowest criteria on the independent sheet;
reproducibility (4 throughout) is the only criterion on which the two agree on every paper. Both prefer the paper in five of six judgements.
Chris's P1 score had model help (he had read the external review), and is marked so.

Against Increment 5's reviews (independent mean 2.93), the papers score a little higher on the independent sheet (3.17 on six criteria, 3.13 on
the five shared ones). That is not evidence that quality improved: different documents, different questions, a new criterion, and three papers.

## Spend, overhead, same-model overlap

| Cap (SPEC) | Spent | Source |
| --- | --- | --- |
| $1 debugging and smoke runs | $0 in model calls (all development ran on offline fakes; the widening trial made no model call) | ledgers |
| $0.75 per paper (SPEC; the form's default) | P1 $0.774, **over**: it stopped at $0.75 with $0.549 spent (the repair bug), and Chris raised its cap to $1.00 on resume; P2 $0.562 and P3 $0.525 under $0.75 (their caps were $1.00) | `paper/request.json` (0.75) and `paper/app_paper_request.json` (1.00) |
| $2 papers from real reviews | $1.861 (three papers) | `data/paper_demo/*/ledger.jsonl` less each review's spend |
| $1 inference measurement | $0.0018 | `data/ledger/inference_incr6_*.jsonl` |
| $5 increment | $2.32 in all ledgers since 2026-10-11, including the reviews made for the demos ($0.16 agent traces, which prompted the increment; $0.17 prompting; $0.13 on the RLM and CLM
review's ledger since 2026-10-11, a review started on 2026-10-07) | ledgers |

Overhead: Chris logs it (`scripts/dogfood.sh overhead`). Met after the Evaluator's rounds (see "After the review"): 4 hours for
2026-10-11 and 2026-10-12 in total.
Same-model overlap: the writer and the independent scorer are Claude models; the judges are GLM (and Jev when its key is set); the external review
is ChatGPT, a different family, and found the same classes of defect.

## Deviations from the SPEC

- **Screenshots** (`docs/screenshots/paper-*.png`, `makepaper-light.png`) show the UI tests' fixture paper, not a real one, and the narrow
  layout is 548 px wide (headless Chrome will not render narrower). They record the layout; real screenshots are not yet taken.
- **The paper's default cap** became $1.00 (SPEC: $0.75), at Chris's request after the first paper stopped.
- **Resume with a raised cap**, polling, and the repair-prompt fix were not in the SPEC; each followed from the first live paper.
- **The `paper_demo` notes** for P2 and P3 were replaced after the gate passed (see "The three papers").
- **`record.json` holds run ids and notes only**, not the caps, spend, audit light, wall time and kept/removed counts the SPEC listed:
  the check computes those from the copied run files, so no figure is typed. Wall time, from `paper/app_state.json` and the ledgers: P2
  8 minutes (12:17 to 12:25Z), P3 7 minutes (11:30 to 11:37Z); P1 16:36 to 19:46Z, which spans its stop at the cap and a three-hour pause
  before the resume (the resume ran 19:40 to 19:46Z). The audits took 89, 76 and 70 seconds (`audit_report.json` `wall_seconds`).
- **The external review** was not planned; Chris commissioned it, and it is kept unedited with provenance.
- **No frozen file changed**, though Chris had allowed it (decision 2); none needed to.

## Next SPEC (candidates, in my order)

1. **Check what the green light does not.** Give every sentence of an evidence section a status (cited claim, synthesis, transition) and check
   synthesis sentences the way interpretation statements are checked; rebuild the inference test set from the real cases above, by someone other
   than the check's author; then measure. This includes the claim-level overstatement the cheap judge passes (P2 C25): measure the claim judges on
   these cases before trusting them more.
2. Cheap deterministic rules: a quote that opens with a demonstrative needs its preceding sentence; "X and colleagues" counts as naming a source;
   count distinct quotes and propositions.
3. Coverage for papers: a targeted second search for named targets the paper says it could not find (P3's CLM paper), with Chris's decision on
   repeating retrieval.
4. Carried: an independent walkthrough (MOE-4), experiments in the app, Increment 7 (the auditor on external papers).

## Independent Evaluator

Rounds are added below, each by a fresh subagent that did not write this review, with every verdict kept unedited in
`.meridian/evaluator/incr6_review-verdict-r<N>.json`.

**Round 1** (warn, 7.0; completeness 6, quality 8, consistency 8, spec adherence 6.5): every headline figure it checked held (paper costs,
audits, counts, rubric cells and means, inference rates and the freeze order, the cited defect examples, tests, traceability, other docs). Gaps
raised: each feature's acceptance criteria not stated as met or not; inference rates not given per fault type, and one judge-layer fault caught
by the rules; an unsourced "7 to 8 of 59"; a word count that included the record sections (prose is 2,532 to 2,722, below the 3,000 target);
P1 over the SPEC's $0.75 per-paper cap; $0.13 missing from the $5 breakdown; `record.json` not holding the figures and no wall time; the
overhead check blocking now; the static showcase not mentioned; a stale docs/07 heading. Verdict kept in `incr6_review-verdict-r1.json`. After
it, each point was addressed in the text above (the acceptance table, the per-type rows, the scorer's recorded counts, prose words, the per-paper
cap row, the spend breakdown, two deviations, the overhead status, the showcase row, docs/07).

**Round 2** (warn, 7.5; completeness 8, quality 7.5, consistency 7, spec adherence 7.5): every round-1 gap addressed and its figures held.
Remaining: a false statement (wall time "recorded nowhere"; it is in `app_state.json`, the ledgers and the audit reports); counts from the
scorer's chat report that no file records; claims labelled "overstated" that the scorer's file lists as leaning on context; the CLM paper
described as named in P3's question (it was named in the emphasis); an unqualified "within their caps"; the source reviews not stated as
unscored. Verdict kept in `incr6_review-verdict-r2.json`. After it, each was corrected in the text above (wall times reported; only the
file's counts and labels; the emphasis; the qualified exit row; the paragraph on unscored reviews).

**Round 3** (pass, 8.0; completeness 8.5, quality 8, consistency 7.5, spec adherence 8): round-2 points fixed and checked; no blocking gap.
Verdict kept in `incr6_review-verdict-r3.json`.

## After the review (2026-10-12; not evaluated)

Corrections from round 3's non-blocking notes, made after its verdict: P1's repair-bug cost restated as about $0.21 to $0.25 (two repairs of
about 65,000 input tokens, $0.269 together, against about $0.03 for a normal repair), not "about $0.30"; the README's "about 3,300 words"
replaced by the prose count; the defects table now says the classification of P1 C28 and P3 C48 is the author's. Also noted: P1's three-hour
pause held 34 small judge calls at 18:21 to 18:22Z ($0.0004), the resume attempt made before the app was restarted with the new resume code,
which stopped again at the old cap (defect 2).

Overhead: the first entry (2026-10-12T20:24Z, 4 h) was recorded with a stray word, so its note began "hours 2026-10-11, ..." and the
dogfood check credited only 2026-10-12. A second entry for 2026-10-11 (2.5 h) was added; its note says it is a correction and that the
4 h of the first entry covered both days. **The log's raw sum (6.5 h) over-counts: the increment's overhead is 4 h.** The log is
append-only, so the first entry was left as written.

`incr6_review` passed on 2026-10-12 (approved by Chris): 753 tests, traceability (29 requirements), dogfood and the Evaluator (pass, 8.0).
