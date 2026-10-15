# SPEC — VERA, Increment 10 (close-out)

> **Status: scoped 2026-10-15 (`incr10_scoped` approved by Chris, decisions 1-4 as proposed).** Passed 2026-10-15:
> `sticky_answer_ready`, `closeout_docs_ready`. `incr10_review` (approved by Chris; [docs/reviews/incr-10.md](docs/reviews/incr-10.md)), the last
> planned gate. Increment 10 is complete and the project is closed. The Increment 9 SPEC is in git history; its review is [docs/reviews/incr-9.md](docs/reviews/incr-9.md).

## Overview

Current-increment features only, in build order. Each `##` below becomes a tracked feature (`scripts/features-init.sh`);
do not add `###` headings. Source: [docs/07-increments.md](docs/07-increments.md) Increment 10; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.13 (unchanged); requirements due: no new ones (RSH-F-17's tests grow), plus
everything due earlier ([docs/02-requirements.md](docs/02-requirements.md)).

**Why this increment, and why it is the last planned one.** Increment 6 delivered what Chris asked for (a paper from a
finished review). Increments 7 to 9 each found the previous checks imperfect, added a layer, and ended with a new list: the
light became more honest ("unsettled", "judges disagree" instead of a false green or red), but an independent reader still
finds about the same share of claims that say more than their quotes, and the papers made in Increment 9 are not better by
the audit. Chris has asked to close the work out (2026-10-15). This increment fixes the one behaviour Increment 9's SPEC
promised and did not build, writes down what VERA is and what its light means as the project's final word, and stops.

**No new checks, no new judge questions, no new measurement.** Anything that would add one goes to the list of what is not
planned (decision 3), not into this increment.

Who does what: Claude Code builds and writes; Chris approves the human gates himself.

Rules carried from the Increment 9 review:

- **Spend.** **$0.50** cap for the increment (ConOps §4's $20/month ceiling holds): the fix is tested offline; at most one
  smoke audit of an existing paper with the real judges. Increment 9 spent $1.30 of $3.
- **Independence and freezing.** The Increment 5 audit freeze, Increment 6's inference hashes, Increment 7's real-case hashes
  hold; no measured set is re-run.
- **Attribution, dogfood, outward-facing actions** as before (overhead: `bash scripts/dogfood.sh overhead <hours> "<date>: <note>"`,
  hours first, no word between; pushing and publishing need Chris).

Gate DAG proposed for `.meridian/gates.yaml` after `incr10_scoped` (only `incr10_scoped` is defined now):

```text
incr9_review ─► incr10_scoped ─► sticky_answer_ready ─► closeout_docs_ready ─► incr10_review
                (human)           (automated: the audit    (automated: the light's   (human +
                                   keeps the write-time     meaning, the             Evaluator)
                                   reference answer)        retrospective, the
                                                            plan marked closed)
```

## The reference's write-time answer sticks in the audit (RSH-F-17, completed)

`vera/app/pipeline.py` (the audit's asker), `vera/audit/disagreement.py` if needed. `vera/audit/sentences.py` and
`sentence_checks.py` stay unedited (hashed for Increment 7).

- When the write step asked the reference about a sentence or statement and stored its verdict, and the text is the same
  in the audit, the audit uses that stored answer instead of asking the reference again: no second draw, no second cost.
- The stored answer is matched by question and by the item's own text (the claim sentence or the statement, which the judge's
  material quotes); an item whose text changed, or that has no stored reference verdict, is confirmed in the audit as now.
- Increment 9's symmetric rule then applies unchanged: a confident stored no fails, a confident stored yes is a disagreement
  if the audit's cheap judge says no, an unsure stored answer is unsettled.
- Shown on the two Increment 9 papers by re-reading their stored verdicts offline (no model call): N1's C41, unsure at write
  time (no at 0.62), would be unsettled, not failed; S60 would keep its write-time answer.

**Acceptance:** offline tests: a stored confident reference yes is reused and the reference is not called; a stored unsure
answer is reused and the item is unsettled; a changed text is confirmed afresh; no stored answer means Increment 9's
behaviour; the offline re-read of N1 and N2 recorded (`data/results/sticky10.json`). `test_RSH_F_17_…` grows. The freezes hold.
**Gate:** `sticky_answer_ready`.

## What VERA is, what its light means, and how the work closed

`README.md`, `docs/reviews/retrospective.md` (new), `docs/07-increments.md`.

- **The light, once and canonically** (README): what green, amber and red each mean today, item by item (citations, claims
  against quotes, synthesis and interpretation against their claims, transitions, the reference's confirmation, disagreements,
  unsettled items), and what no colour means (completeness, the reading being right, coverage). Every earlier wording that
  disagrees is pointed here.
- **A retrospective** (`docs/reviews/retrospective.md`, about two pages): what was built in Increments 0 to 10; what was
  measured and what it showed, with the figures that matter; what was never shown (no human-labelled measurement since
  Increment 6; papers not shown to improve after Increment 6; one run per paper); spend in all; what the Meridian process
  caught and what it cost; and why the work stopped where it did.
- **The plan marked closed** (`docs/07-increments.md`): Increment 10 as the last planned increment; the candidates left
  (asking the reference about every claim, multi-run measurement, a person's labels, the auditor on external papers) listed
  as **not planned**, each with the reason it was left and what would justify reopening it.

**Acceptance:** `check_carry10.py --part docs`: the README section names each colour and each item, the retrospective has
its sections and its figures trace to the review files, docs/07 marks the work closed and lists the not-planned items.
**Gate:** `closeout_docs_ready` (requires `sticky_answer_ready`).

## Increment 10 review

`docs/reviews/incr-10.md`: what was built; each acceptance criterion met or not; spend against the cap; deviations; and a
closing statement. Plain about what was not shown.

**Acceptance:** `check_dogfood.py` finds an overhead entry for each day a gate passed; traceability passes; the independent
Evaluator passes the review.
**Gate:** `incr10_review` (human + Evaluator).

## Decisions for Chris at incr10_scoped

1. **Cap:** $0.50 for the increment.
2. **Scope:** the sticky answer, the canonical light, the retrospective and the closed plan; nothing else.
3. **Not planned after this:** asking the reference about every claim; multi-run measurement; a person's labels or a vote of
   strong judges; the claim-level misses Increment 7's scorer found; the auditor on external papers (Increment 11 in the
   requirement rows, marked not planned). Reopening any of these is a new decision, not a next increment.
4. **After closing:** VERA is used on topics Chris cares about; if a limit bites in real use, that is the evidence for
   reopening one of the items in 3.
