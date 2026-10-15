# SPEC — VERA, Increment 9 (an unsure judge is not a verdict)

> **Status: scoped 2026-10-15 (`incr9_scoped` approved by Chris, decisions 1-5 as proposed).** Passed 2026-10-15:
> `unsure_rule_ready`, `write_confirm_ready`, `papers9` (the papers made by Claude Code at Chris's request). `incr9_review` (approved by Chris;
> [docs/reviews/incr-9.md](docs/reviews/incr-9.md)). Increment 9 is complete. The Increment 8 SPEC is in git history; its review is
> [docs/reviews/incr-8.md](docs/reviews/incr-8.md).

## Overview

Current-increment features only, in build order. Each `##` below becomes a tracked feature (`scripts/features-init.sh`);
do not add `###` headings. Source: [docs/07-increments.md](docs/07-increments.md) Increment 9; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.13 (no schema change is planned; if one is needed it goes into docs/03 first);
requirements due: AUD-F-14, RSH-F-17, plus everything due earlier ([docs/02-requirements.md](docs/02-requirements.md)).

**Why this increment.** Increment 8 measured the sentence checks' judge questions against the reference judge (Claude Sonnet
5.5): no cheap route met the bars, so the audit now asks the reference to confirm a cheap "no" on claims and statements. Its
re-audits showed the rule is asymmetric (docs/reviews/incr-8.md): any reference no lets a failure stand, even an unsure one
(14 failures rest on a reference no below 0.7), while only a confident reference yes overrules (6 failures stand on a
reference yes below 0.7). And the reference is consulted only in the audit, so the writer never repairs what the reference
would reject: N2 went to its audit with three claims the cheap judges had passed at write time. This increment makes the
rule symmetric (a failure needs a confident no; anything unsure is a warning that says so) and moves the reference's
confirmation into the write step, so a sentence the reference rejects is repaired or removed before the audit, and one it
accepts is not removed on a cheap judge's no. (The review's next-SPEC candidate 1; candidates 2 to 4 under decision 5.)

**The goal is unchanged:** very good research on whatever topic is requested, checkable sentence by sentence. Success here
is **a red light that rests on a confident no**, and papers whose sentences have already met the judge the audit will use.

Who does what: Claude Code builds and runs the offline work, and with Chris's go-ahead the paid runs; Chris approves human
gates himself (the agent reports readiness and never approves for him). Each step's record names who did it.

Rules carried from the Increment 8 review:

- **Spend.** Every model call goes through a `Budget` that raises before a limit is crossed, inside the $20/month ceiling
  (ConOps §4). Proposed caps for Chris to confirm at `incr9_scoped`: **$0.50** for debugging and smoke runs; **$2** for the
  two papers made again (cap $1.00 each on the form; the write step's confirmations add an estimated $0.05 to $0.15 a paper);
  **$0.25** for their audits beyond what the papers' own caps cover; **$3** for the increment. Increment 8 spent $2.35 of $5.
- **Independence and freezing.** The Increment 5 audit freeze, Increment 6's inference hashes and Increment 7's real-case
  hashes hold (`vera/audit/sentences.py`, `sentence_checks.py` and the others they list are not edited). Increment 8's judge
  set is not re-run: its test split was measured once.
- **No self-grading.** Producers are unchanged; the reference judge confirms, it never writes.
- **Attribution.** Every label, score, note and run is recorded under whoever made it.
- **Dogfood.** Overhead logged on each day a gate passes: `bash scripts/dogfood.sh overhead <hours> "<date>: <note>"`
  (hours first, then the note; no word between).
- **Outward-facing actions** need Chris: pushing a commit, publishing on the showcase.

Gate DAG proposed for `.meridian/gates.yaml` after `incr9_scoped` (only `incr9_scoped` is defined now):

```text
incr8_review ─► incr9_scoped ─► unsure_rule_ready ─► write_confirm_ready ─► papers9 ─► incr9_review
                (human)          (automated: the rule,   (automated: the write   (human: two     (human +
                                  re-read offline on the  step confirms with the  papers made     Evaluator)
                                  five re-audits)         reference)              again, audited)
```

## An unsure judge is not a verdict (AUD-F-14)

`vera/audit/disagreement.py`, `vera/app/pipeline.py`, `scripts/reread9.py` (new).

- **The rule, both ways.** A sentence or statement fails only when the judge of record gives a **confident no**: the
  reference's confident no where the reference was asked; otherwise the cheap judge's confident no with no confident yes
  against it (at write time or from the reference). A reference answer below 0.7, either way, makes the finding a warning:
  "unsettled: the reference judge was unsure (no at 0.62)". A confident reference yes stays a disagreement (amber), as now.
- **No new spend to see its effect.** Every Increment 8 re-audit finding stores the cheap judge's and the reference's
  verdicts and confidences, so `scripts/reread9.py` applies the new rule to the five reports in `data/reaudit8/` without a
  model call and records, per paper, the light and the failures, disagreements and unsettled findings before and after
  (`data/results/reread9.json`).
- **Reader and PDF** list unsettled findings apart, beside disagreements; the amber wording names both.

**Acceptance:** offline tests: a confident reference no fails; a reference no or yes below 0.7 is unsettled (warn); a
confident reference yes is a disagreement; a cheap confident no with no reference asked and no write-time yes still fails; a
rule failure (no verdict) still fails; the re-read of the five reports is reproducible from the stored files and changes no
verdict, only severities. `test_AUD_F_14_…` exists. The earlier freezes hold.
**Gate:** `unsure_rule_ready`.

## The write step confirms with the reference (RSH-F-17)

`vera/literature/synthesis_stage.py` (`verify_sentences`, shared by the review and the paper), `vera/literature/paper_interpret.py`,
`vera/app/pipeline.py`.

- When a cheap judge gives a confident **no** on a question in `cheap_path.CONFIRM_NO` (`claim.within_quote`,
  `paper.inference_follows`) during writing, the reference is asked the same question on the same material.
  - Reference **confident yes**: the sentence or statement is kept without repair; both verdicts are stored on its record,
    so the audit sees that the reference already accepted it.
  - Reference **confident no**: it goes to repair as now, and a repair is re-checked the same way.
  - Reference **unsure**: kept, stored as unsettled (the audit will report it as such), not repaired on an unsure verdict.
- The audit, seeing a stored confident reference yes on the same question, does not fail the sentence on a cheap no (the
  reference is the judge of record for these questions); it asks the reference again only if the text changed.
- The reference is passed to the write step the way the cheap judge is (`deps.extra["reference"]`); with none (tests, or a
  user who opts out), the write step behaves as in Increment 8. Every reference call is on the run's ledger and budget.

**Acceptance:** offline tests with fake judges: a cheap no that the reference overrules is kept without a repair call; a cheap
no the reference confirms is repaired, then re-checked; an unsure reference keeps the sentence and records it as unsettled;
no reference given means Increment 8's behaviour; the review and the paper both use it; the producer never judges its own
text; the stored verdicts carry both judges. `test_RSH_F_17_…` exists. The earlier freezes hold.
**Gate:** `write_confirm_ready` (requires `unsure_rule_ready`).

## Two papers made again (human)

The two papers made with Increment 7's checks, made again from the same reviews and requests, cap $1.00 each, in the app with
Chris's key: N1 (`discuss-the-evolution-of-prompting-guv8`) and N2 (`rlm-vs-clm-2`). The Increment 7 papers are set aside
first (`scripts/set_aside_paper.py`, which keeps them). Recorded in `data/papers9/` with who made them and notes; spend,
lights, write-time confirmations and their outcomes, and the audit's failures, disagreements and unsettled findings computed
from the copied files.

**Acceptance:** `check_papers9.py`: two papers, each within its cap, each audited with the Increment 9 rule; the record names
who made them; the write-time confirmations counted from the stored verdicts.
**Gate:** `papers9` (human, requires `write_confirm_ready`).

## Increment 9 review

`docs/reviews/incr-9.md`: what was built; each acceptance criterion met or not; spend against each cap; the offline re-read of
the five re-audits; the two papers before (Increment 7, re-audited in Increment 8) and after, with the cost of the write-time
confirmations; deviations; what the next increment takes. Plain about what was not shown.

**Acceptance:** `check_dogfood.py` finds an overhead entry for each day a gate passed; traceability passes; the independent
Evaluator passes the review.
**Gate:** `incr9_review` (human + Evaluator).

## Decisions for Chris at incr9_scoped

1. **Caps:** $0.50 debugging, $2 papers (cap $1.00 each), $0.25 audits, $3 for the increment (above).
2. **The symmetric rule** (AUD-F-14): a failure needs a confident no; anything unsure is "unsettled" (amber). Recommended: a
   red light should rest on a confident judgement. The alternative keeps Increment 8's asymmetry.
3. **The reference in the write step** (RSH-F-17), on the two questions it already confirms in the audit. Recommended: it
   costs a few cents a paper and makes the writer meet the judge the audit uses. The alternative leaves the reference to the
   audit only.
4. **The papers are made by** Chris in the app, or by whoever he asks (named in the record).
5. **Out of scope, for later increments:** a better yardstick for claims and statements (a person's labels, or a vote of
   strong judges); the claim-level misses Increment 7's scorer found; Increment 10, the auditor on external papers
   (renumbered from 9; its requirement rows move with it).
