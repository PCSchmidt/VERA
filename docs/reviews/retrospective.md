# VERA retrospective (Increments 0 to 10, 2026-09-29 to 2026-10-15)

Written 2026-10-15 by Claude Code at the close of the work, from the increment reviews in this folder. Every figure here is
from a review or a file it names. This is the project's last word on what VERA is and what it showed; the reviews hold the
detail.

## After the close

On 2026-10-15, after `incr10_review`, Chris asked for the showcase to link the finished papers. Three examples now carry the
review paper made from their review (the Increment 9 papers on recursive and Context Language Models and on prompting, and the
Increment 6 paper on agent traces), each with the light its own audit gave it and a note of the deficiencies found in it (the
red items, the offline re-reads, the independent scorer's notes). A presentation change only: no model call, no gate, no
change to any audit or frozen file.

## What was built

VERA (Verifiable, Economical Research Agents) is a local app and a command-line pipeline that take a topic to a checked
literature review, and on request to a review paper, on the user's own model key and within a cap the user sets.

| Increments | What they added |
| --- | --- |
| 0 | The data spike: the ScientistTwo corpus inventoried (86 generated papers), parent problems chosen, schemas v0.1 |
| 1 | The cheap judge (P2): a router that asks a cheap model first and escalates when unsure, benchmarked against a reference judge |
| 2 | A thin research loop on one parent problem (TreeHFD), ending in a minimal auditor (P1) |
| 3 | From a topic to a confirmed question and a literature review whose every claim is tied to a quote |
| 4 | Paper-quality write-ups, a second parent problem, the comparison with ScientistTwo |
| 5 | The local app with bring-your-own-key, live progress, stop and resume, a PDF; a static showcase |
| 6 | A review paper made from a finished review, with labelled, judged interpretation sections |
| 7 | Every sentence of an evidence section given a status (claim, synthesis, transition) and checked; the audit lists every sentence |
| 8 | The judge questions behind those checks measured against the reference; the audit confirms a cheap "no" with the reference |
| 9 | A failure needs a confident "no"; an unsure judge is "unsettled"; the writer asks the reference too |
| 10 | The reference's write-time answer sticks in the audit; this retrospective; the plan closed |

At the close: 836 tests (13 need Docker), schemas v0.13, requirements v0.11, 231 commits.

## What was measured

| Question | Answer | Where |
| --- | --- | --- |
| Can the judge be cheap? | Yes for the loop's decisions: about 1 to 2% of the reference judge's cost at matching decisions (Increment 1); 150 of 150 gate decisions agreed, mostly perturbed copies (Increment 5) | `incr-1.md`, `incr-5.md` |
| Does the audit catch planted faults? | 50 of 52 on a frozen-source test; 3 of 6 clean controls failed (two for real misstatements) | `incr-4.md` |
| Did the research loop beat a baseline? | No, on either parent problem | `incr-2.md`, `incr-4.md` |
| Versus ScientistTwo (MOE-3)? | Not met: the gain half fails, the cost half cannot be assessed | `incr-4.md` |
| Does retrieval find the key papers? | 59% of key papers before the screen, 64% with Semantic Scholar | `incr-5.md` |
| Is a green audit enough? | No, from Increment 5 on: independent readers kept finding claims that say more than their quotes in green reviews and papers | `incr-5.md`, `incr-6.md`, `incr-7.md` |
| Do the sentence checks catch real defects? | On 90 real items: the old checks flagged 0 of 21 faulty items, the new ones 15 (and 14 of 69 sound ones), against an AI assistant's labels | `incr-7.md` |
| Are the new judge questions reliable? | No backend meets the 97% agreement bar: the best route agrees with the reference on 89%, 95% and 89%; the reference is itself unsure on about a fifth of claim and statement verdicts | `incr-8.md` |
| Do papers get better with each layer? | Not shown. An independent reader found about the same share of overstated claims in Increment 6 and 7 papers; Increment 9's remade papers are not better by the audit (0 to 1 and 1 to 2 failures, one run each) | `incr-7.md`, `incr-9.md` |

## What was never shown

- **A new user completing a run (MOE-4).** The only walkthrough was by the builder.
- **A person's labels since Increment 6.** The Increment 7 and 8 reference labels and the Increment 7 first scores came from an
  OpenAI assistant at Chris's request; every measurement since rests on a model's judgement, stated as such in each review.
- **That the checks make the research better**, as opposed to the light more honest. Each layer from Increment 7 on changed
  what the light says; none was shown to reduce what a careful reader finds.
- **Run-to-run variance.** Every paper was made once; no change was measured against repeated runs.

## Spend

$16.05 of model spend over the 16 days, inside the $20 monthly ceiling set in Increment 0: every record in every ledger
file in the repository, counted once by its trace id (`scripts/spend_total.py`, `data/results/spend_total.json`; $15.78 in
`data/ledger/` and $0.28 from two runs whose ledgers exist only as copies, the app rehearsal and the new-user walkthrough).
The increment reviews' own totals sum to about $15.98; they were each read over a window of dates, so they differ by cents. The ledgers in
`data/ledger/` are mostly git-ignored, so this figure reproduces on the machine that ran the work, not from a fresh clone. The largest single
items were the Increment 1 judge benchmark, the Increment 4 runs and the Increment 8 reference-judge measurement ($1.99). A
literature review costs $0.11 to $0.21 and a review paper $0.53 to $0.77 in this project's runs.

## The process

VERA was built with Claude Code under the Meridian harness: gated increments, each with a SPEC Chris approved, automated gates
that re-run the tests and their checks, human gates only Chris approves, and an independent Evaluator that scores each review
before it can pass.

What it caught that would otherwise have shipped: a wrong headline in the Increment 9 review (the remade papers were called
better on an unfair comparison; the Evaluator failed it at 5.5); unsupported figures and missing costs in the Increments 6 to
8 reviews; the Increment 4 freeze break; a judge disagreement that made red lights mean less than they said (Increment 7).
Freezing test sets and code before their one measurement kept every result reproducible from its files.

What it cost: 32 hours of logged overhead over the 16 days (29.5 after one correction counted twice), several Evaluator rounds
per increment, and a habit of each review's "next SPEC" list generating the next increment.

## Why the work stopped here

Increment 6 delivered what was asked: a paper from a finished review. Increments 7 to 9 each found the previous checks
imperfect, added a layer, and ended with a new list. The light became more honest, but the papers did not demonstrably
improve, and the remaining candidates (asking the reference about every claim, multi-run measurement, a person's labels, a
stronger reference) are each open-ended. On 2026-10-15 Chris decided to close the work out. Increment 10 completed the one
behaviour Increment 9 had promised and not built, and stopped.

What would justify reopening: real use of VERA on topics that matter, showing that one of the limits above changes a
decision. The not-planned list, with the reason each item was left, is in [docs/07-increments.md](../07-increments.md).
