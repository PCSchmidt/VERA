# Increment 5 review: the app (UI/UX and bring-your-own-key)

Date: 2026-10-09 · Reviewer: Chris (decisions and human gates) · Author: Claude Code
Gates passed: `incr5_scoped`, `t8_decided` (Chris, through the engine), `carry5_ready`, `app_core_ready`, `key_safety_ready`, `ui_ready`
(automated), `newuser_walkthrough` (Chris, through the engine, recorded as not independent of the builder), `rubric5_scored` and `incr5_review`
(Chris, through the engine, 2026-10-09). This review is the evidence for `incr5_review`.

## Outcome

A local web app now takes a topic to an audited, downloadable literature review on the user's own model key, and it ran end to end on real
topics. It has **not** been shown to work for a person other than its builder, and its output is a literature review only: experiments are not
started from the app. In order of how much each statement should be trusted:

1. **The app works end to end, and the first live runs found real defects that tests had not.** A clean clone of the pushed repository followed
   the README to a finished run (a rehearsal: 7.5 minutes, $0.135, green audit). Two defects came from live runs on Chris's own topics: the
   scoping check rejected a question and the app then dead-ended with no way to edit it (fixed: the question can now be edited and confirmed), and
   a garbled year from the PDF parser (`"Apri"`) crashed the snowball step (fixed; resume restarted from the checkpoint without repeating paid work).
2. **Bring-your-own-key is enforced and tested.** The key is held in server memory, validated by one OpenRouter call, passed to the worker through
   its environment, and appears in no file, status, error message or process argument in an adversarial test in which the provider echoes the key
   back in its error (a mocked provider transport, not a live one), and a second test removes the redaction and shows the same run then puts the key in the log (so the first test is not vacuous). What this does not cover is listed under "Key safety". The server answers only on this computer and refuses cross-origin requests.
3. **The walkthrough was done by the builder, so it does not show MOE-4.** It was a fresh clone at commit 29b7836 with a finished run in 10.8
   minutes for $0.141 of a $1.50 cap, a green audit, and the user's own key. Chris said he cannot tell from one run whether he would keep using it,
   that the interface is "not really user friendly nor attractive", and that he wants a "highly polished, uber professional, academic look", a
   more detailed review that offers possible conclusions where the question allows, and a downloadable PDF. Two of the five confusions logged in the record were
   said by Chris (the interface; the review's detail and PDF); three were noted by the observer (the run name, the `uv` warning, the unsupported sentence) and were not raised by him.
4. **Two of those requests were built the same day:** a redesign (serif reading face, restrained accent, a landing page that explains the four steps,
   a run timeline with a spend meter, a reader with an evidence panel and one reference per line) and a PDF of any review or paper with its
   tables, figures, audit and a claims-and-quotes appendix. Neither has been seen by anyone but the builder; the redesign has screenshots and 15
   page tests, not a user's reaction. The request for conclusions is **not built**: it changes what the audit guarantees (below).
5. **The carry-ins measured what they said, with limits.** The judge agreed with the Sonnet reference on 150 of 150 decisions (97.5-100%), but
   only 14 are real new decisions and 136 are perturbed copies of earlier result tables, so this shows the judge is not near-tie fragile, not that it
   is accurate on hard real cases. A second keyed source (Semantic Scholar) raised pooled key-paper recall from 59% to 64% (+3 of 58) before the
   screen. A near-zero-spread rule now stops an idea whose results do not vary across seeds.
6. **The outputs are useful drafts, not reliable ones, and a green audit misses real defects.** Chris scored the three reviews 3 to 5 on every criterion; the independent scorer scored them 2 to 4 (mean 2.93
   against his 4.27) and found an overstated claim that passed the audit, an uncited generalisation, and an inaccuracy about a source ("Rubric scores"). Coverage is the weakest criterion on both scorers' sheets.

## Exit criteria (docs/07, SPEC)

| Criterion | Status |
|---|---|
| A new user completes S4 through the app with their own key (MOE-4) | **Not shown.** The one walkthrough was the builder, from a clean clone with a pre-placed `.env`; the check records `independent_of_builder: false`. A person who did not build it has not used it. |
| Landing page that explains bring-your-own-key and typical costs in plain words | Met; figures are read from the example runs' ledgers by code, with a test that the page contains none of its own |
| Connect a key; start a run from a topic with guidance and budget | Met (key check against OpenRouter; length and cap on the form) |
| Watch progress, stage verdicts and spend live | Met (stage timeline, latest check, spend meter from the ledger) |
| Read the paper with evidence links | Met for reviews (dotted sentences open their quote, source numbers open the paper, table numbers a results cell); not exercised by anyone but the builder |
| Stop or resume a run | Met and tested offline with a fake pipeline and live (resume after a crash) |
| No maintainer key in any shipped artifact | Met (repository scan, adversarial leak test, `.env` untracked) |
| Attractive, functional interface (docs/07) | **Not demonstrated.** The first version was called unattractive by its builder-user; a redesign followed the same day and has had no outside look |
| Experiments from the app | **Not met.** The form's checkbox is disabled with a reason; experiments run from the command line |

## What was built

`vera/app/` (server, run manager, worker, pipeline phases, key store, stop-aware budget, PDF writer, facts), `vera/app/static/` (the pages), schemas 0.11
(`SourceRecord.source` gains `semanticscholar`; `RunRequest`, `RunStatus`, `AppConfig`), `tools/checks/check_app.py`, `check_carry5.py`, `check_t8.py`,
`check_newuser.py`, `check_rubric5.py`, ten new test files (`test_app_core`, `_facts`, `_schemas`, `_secrets`, `_server`, `_ui`, `test_cheap_path_byok`, `test_check_newuser`, `test_check_rubric5`, `test_loop_spread`) and additions to five existing ones. Behaviour changes outside the app: the judge path falls back to GLM
alone when no Jev key is set (a bring-your-own-key user usually has only an OpenRouter key); a sentence with no claim that names a source in
running text is removed before the audit (below); a rejected scoping question can be edited and confirmed; an unreadable reference year no longer crashes
the snowball step. The two process calls the app makes moved under `vera/sandbox/` to satisfy FND-F-03.

## Carry-ins from the Increment 4 review

| Carry-in | Result |
|---|---|
| Judge on a larger labelled set (T1 reverse-if (1)) | 150 items (14 real, 136 perturbed), decided path versus the Sonnet reference **150/150 (97.5-100%)**, reverse-if not fired; both paths agree with the labels on every item. **Easy by construction**, so it does not test hard real cases. Cost $0.615. |
| Second keyed source (T5 reverse-if (5)) | Pooled recall before the screen 34 to 37 of 58 (59% to 64%); +1 on research-agents-eval, credal-dro and llm-judge-numbers, 0 elsewhere. The screen was not re-run, so the kept-by-screen figure is unchanged. A modest gain, reported as such. |
| Degenerate-spread rule | Built, tested with a planted near-zero spread and in the loop (a flat idea is sent back with the reason, and dropped if it stays flat). It has not run on a real loop run since. |
| Method-code check scoped to the idea | **Decided against (Chris):** left as a lead for a person, shown collapsed outside the traffic light; scoping it and a seeded set v4 deferred to Increment 6. |
| T9 reverse-if (2) reasoning control | **Dropped (Chris):** a Sonnet run costs about $0.10, so a cheaper model saves cents. A standing "model economics" item replaces it. |
| Retrieval beyond keyword queries | The second source is the only step taken; recall remains the weakest measured stage. |
| Per-session overhead | Logged for 2026-10-07 and 2026-10-09 (3 hours, as Chris reported, in one entry crediting both days); not logged day by day. |
| Chris's own labels of the novelty ideas; credal ideas that run | Not done; carried to Increment 6. |

## Live runs and the defects they found

`docs/results/app_live_run_1.md` (the RLM versus CLM topic: two attempts, a scoping dead end, a snowball crash, then a finished review at
$0.185 with a green audit; three of its claims checked by hand against the CLM paper and all three hold). `docs/results/walkthrough_preflight.md`
(the clean-clone rehearsal). The walkthrough record is `data/walkthrough/record.json`.

**A defect in a finished, green-audited review (the walkthrough's own).** One sentence reads "The two studies thus differ on trajectory length as a
failure signal, although R4 examined three agents and R12 a much larger set." It has no citation and no quote, names R12, which is not in the reference list,
and the audit (green, 20 claims) did not catch it, because the audit only checks sentences that carry a claim. This is the known limit that a green audit
does not mean every clause is anchored. It was found by the observer reading the text, not by Chris. **Fixed in the review step, not in the frozen
audit:** a sentence with no claim that names a source in running text is now removed (test added); it was not re-run on that review, whose text is as it
was.

## T8 decided: what was decided and what it costs

**Decision (Chris, through `t8_decided`, on the entry in `docs/04-trade-studies.md`):** a **local app only**. A hosted demo is not built; a hosted part would be its own gate. Reverse-ifs as written: hosting cost per
visitor that can be bounded near zero and measured, or a local install that proves too hard for the intended users. Neither was tested: nothing was deployed.

**Measured costs, from the ledgers and the runs of this increment:**

| What | Measured |
|---|---|
| Model fees for a literature review through the app | $0.185 (RLM and CLM topic; its three attempts $0.197), $0.112 (first agent-traces), $0.135 (clean-clone rehearsal, `data/app/live/rehearsal-1/`), $0.141 (the walkthrough, on Chris's own key); the Increment 4 reviews were $0.16 to $0.21 |
| Wall time of a run | 7.5 minutes (rehearsal), 10.8 minutes (walkthrough); about 15 minutes for the RLM and CLM review including a crash and a resume |
| Install on a clean clone | `git clone` 2 s, `uv sync` 8 s, first start over 8 s (the README now says up to half a minute); Python 3.11 or later and `uv`; Docker and GROBID optional (without GROBID the app reads abstracts only and says so) |
| Hosting | **Not measured.** Nothing was deployed; the cost of running GROBID, fetching and the web process for visitors would be the maintainer's and is unknown |

## Key safety: what the tests cover and what they cannot

Tested (`tests/test_app_secrets.py`, `test_app_server.py`, `tools/checks/check_app.py`): the key appears in no file under a run's directory, ledger, log or cache, no status or error message, no PDF, and no process argument; the key is
redacted from error text; the server answers only for this computer's host names and refuses cross-origin POSTs; the pages load nothing from outside the machine and set a Content-Security-Policy; no tracked file holds a key-shaped
string; the leak test fails if the redaction is removed.

**Not covered, or covered only by design:**

- The key is in the server's memory, and in the worker's environment for the length of a run. Any program running as the same Windows user can read a process's environment or memory; swap and hibernation files may hold it.
- OpenRouter and the model provider receive the key because it is the credential; the paper-search services receive their own keys.
- Redaction replaces the exact string. A truncated or encoded form of a key in an error message would not be caught. The provider-echo test uses a mocked transport, not a live provider.
- The browser may offer the password box to a password manager (the box sets autocomplete off but cannot force it).
- A `.env` in the repository folder is read as a fallback (the user's own file); a key kept there is on disk by the user's choice, and the app then reports "found in your environment".
- Only this operating system was exercised; the sandbox tests for keys in container output are from earlier increments.

## What the walkthrough's confusions led to

| Confusion (who raised it) | What the app does about it now | Seen by a user since? |
|---|---|---|
| The interface is not friendly or attractive (Chris) | A redesign the same day (serif reading face, restrained accent, a landing page with the four steps, a run timeline and spend meter) | No. 15 page tests and screenshots; Chris has not said whether it answers his comment |
| More detail, possible conclusions, a PDF (Chris) | PDF built and tested; a **Length** setting (short, standard, detailed: 1,000, 1,500 or 2,500 words) on the form, whose effect on a real review was not tested; conclusions not built (they change the audit's guarantee) | No |
| Run name generated from the topic and cut mid-phrase (observer) | The run list and run screen show a shortened topic as the title; the id is still generated | No |
| `uv` warning about another project's environment (observer) | **Nothing.** The README does not mention it | No |
| An unsupported sentence naming R12 (observer) | A sentence with no claim that names a source in running text is now removed, with a test; not re-run on that review | No |

## Model economics (standing item)

T9's reverse-ifs restated: (1) price: a Sonnet 5.5 literature review cost $0.11 to $0.21 this increment, far below a few percent of the $20 ceiling: **not fired**; (2) the reasoning-control test was dropped by Chris; (3) not tested; (4) the judge
is GLM (or Jev then GLM) and the writer is Sonnet, so they do not coincide. **I did not re-read price lists or probe newer models this increment**, and the GLM-only arm's cost (about 25 times lower per loop run in Increment 2: $0.0019
against $0.049) is not re-measured. The app takes its model from a setting (`VERA_GENERATOR_MODEL`), so a cheaper or newer model can be tried without code changes.

## Where the app falls short (honest account)

- **No independent user.** MOE-4 is not shown; the walkthrough is the builder from a clean clone, with a `.env` placed in it and a key pasted, and a gap of
  about an hour between the folder's creation and the environment's whose cause was not asked.
- **Literature reviews only.** The experiment path (a parent paper's code in a sandbox) is not in the app. The loop's two papers from Increment 4 are shown as
  examples; they did not beat their baselines.
- **Reviews are abstract-heavy.** The walkthrough run read 6 papers in full text and 33 at the abstract only; a review is limited by what the search found, and
  retrieval recall is 64% on the measured topics before the screen.
- **No conclusions section.** The request for possible conclusions is a real product gap and a real risk: unmarked conclusions would break the promise that
  every claim has a quote. The recommendation (a labelled "Synthesis" section marked as the author's reading, not audited against quotes) awaits Chris's decision.
- **Run names and the uv warning.** Run ids are generated from the topic and cut mid-phrase (the redesign uses a short title in their place); a `uv` warning appears
  whenever another project's virtual environment is active. Both were noted by the observer, not raised by the user.
- **First start is slow** (over 8 seconds on a clean clone): the README now says so.

## Rubric scores (both scorers)

Three outputs, all literature reviews produced through the app: **W1** (the walkthrough's agentic-traces review), **R1** (the RLM and CLM review) and **R2** (the first agent-traces
review, run from the development folder; not the clean-clone rehearsal, which was a different run on conformal prediction and was not scored). Scores are answers the question / coverage / correctness / reproducibility / honesty, 1 to 5 (`docs/results/rubric_sheet_5.md`). Chris scored first and blind, in
his own terminal; the independent scorer is a fresh Claude agent given the same sheet and files, told not to open Chris's file, which ran afterwards.

| Output | Chris (blind) | Independent scorer |
|---|---|---|
| W1 | 3 4 4 4 5 | 3 2 3 3 4 |
| R1 | 4 4 4 4 5 | 3 2 3 2 3 |
| R2 | 5 4 5 4 5 | 2 2 4 4 4 |

**Agreement is low and the gap is one-directional.** 2 of the 15 cells are equal; Chris's score is at or above the independent scorer's in every cell (mean 4.27 against 2.93, a gap of about 1.3
points per cell). The largest gaps are on **coverage** (Chris 4, 4, 4 against 2, 2, 2) and on whether R2 answers its question (5 against 2). This increment does not decide which scorer is nearer the truth:
the independent scorer is the same model family as the writer, and Chris's read is of documents he has also worked on. What the two agree on is that none of the three is a 5 on coverage, and that all three
are honest about their limits (4 to 5).

**Against Increment 4** (means over the outputs scored; the criteria are answers the question / coverage / correctness / reproducibility / honesty):

| Set | Chris | Independent scorer |
|---|---|---|
| Increment 4 reviews (L1 to L6, n = 6) | 3.67 / 2.50 / 3.83 / 4.00 / 5.00, overall 3.80 | 2.50 / 2.50 / 3.83 / 3.83 / 3.83, overall 3.30 |
| Increment 4 papers (P1, P2, n = 2) | 3.50 / 2.50 / 2.00 / 5.00 / 5.00, overall 3.60 | 2.50 / 2.50 / 4.00 / 3.50 / 4.50, overall 3.40 |
| Increment 5 reviews (W1, R1, R2, n = 3) | 4.00 / 4.00 / 4.33 / 4.00 / 5.00, overall 4.27 | 2.67 / 2.00 / 3.33 / 3.00 / 3.67, overall 2.93 |

Chris's overall mean on reviews rose from 3.80 to 4.27 and his coverage mean from 2.5 to 4.0; the independent scorer's fell from 3.30 to 2.93 and its coverage mean from 2.5 to 2.0. **The sets are not comparable** (different topics, three reviews against six,
different retrieval, and in Increment 4 the scoring sheet pointed the scorer to each topic's key-paper list and recall table, while these three topics have no key list; the Increment 4 human scores also carried the provenance caveat recorded in `incr-4.md`). The two scorers moving in opposite directions is itself the finding: this increment gives no
evidence that review quality improved. Dropping W1, whose final note is the example text, Chris's mean on R1 and R2 is 4.4 against the independent scorer's 2.9.

**The independent scorer's specific findings, each from reading claims against quotes (model output; I verified the Tracezip claim, the uncited sentence, the pipeline wording and the two CLM-paper points against the files and the paper's text; the rest are the scorer's reading):**

- **An overstated claim passed a green audit.** W1 says "The Tracezip authors say sampling forces a trade-off between completeness of tracing and system overhead"; the quote in `claims.jsonl` says only "existing work
  faces a trade-off between the completeness of tracing and system overhead". Sampling is not in it. This is the known weak class (`overstated_claim`, 1 of 2 on the Increment 4 test set).
- **R1 ends with an uncited generalisation and pipeline wording.** "RLM reports comparable cost on long-context tasks" has no citation, and the review says "the supplied abstract" and "the evidence supplied", which leaks how the
  pipeline works into the text.
- **R1 has an inaccuracy about the CLM paper.** It says the CLM metric is prefix-reuse FLOPs "not wall-clock latency", but the paper also reports a "65% greater end-to-end speedup at the same compute" on a 24-hour six-repository task; the review also
  omits the 35% server-side compute reduction from Suffix Cache Reuse at matched performance. Both are in the PDF's abstract and introduction (I checked the text).
- **R2 answers part of the question** (Claude Code's storage is described, SWE-agent and OpenHands get one line each, Aider and Codex CLI are not covered, the vector-database part rests on one source) and leaves out an
  OpenHands qualifier (the quote says the event-sourcing overhead is negligible). It says these gaps exist, which is why its honesty score is 4.
- **W1 uses 10 claims from 39 kept papers** and never uses two retrieved sources the scorer judged central (OpenTelemetry's GenAI conventions, SWE-agent).
- **A gap in my committed evidence.** R1's `retrieved.jsonl` was not committed with its other files, so the scorer could not inspect its 120 candidates and gave reproducibility 2 partly for that; I added the file after the scorer had run
  and did not change its scores. R1's reproducibility score is lower than it would be with the file.
- Explained: the audit's "claims checked" counts the cited claims plus the reference entries (W1: 10 + 10 = 20; R1: 13 + 9 = 22; R2: 11 + 9 = 20; counts from `claims.jsonl` and each review's reference list).

**Provenance of Chris's scores.** Five entries are on file in `data/results/rubric5_chris.json`: W1 `1 2 3 4 5` (the format example), then `3 4 4 4 5`; R1 `3 4 4 4 5` (identical to W1's, with the same note), then `4 4 4 4 5`; R2 `5 4 5 4 5`.
The entries that count are the latest per output. Their notes: W1's reads "clear on limits; coverage thin; one unsupported sentence", which is the text of the example command I gave (it says coverage is thin while coverage is scored 4; the unsupported sentence is a
real one in that review); R1's "Answers the questions"; R2's "Answers the questions accurately". All five entries were blind-stamped before the independent file existed. I do not know whether a language model helped with the numbers or notes beyond that.

## Judge and review checks; spend; overhead; same-model overlap

- **Spend, maintainer's key.** By the ledgers written since Increment 4 closed: the judge re-test $0.615; the app's live runs $0.309 (the RLM and CLM topic's three
  attempts $0.197, the first agent-traces run $0.112); the clean-clone rehearsal $0.135 (its ledger and review are in `data/app/live/rehearsal-1/`). About **$1.06** (ledgers: `data/ledger/` for the judge re-test and live runs, `data/app/live/rehearsal-1/ledger.jsonl` for the rehearsal) against
  the $5 cap and its sub-caps ($1 debugging, $3 end-to-end, $1.50 judge and second-source): the judge re-test is inside its $1.50. The Semantic Scholar queries cost nothing.
  The walkthrough run's $0.141 was spent on Chris's own key and is not counted. The independent scorer's work is a subagent and has no ledger of its own.
- **Overhead.** Chris reported 3 hours for 2026-10-07 and 2026-10-09 together; one entry (recorded 2026-10-09) credits both days by the named-day rule from Increment 4,
  and the check passes. No entry was made on 2026-10-07 itself, the same lapse as Increments 3 and 4.
- **Same-model overlap.** The writer is Sonnet 5.5; the cheap judge path is GLM (or Jev then GLM with a Jev key); the independent scorer is a Claude model, the same family as the
  writer; Chris's blind scores are his own except as noted below. The audit's judge is never the producer of the text it judges.
- **Test suite.** 689 tests passed in a full run made after the Evaluator's round 2, with its output captured unedited in `docs/results/incr5_test_run.txt` (an earlier full run, before the leak test's counterpart was added, passed 688). The suite takes 2 to 4 minutes. One gate run failed at its test hook for a reason not found (the suite passed on every later run), and the
  `ui_ready` gate failed once on three browser-test timeouts, fixed with a fresh browser profile per load and one retry.

## Deviations

- **The freeze check caught my own change.** A formatter run over `vera/` reformatted seven audit files and six others (formatting only); `check_carry5.py` refused because the audit
  files' hash had changed since scoping. I reverted those files to their state at scoping. The check did its job; the change was mine and unnecessary.
- **The audit freeze from Increment 4 is still broken**, by design: `check_seeded_v3.py` and `check_novelty_gold.py` block at HEAD. This increment changed no frozen audit file.
- **Human scoring provenance.** The rubric entries were re-recorded after format-example entries: W1 was recorded twice (the first entry was the format example `1 2 3 4 5`), R1 twice (the first repeated W1's
  numbers and example note word for word). The latest entry counts; all earlier ones stay on file in `data/results/rubric5_chris.json`. The W1 and R1 notes of the entries
  that count are described below.
- **Rubric outputs.** The SPEC named the walkthrough's paper and two more produced through the app, one empirical and one not. The app cannot run experiments, so there is no empirical
  output; the three scored outputs are all literature reviews (the walkthrough's, the RLM and CLM review, and the first agent-traces review).
- **The walkthrough setup.** Chris placed a `.env` in the clone and also pasted a key; an earlier attempt was started from the development folder and does not count.
- **A pre-flight and a rehearsal** were run by me on Chris's TEST key before the walkthrough; they are separate from it and are not evidence for MOE-4.

## Next SPEC (Increment 6, or a decision to stop)

Candidates, in my order: (1) a walkthrough by a person who did not build it (the one gap in MOE-4), with a key and credit from Chris; (2) the labelled Synthesis section and its
audit rule, if Chris wants it; (3) experiments from the app for the two problems that have harnesses; (4) Increment 6 as planned (the auditor on external papers), which would also rebuild the
seeded set the method-code scoping needs; (5) the judge on harder real decisions, now that real gate decisions are mostly rule verdicts and the judge is the shadow.

## Independent Evaluator

Rounds are added below, each by a fresh subagent that did not write this review, with every verdict kept unedited in `.meridian/evaluator/incr5_review-verdict-r<N>.json`.

**Round 1** (fail, 6.0; completeness 4, quality 7, consistency 8, spec adherence 5): two blockers, the T8 decision and its measured costs were missing, and the comparison of both scorers with Increment 4's scores was missing. Also raised: no
statement of what the key-safety tests cannot cover; the walkthrough's confusions not mapped one by one to what the app does; model economics as a one-line carry-in; a test count not backed by a record (688 against about 493 test
functions); the unexplained difference between "claims checked" and the number of saved claims; a rehearsal ledger not in the repository; two of the scorer's CLM-paper findings presented as verified when they were not; scores that repeated
an example counted without comment; and three of five confusions being the observer's, not the user's. Everything it verified held (spend, the judge and recall figures, the rubric cells and means, the walkthrough record, the gates, the unchanged
audit files, the fixes' tests). Verdict kept in `incr5_review-verdict-r1.json`. After it, each point was addressed in the text above or backed by a file (the T8 section, the Increment 4 comparison, the key-safety limits, the confusions table,
model economics, the claim-count explanation, `docs/results/incr5_test_run.txt`, `data/app/live/rehearsal-1/`, and a test that removes the redaction and shows the leak).

**Round 2** (pass, 7.8; completeness 8, quality 8, consistency 7, spec adherence 8): no blockers; every round 1 blocker resolved (the T8 decision and costs, the Increment 4 comparison) and the rest resolved or partly resolved. It verified the
ledger sums and the $1.06 total, the rubric means and the new comparison table, the claim-count reconciliation, 689 tests collected, the new leak-test counterpart, the unchanged audit files, and the gates. Remaining points (none blocking), fixed in the
text after the round: the word "rehearsal" named two different runs (R2 is the development-folder run, the rehearsal is a separate unscored run); a stale sentence said the rehearsal ledger was not in the repository; the test record was a summary
with an old commit (it is now the captured output of a full run); the Increment 4 provenance claim could not be found in its sheet (the sentence now says only what the sheet shows); and "tested" for key safety did not say "mocked" until later (now
in the same sentence). Verdict: `incr5_review-verdict-r2.json` and the standing `incr5_review-verdict.json`.

## After the review (2026-10-09; not evaluated)

Work done after the Evaluator's round 2 and Chris's approval, recorded here so the approved text is not edited: a static, read-only **GitHub Pages showcase** (`scripts/build_pages.py`,
`.github/workflows/pages.yml`, https://pcschmidt.github.io/VERA/) with seven examples, three of them reviews Chris chose (his RLM and CLM review and two agent-traces reviews) shown with their known
issues, and a note in T8 that it is a static showcase and not the hosted demo T8 rejected; a rewrite of `README.md` in the style of the author's other project READMEs; and an alignment pass over the
other documents (the dogfood log, the data dictionary, the risk register with three new risks, the verification plan's "as built" section, requirements APP-F-03 and APP-C-03, the T1, T5 and T9 notes,
the concept of operations, the contract and SPEC status, and the regenerated `MERIDIAN.md`).
