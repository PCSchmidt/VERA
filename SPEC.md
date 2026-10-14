# SPEC — VERA, Increment 7 (check what the green light does not)

> **Status: scoped 2026-10-13 (`incr7_scoped` approved by Chris, decisions 1-6 as proposed).** Passed 2026-10-13:
> `sentence_checks_ready`, `realcase_labelled`, `audit_sentences_ready`, `checks_measured`, `coverage_search_ready`, `paper_rerun`,
> `rubric7_scored`; 2026-10-14: `incr7_review` (approved by Chris; [docs/reviews/incr-7.md](docs/reviews/incr-7.md), which lists the
> deviations: the labels and first scores are an OpenAI assistant's, not Chris's). Increment 7 is complete. The Increment 6 SPEC is in git history; its review is
> [docs/reviews/incr-6.md](docs/reviews/incr-6.md).

## Overview

Current-increment features only, in build order. Each `##` below becomes a tracked feature (`scripts/features-init.sh`);
do not add `###` headings. Source: [docs/07-increments.md](docs/07-increments.md) Increment 7; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.12, with v0.13 (proposed below, written into docs/03 before any code uses
it); requirements due: RSH-F-15, RSH-F-16, AUD-F-12, plus everything due earlier
([docs/02-requirements.md](docs/02-requirements.md)).

**Why this increment.** Increment 6's three papers all audited green, and the external review (ChatGPT, of P1) and the
independent scorer (all three, every claim read against its quote) still found, in text the checks had passed:

- **cited claims that say more than their quotes** (P2 C25 and C31, "a structured form of context engineering", which carries
  P2's abstract; P1 C28 adds "GPT-3.5-turbo"); the scorer's file names 4, 6 and 3 such claims or claims leaning on context;
- **wrong uncited synthesis sentences** (P1 "The two studies therefore disagree", both premises one source; P3 "no passage
  covers recursive language models on cost", contradicted by C5 and C15). 23 to 33 claim-free sentences per paper are checked
  only for naming a source, and the audit does not list them at all;
- **a source named without a claim** ("by Shao and colleagues"), which the name rule does not know;
- **quotes that depend on context outside them** (P1 C41, "However, this patch may be overfitting.");
- **interpretation that overreaches**, which a check measured at 48 of 48 on faults its own author wrote did not catch;
- **repeated quotes read as corroboration** (3, 10 and 14 claims per paper reuse a quote already used);
- **a coverage gap not flagged**: P3 never retrieved the Context Language Models paper Chris named in its emphasis.

The first is the defect class VERA's main promise is about. So this increment adds no new kind of document. It makes the green
light cover every sentence, and it measures the checks on **real** defects labelled by Chris, not on faults the checks' author
wrote. (This was the review's next-SPEC candidate 1, with candidates 2 and 3 folded in; Chris agreed 2026-10-12.)

**The goal is unchanged:** very good research on whatever topic is requested, checkable sentence by sentence. Success here is a
measured improvement on real defects **without a weaker green**: every sentence of an evidence section has a status, and a
status of "checked" means a component other than the writer checked it.

Who does what: Claude Code builds and runs short work with offline fakes; Chris approves human gates himself (the agent reports
readiness and never approves for him), labels the test cases, makes the papers in the app with his own key, and scores blind.

Rules carried from the Increment 6 review:

- **Spend.** Every model call goes through a `Budget` that raises before a limit is crossed, inside the $20/month ceiling
  (ConOps §4). Proposed caps for Chris to confirm at `incr7_scoped`: **$1** for debugging and smoke runs; **$1** for measuring
  the checks on the real-case set (dev and test); **$0.50** for re-auditing the three Increment 6 papers; **$2** for the two
  papers made in the app (cap $1.00 each on the form); **$5** for the increment. Increment 6 spent $2.32 of its $5.
- **One ledger file per run**, never deleted, truncated or overwritten; papers append to their run's ledger.
- **Independence and freezing.** The frozen files (`data/results/audit_hash_incr5.json`, hash `69890a43f1fc`) are **imported,
  not edited**. Every change in this plan is in unfrozen code: `vera/literature/synthesis_stage.py`, `anchoring.py`,
  the paper modules, `retrieval.py`, `vera/audit/inference.py`, and new modules. `tools/checks/check_carry7.py` blocks a changed
  frozen file.
- **No self-grading.** Producers stay `p3.synthesize`, `p3.paper.write`, `p3.paper.interpret`; every verdict on their text comes
  from the cheap judge path; `StageResult` refuses a judge equal to the producer.
- **Measured sets are frozen before they are measured** and reported whatever the result; no target is set before the first
  measurement. Wording of a judge question may change on the dev split only.
- **Human scoring is blind and attributed**; Chris scores before the independent scorer runs.
- **Dogfood.** Overhead logged at the end of every session; **the note must start with the date** (`2026-10-13: ...`), and
  `dogfood.sh overhead` takes the hours first, then the note: `bash scripts/dogfood.sh overhead 2 "2026-10-13: ..."`.
- **Outward-facing actions** need Chris: pushing a commit, publishing a paper on the showcase.

Gate DAG proposed for `.meridian/gates.yaml` after `incr7_scoped` (only `incr7_scoped` is defined now):

```text
incr6_review ─► incr7_scoped ─┬─► sentence_checks_ready ─► audit_sentences_ready ───────────────┐
                (human)       │   (automated)               (automated: audit, reader, PDF)     │
                              ├─► realcase_labelled ─► checks_measured ────────────────────────┤
                              │   (human: Chris        (automated: set and check source hashed  │
                              │    labels the test     before the one test run; requires        │
                              │    split)              sentence_checks_ready)                    │
                              └─► coverage_search_ready ───────────────────────────────────────┤
                                  (automated)                                                   │
   ┌────────────────────────────────────────────────────────────────────────────────────────────┘
   └─► paper_rerun ─► rubric7_scored ─► incr7_review
       (human: app,    (human, blind)    (human + Evaluator)
        own key)
```

## Schemas 0.13 (docs/03 first)

`vera/schemas/`, `docs/03-interfaces.md`. Written into docs/03 with a version bump and a changelog line **before** any code
uses them; `vera/schemas/version.py` follows (`gate-schema-version.sh`).

```python
class SentenceRecord(BaseModel):
    id: str  # "S1", "S2", ... in reading order across the document's evidence sections
    section: str  # heading of the section it is in
    text: str
    kind: Literal["claim", "synthesis", "transition"]
    # claim: carries one or more verified claims; synthesis: relates claims (compares, generalises, counts, contrasts) and
    # names them as premises; transition: no factual content (it introduces, orders or signposts)
    claims: list[str] = []  # claim ids the sentence carries (kind "claim")
    premises: list[str] = []  # claim ids a synthesis rests on; at least one, each existing
    verdicts: list[Verdict] = []  # from a component other than the producer
    status: Literal["pass", "removed"]
    reason: str | None = None  # for a removal: the rule or judge question that removed it


# LiteratureSection and PaperDocument each gain:
sentences: list[SentenceRecord] = []  # every sentence of every evidence section; documents made before 0.13 load with []
```

`Finding.check` gains `"sentence"`. `evidence_stats` gains `distinct_quotes` and `claim_sources` (no schema change; it is a
`dict[str, int]`). A document whose sentence names a premise that does not exist, or whose synthesis has no premise, raises.
Review claims get ids (`C1…`) as paper claims already do, so a review's synthesis sentences can name them.

**Acceptance:** round-trip tests, a test that each raising rule raises, old documents (Increment 6's papers, committed reviews)
still load, and `check_schema_version.py` passes at 0.13.

## Every sentence has a status (RSH-F-15)

`vera/literature/synthesis_stage.py` (`verify_sentences`, shared by the review and the paper), `vera/literature/anchoring.py`,
`vera/literature/paper.py` (prompts), `vera/literature/sentence_checks.py` (new). One implementation for the review and the paper.

- **The writer declares each sentence's kind.** Claim sentences as now. A synthesis sentence names, as premises, earlier claim
  sentences of its section; after verification these resolve to claim ids, and a synthesis whose premise was removed is
  repaired once against the remaining claims, then removed.
- **Synthesis is checked like interpretation:** the deterministic rules of `vera/audit/inference.py` (premises exist, no stray
  attribution, no unsupported number, no name absent from the premises), then the judge question `paper.inference_follows`
  on the sentence and its premise claims. A confident no or an unsure verdict, after one repair, removes it.
- **Transitions are checked to carry no fact:** a new judge question `sentence.no_fact` ("Does this sentence state anything
  about the literature, a study, a result or the evidence?"). A yes makes it a synthesis without premises: repaired once, then
  removed.
- **Deterministic rules, no model call** (`sentence_checks.py`):
  1. *Agreement needs two sources.* A synthesis or interpretation that says studies agree, disagree, converge, conflict or that
     "several"/"the two" studies show something must have premises from at least two distinct sources (P1's "The two studies
     therefore disagree").
  2. *Absence belongs to the record.* A sentence in an evidence section saying the evidence lacks something ("no passage",
     "none of the studies", "no study examines") is removed; what the evidence lacks is stated in the threats section, from the
     run's files (P3's "no passage covers recursive language models on cost").
  3. *"X and colleagues" names a source* (also "X's team", "the X group", "X and co-authors"), added to
     `anchoring.names_a_source_without_a_claim` (P3's "Shao and colleagues").
  4. *A quote that leans on context is widened.* A quote opening with a demonstrative or a back-reference ("This", "These",
     "Such", "It", "However, this") is extended with the preceding sentence of the same passage, which keeps it verbatim, and
     re-checked; with no preceding sentence available it fails the quote-alone check (P1 C41).
  5. *One quote, one claim id.* A claim reusing a (source, quote) pair already cited gets the earlier claim's id instead of a new
     one; premises are counted by distinct quote and source, and the method section reports claims, distinct quotes and sources.
- **Claims that say more than their quotes:** a new judge question `claim.within_quote`, shown only the claim and its quote:
  "Does the claim add anything the quote does not say: a name, number, model, characterisation or causal link?" A yes or unsure,
  after one repair, removes the claim. It runs after the existing frozen checks and does not replace them. Its wording may be
  tuned on the dev split only.
- **Interpretation:** the same agreement rule applies, and `paper.inference_follows`'s wording may be tightened on the dev split
  (test every clause and quantifier; absence of evidence in the set is not evidence of absence).

**Acceptance:** offline tests with a fake generator and judge for each rule and each new question: P1's "two studies disagree"
with one source is removed; P3's absence sentence is removed; "Shao and colleagues" is caught; a "However, this ..." quote is
widened and re-verified; a repeated quote shares one id; a transition stating a fact is repaired or removed; a claim adding a
model name is removed; a synthesis whose premise was removed is repaired, then removed; the producer never judges its own text;
the review's existing tests still pass. `test_RSH_F_15_…` exists.
**Gate:** `sentence_checks_ready`.

## The audit lists every sentence (AUD-F-12)

`vera/audit/sentences.py` (new), `vera/app/pipeline.py`, `vera/app/pdf.py`, `vera/app/static/`.

- The audit of a review or a paper runs the frozen literature audit as now, then `sentences.audit` re-checks **every** sentence
  of the evidence sections: claim sentences by their claims, synthesis by the rules and the judge, transitions by `sentence.no_fact`,
  plus the `claim.within_quote` question on every claim. Findings are `sentence` findings; a confident failure is `fail`, unsure
  is `warn`.
- **Documents made before 0.13** (Increment 6's papers, earlier reviews) have no sentence records: the audit splits their evidence
  sections into sentences, treats a sentence with a claim as a claim sentence and every other one as a transition, so any
  factual claim-free sentence is reported. This is how the three Increment 6 papers are re-audited.
- The light's words say what it covers: *"Green: the citations are real, each claim is supported by and says no more than the
  passage it quotes, each synthesis and interpretation was judged to follow from the claims it names, and the other sentences
  state no facts."*
- **Reader and PDF:** a synthesis sentence is marked as such with its premise links (as interpretation premises are); Appendix B
  lists claims by distinct quote; a new appendix lists synthesis sentences and their premises. The run page says which spend it
  shows (the run's whole spend, or the paper's), since the external review read $0.94 beside the PDF's $0.77.

**Acceptance:** tests that the audit reports a factual claim-free sentence, a synthesis whose premise does not support it, and a
claim saying more than its quote; that old documents are audited without error; headless-browser tests of the synthesis marking in
light, dark and narrow layouts; PDF tests for the new appendix and the light's wording. `test_AUD_F_12_…` exists.
**Gate:** `audit_sentences_ready` (requires `sentence_checks_ready`).

## The real-case set: labelled by Chris, frozen, measured

`scripts/build_realcase_set.py`, `scripts/record_realcase_labels.py`, `scripts/measure_realcase.py` (new),
`data/realcase/`.

- **Items are real text from VERA's papers**, not written by the checks' author: cited claims with their quotes, claim-free
  evidence sentences with the claims of their section, and kept interpretation statements with their premises, from the three
  Increment 6 papers (about 170 claims, 80 claim-free sentences, 50 statements).
- **Split by paper.** Dev: P1 (the external review read it closely, so its cases are known). Test: P2 and P3, about **90 items**:
  every item the external review or the scorer named, plus a random sample of the rest, shuffled, with no mark of which were named.
- **Labels.** The dev split is labelled by the agent from the external review and the scorer's notes, and may be used to tune
  question wording. **Chris labels the test split** on a sheet (one line each: *says no more than its quote / says more /
  needs outside context*; *follows from its claims / does not / states no fact*), about 1.5 hours. His labels are the reference.
- **Frozen before the one test run:** items, labels and the source of every check are hashed
  (`data/results/realcase_hash_incr7.json`) before `measure_realcase.py --split test` runs once.
- **Reported, whatever it shows:** for each item type, the share of Chris's "bad" items each check flags and the share of his
  "good" items it wrongly flags, with Wilson intervals, **for Increment 6's checks and for the new ones on the same items**.
  That comparison is the increment's main result.
- **Limits stated now:** the test split is small (about 15 to 25 bad items in all), so intervals will be wide; Chris has read the
  external review and the scorer's notes, so some test items are not new to him.

**Acceptance:** `check_carry7.py --part realcase`: labels attributed to Chris and dated before the hash; the hash file predates
the test results; results for both the old and the new checks on every test item.
**Gates:** `realcase_labelled` (human, Chris's labels recorded), then `checks_measured` (requires `sentence_checks_ready`).

## A targeted search for what the paper names (RSH-F-16)

`vera/literature/retrieval.py`, `vera/literature/paper_evidence.py`.

- When the paper's emphasis or the confirmed question names a work (a quoted title, an arXiv id, or "Name et al." / "Name and
  colleagues" with a system name) that is not among the run's sources, the paper stage makes **one targeted lookup** per name
  (at most 3) through the existing search clients, before widening.
- A work found with an open-access text is read and its passages added to the paper's evidence, through the same reading and
  verification; the review's own sources and claims are unchanged.
- The threats section, written from the run's files, says what was searched for and whether it was found and read.
- No other change to retrieval; the general search is not repeated.

**Acceptance:** offline tests with a fake search client: a named work not in the sources is looked up once; found works join the
evidence with new passage ids; a miss is stated in the threats section; at most 3 lookups; nothing named means no lookup.
`test_RSH_F_16_…` exists.
**Gate:** `coverage_search_ready`.

## Papers made again, and a fresh one (human)

Chris, in the app with his own key: (a) re-audits the three Increment 6 papers with the new audit (no rewriting; the light may
change from green and that is the point); (b) makes a paper again from P2's review (`discuss-the-evolution-of-prompting-guv8`),
same request, cap $1.00; (c) makes a paper from a finished review not used in Increment 6. Recorded in
`data/paper_rerun/record.json`: run ids and Chris's notes; spend, lights, and kept and removed counts by sentence kind are computed
from the copied run files, not typed.

**Acceptance:** `tools/checks/check_paper_rerun.py`: three re-audit reports and two new papers, each within its cap, each audited.
**Gate:** `paper_rerun` (human, requires `audit_sentences_ready`, `checks_measured` and `coverage_search_ready`).

## Rubric scoring of the new papers (human, blind)

The two new papers on the Increment 6 rubric (six criteria, 1 to 5). Chris scores first and blind; then an independent scorer (a
fresh agent, told not to open Chris's file) scores them **and reads every claim against its quote and every synthesis sentence
against its premises**, recording each defect it finds by kind. The defect counts per paper are compared with Increment 6's scorer
counts (P2: 6 claims of 59).

**Acceptance:** `check_rubric7.py`: both score files; Chris's earlier and attributed; the scorer's not a copy and listing its
defects by claim or sentence id.
**Gate:** `rubric7_scored` (human, requires `paper_rerun`).

## Increment 7 review

`docs/reviews/incr-7.md`: what was built; each acceptance criterion met or not; spend against each cap; the real-case results,
old checks against new; what the re-audits of the Increment 6 papers found; the new papers' defect counts against Increment 6's;
the cost of the extra checks per paper; deviations; what the next increment takes. Plain about what was not shown.

**Acceptance:** `check_dogfood.py` finds an overhead entry for each day a gate passed; traceability passes; the independent
Evaluator passes the review.
**Gate:** `incr7_review` (human + Evaluator).

## Decisions for Chris at incr7_scoped

1. **Caps:** $1 debugging, $1 measurement, $0.50 re-audits, $2 new papers, $5 for the increment (above).
2. **Renumbering:** the optional "P1 on external papers" moves from Increment 7 to Increment 8, with its requirement rows
   (AUD-F-01, -02, -06, -08, AUD-P-01, -02). (Done in this draft; revert if you prefer.)
3. **The review changes too.** Sentence statuses and the new checks run in `verify_sentences`, which the review and the paper
   share, so a review made after this increment will drop sentences that a review made before it kept. Recommended: yes, one
   implementation. The alternative is paper-only, which leaves reviews with the same blind spot.
4. **Labelling:** Chris labels the test split (about 90 items, about 1.5 hours); the agent labels the dev split. The alternative,
   an independent agent labelling with Chris checking a sample, is cheaper for Chris but is a Claude model labelling a Claude
   system's output.
5. **Targeted search** for works the paper names is **in**, limited to 3 lookups; the general search is not repeated.
6. **Freeze:** the plan changes no frozen file. If building shows one must change, the agent stops and asks before changing it.
