# SPEC — VERA, Increment 8 (a judge you can trust on the new questions)

> **Status: scoped 2026-10-14 (`incr8_scoped` approved by Chris).** Passed 2026-10-14: `judge_set_frozen`, `judge_measured`,
> `routing_ready`, `reaudit8`, `incr8_review` (approved by Chris; [docs/reviews/incr-8.md](docs/reviews/incr-8.md)). Increment 8 is complete. Decided along the way: the
> 45-item sample labelled by an OpenAI assistant (decision 4); no route met the bars, and Chris chose the decided path with the
> reference confirming an audit's no (decision 3); the re-audit cap raised to $0.50. The Increment 7 SPEC is in git history; its
> review is [docs/reviews/incr-7.md](docs/reviews/incr-7.md).

## Overview

Current-increment features only, in build order. Each `##` below becomes a tracked feature (`scripts/features-init.sh`);
do not add `###` headings. Source: [docs/07-increments.md](docs/07-increments.md) Increment 8; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.13 (no schema change is planned; if one is needed it goes into docs/03 first);
requirements due: JDG-F-07, JDG-P-04, AUD-F-13, plus everything due earlier ([docs/02-requirements.md](docs/02-requirements.md)).

**Why this increment.** Increment 7 checked every sentence with three new judge questions (`claim.within_quote`,
`sentence.no_fact`, and a clause-by-clause wording of `paper.inference_follows`). None was benchmarked against the reference
judge, as Increment 1's questions were (JDG-P-01). The two papers made with them were red on 2 and 3 items, and every failing
claim had passed the same question at write time: the cheap path sent one call to Jev and the other to GLM, and they
disagreed near the 0.7 threshold (docs/reviews/incr-7.md). The cause is in the routing: `cheap_path` sends `lit.` and `loop.` questions
to GLM alone, and everything else to Jev first, escalating to GLM below 0.7; the new questions carry no such prefix.
So today a red light can mean "one of two judges said no once". This increment measures the new questions against the
reference, routes each to one judge chosen by that measurement, and makes the audit say "the judges disagree" instead of
"failed" when its verdict contradicts the write-time verdict. (The review's next-SPEC candidate 1; candidates 2 to 4 are
listed under decision 5.)

**The goal is unchanged:** very good research on whatever topic is requested, checkable sentence by sentence. Success here is
**a red light that means what it says**: every judge question the green light rests on is measured against the reference
judge, with the result stated whatever it is, and a sentence fails only when the judge of record says no.

Who does what: Claude Code builds, runs the offline work and, with Chris's go-ahead on spend, the measurement; Chris approves
human gates himself (the agent reports readiness and never approves for him). Increment 7's human steps were done by an
OpenAI assistant at Chris's request; the SPEC names who does each step, and the review records who actually did.

Rules carried from the Increment 7 review:

- **Spend.** Every model call goes through a `Budget` that raises before a limit is crossed, inside the $20/month ceiling
  (ConOps §4). Proposed caps for Chris to confirm at `incr8_scoped`: **$0.50** for debugging and smoke runs; **$3** for the
  judge benchmark (the reference, Claude Sonnet 5.5, is the costly part: Increment 5's re-test cost $0.615 for 150 items);
  **$0.25** for re-auditing the five papers (raised to **$0.50** by Chris on 2026-10-14, once the reference's
  confirmation of each "no" was chosen: about 76 confirmations); **$5** for the increment. Increment 7 spent $1.33 of its $5.
- **Independence and freezing.** The Increment 5 audit freeze (`69890a43f1fc`) and Increment 6's inference hashes hold, and
  Increment 7's real-case freeze (`realcase_hash_incr7.json`) is not re-run: its test split was measured once. Question
  wording may change on a dev split only; the test split and the checks' source are hashed before the one test run.
- **No self-grading.** Producers are unchanged; every verdict on their text comes from the judge path; `StageResult` refuses a
  judge equal to the producer.
- **Attribution.** Every label, score and note is recorded under the name of whoever made it; a step done by an assistant says
  so in its file (as `labels_test.json` and `rubric7_first.json` now do).
- **Dogfood.** Overhead logged on each day a gate passes: `bash scripts/dogfood.sh overhead <hours> "<date>: <note>"` (hours
  first; no word between).
- **Outward-facing actions** need Chris: pushing a commit, publishing on the showcase.

Gate DAG proposed for `.meridian/gates.yaml` after `incr8_scoped` (only `incr8_scoped` is defined now):

```text
incr7_review ─► incr8_scoped ─► judge_set_frozen ─► judge_measured ─► routing_ready ─► reaudit8 ─► incr8_review
                (human)          (automated: set and   (automated: one     (automated: routes  (human: re-audit  (human +
                                  checks hashed before  test run, every     from the result,    the five papers,  Evaluator)
                                  any backend runs)     rate reported)      disagreement rule)  Chris's key)
```

## The judge set for the new questions (JDG-P-04)

`scripts/build_judge_set8.py`, `data/judge8/` (new).

- **Items are the questions as the pipeline asks them**, on real material from the five papers made so far (Increment 6's
  P1 to P3 in `data/paper_demo/`, Increment 7's N1 and N2 in `data/paper_rerun/`), each built with the same functions the
  pipeline uses (`sentence_checks.within_quote`, `sentence_checks.no_fact`, `sentence_checks.follows_strict`), so the
  material is exactly what a judge sees:
  - `claim.within_quote`: about **120** kept claims with their quotes, stratified by paper;
  - `sentence.no_fact`: about **80** claim-free evidence sentences (from the old papers, split as the audit splits them, and the
    new papers' transitions);
  - `paper.inference_follows` (the clause-by-clause wording): every kept interpretation statement and synthesis sentence with
    its premises, about **80**.
- **Split by paper**: dev is P1 and N1; test is P2, P3 and N2. The test items' SHA-256 and the source of the three question
  builders and the routing code are written to `data/results/judge8_hash.json` before any backend sees a test item.
- **Reference labels** are the reference judge's modal answer over two repeats, as in Increments 1 and 5. Where an item is
  also in Increment 7's real-case set, the reference's agreement with those labels is reported too, as a check on the
  reference itself.
- **Optional, decision 4: a person's labels** on a stratified 45 of the test items (15 per question), labelled blind to every
  backend's answer, so the reference is itself measured against a person.

**Acceptance:** `check_carry8.py --part set`: counts within the SPEC's ranges, the split by paper, the hash file written before
any test result, every item built by the pipeline's own question functions (a test rebuilds a sample and compares).
**Gate:** `judge_set_frozen`.

## Measuring the backends against the reference (JDG-P-04)

`scripts/measure_judge8.py` (new), using `vera.bench.harness` and `vera.bench.metrics` unchanged.

- **Backends, each on every item:** the reference (Claude Sonnet 5.5, 2 repeats); Jev alone, GLM alone and the decided path
  as configured today (3 repeats each). Dev may be run more than once (only to read behaviour or change wording); test once.
- **Reported per question, whatever it shows:** agreement with the reference (Wilson 95%), flip rate across repeats
  (JDG-P-03's measure), the share of verdicts below the 0.7 threshold, calibration (ECE), cost and latency per item; for the
  decided path, how often Jev and GLM disagree on the same item. If the person's labels exist, the reference's agreement with
  them.
- **The bar is JDG-P-01's** (97% agreement with the reference) **and JDG-P-03's** (flip rate at most 2%), stated now, before
  the first measurement; the result is reported against them, met or not.

**Acceptance:** `check_carry8.py --part measured`: the one test run came after the freeze, on the frozen set and code, and
reports every figure above for every question and backend; spend within the $3 cap, read from its ledger.
**Gate:** `judge_measured` (requires `judge_set_frozen`).

## One judge per question, and an audit that says when judges disagree (JDG-F-07, AUD-F-13)

`vera/judge/cheap_path.py`, `vera/audit/disagreement.py` (new), `vera/app/pipeline.py`, `vera/literature/paper_interpret.py`,
`vera/app/pdf.py`, `vera/app/static/`. `vera/audit/sentences.py` and `sentence_checks.py` are hashed for Increment 7's real-case
measurement and are not edited: the disagreement rule is applied to the sentence audit's findings in the pipeline.

- **A route per question (JDG-F-07).** `cheap_path` takes a routing table, `QUESTION_ROUTES`, mapping a question id to the
  backends that may answer it, in order (for example `claim.within_quote: ("glm",)`). Each of the three new questions is routed
  by the measurement: the cheapest route that meets both bars; if none does, the route that agrees best with the reference,
  and the review says the bar is not met. Questions not in the table keep today's routing. The route that answered is
  recorded on every verdict (`Verdict.backend`, as now), so a reader can see who judged.
- **The same judge at write time and in the audit.** Both ask through the same `cheap_path` and table, so a question has one
  route wherever it is asked.
- **Disagreement is not failure (AUD-F-13).** The audit compares its verdict on a sentence with the verdict stored on that
  sentence at write time (`SentenceRecord.verdicts`). When they disagree, the finding is a `warn`, "the judges disagree: passed
  at write time, failed in the audit", and the light is amber, not red; a sentence fails only when the audit's verdict is a
  confident no and the write-time verdict is not a confident yes (or there was none: documents made before 0.13). The
  interpretation stage stores its write-time verdicts on each `Inference` (today it stores none), so the same rule covers
  statements.
- **Reader and PDF** list judge disagreements apart from failures, and the light's wording says amber can mean the judges
  disagreed.

**Acceptance:** offline tests with fake backends: each routed question reaches only its route; an unrouted question keeps
today's path; a write-time yes and an audit no give a `warn`, not a `fail`; a write-time no (repaired) and an audit no give a
`fail`; an `Inference` keeps its verdicts; documents made before 0.13 are audited as now; headless test of the disagreement
list. `test_JDG_F_07_…` and `test_AUD_F_13_…` exist. Both freezes still hold.
**Gate:** `routing_ready` (requires `judge_measured`).

## The five papers re-audited (human)

Chris (or whoever he asks, named in the record) re-audits the five papers with the new routing and rule
(`scripts/reaudit8.py`, on temporary copies, as in Increment 7), with his key. Recorded in `data/reaudit8/`: each paper's light
and findings before (Increment 7's audit) and after, with failures, disagreements and the backends that answered.

**Acceptance:** `check_reaudit8.py`: five reports, each with the sentence check and the routing table's hash; spend within
$0.50 from the ledger (raised from $0.25); the record names who ran it.
**Gate:** `reaudit8` (human, requires `routing_ready`).

## Increment 8 review

`docs/reviews/incr-8.md`: what was built; each acceptance criterion met or not; spend against each cap; the measurement per
question and backend against the bars; the routes chosen and why; what the re-audits show (how many reds were disagreements);
the person's labels, if made; deviations; what the next increment takes. Plain about what was not shown.

**Acceptance:** `check_dogfood.py` finds an overhead entry for each day a gate passed; traceability passes; the independent
Evaluator passes the review.
**Gate:** `incr8_review` (human + Evaluator).

## Decisions for Chris at incr8_scoped

1. **Caps:** $0.50 debugging, $3 judge benchmark, $0.25 re-audits, $5 for the increment (above).
2. **Disagreement is amber, not red** (AUD-F-13). Recommended: a red light should mean the judge of record said no; a
   disagreement is worth a reader's look, not a failure. The alternative keeps today's rule (any confident no in the audit
   fails), which is stricter but makes the light depend on which judge answered.
3. **Routes are chosen by the measurement** under the stated bars, without coming back to you, unless no route meets them; then
   the agent reports the options and you choose.
4. **A person's labels on 45 test items** (about 45 minutes): optional, recommended. Without them the reference is the only
   yardstick, and the review says so. If you have an assistant do it, it is recorded under the assistant's name.
5. **Out of scope, for later increments:** closing the misses the Increment 7 scorer found (small claim-level additions,
   statements about the paper itself, more agreement wording); new papers; Increment 9 (the auditor on external papers,
   renumbered from 8; its requirement rows move with it).
6. **Freeze:** the plan changes no frozen file and no file hashed for Increment 6's inference measurement or Increment 7's
   real-case measurement. If building shows one must change, the agent stops and asks before changing it.
