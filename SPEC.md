# SPEC — VERA, Increment 6 (from a review to a paper)

> **Status: scoped 2026-10-11 (`incr6_scoped` approved by Chris, decisions 1-5 below accepted as proposed).** Passed 2026-10-11: `evidence_ready`, `paper_stage_ready`, `inference_set_frozen`, `inference_measured`, `app_paper_ready`; 2026-10-12: `paper_demo`, `rubric6_scored`, `incr6_review` (approved by Chris; docs/reviews/incr-6.md). Increment 6 is complete. The Increment 5 SPEC is in git
> history; its review is [docs/reviews/incr-5.md](docs/reviews/incr-5.md).

## Overview

Current-increment features only, in build order. Each `##` below becomes a tracked feature (`scripts/features-init.sh`);
do not add `###` headings. Source: [docs/07-increments.md](docs/07-increments.md) Increment 6; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.11, with v0.12 (proposed below, written into docs/03 before any code uses
it); requirements due: RSH-F-12, RSH-F-13, RSH-F-14, AUD-F-11, APP-F-04, plus everything due earlier
([docs/02-requirements.md](docs/02-requirements.md)).

**Why this increment.** A finished run gives a literature review of about 500 to 900 words. Every sentence in it rests on a
quote, and it draws no conclusions of its own. Chris asked for the next step twice: in the Increment 5 walkthrough ("possible
conclusions where the question allows") and again on 2026-10-11, after the review
`how-much-useable-information-about-6x3n` ($0.16, green, 16 claims from 12 sources, 6 papers read in full and 42 at the abstract
only). That request was to take the gathered information and, when the user asks, produce an academic-style research paper.
The Increment 5 review listed it as candidate (2), "the labelled Synthesis section and its audit rule".

**Decisions already made by Chris (2026-10-11):**

1. **Interpretation sections are allowed, labelled, and checked by a judge.** A paper may contain the author's own reading
   (discussion, conclusions, a research agenda). Such a section is shown as interpretation, never mixed with evidence. Each
   statement in it names the verified claims it rests on, and a component other than its writer judges whether the statement
   follows from them.
2. **The paper stage widens the evidence.** It reads more papers in full and more passages per paper before writing, and Chris
   accepts that this may touch the audit freeze. The plan below **avoids changing any frozen file**: the limits involved live in
   unfrozen code. If a frozen file must change after all, the freeze rule applies: build a new seeded set first and spend it
   openly.
3. **A "Make a paper from this review" button** on a finished review in the app. The review stays as it is; the paper is a
   second document of the same run.

**What the paper is, honestly.** The question had no experiment behind it, so the paper is a **review paper**: a structured,
survey-style paper with a stated method, findings by theme, a labelled discussion and conclusions, threats to validity and a
research agenda. It is not a paper reporting new results, and its title block says "Review paper". Experiment-mode papers
(`vera/loop/writeup.py`) are unchanged.

**The goal is unchanged:** very good research on whatever topic is requested, checkable sentence by sentence. Success here is
a paper a reader would rather have than the review it came from, **without weakening what the green light means**: green on a
paper must say exactly what was checked, and interpretation is never counted as quote-checked.

Who does what: Claude Code builds and runs short work with offline fakes; Chris approves human gates himself (the agent reports
readiness and never approves for him), presses the button on real reviews with his own key, and scores the outputs blind.

Rules carried from the Increment 5 review:

- **Spend.** Every model call goes through a `Budget` that raises before a limit is crossed, inside the $20/month ceiling
  (ConOps §4). Proposed caps for Chris to confirm at `incr6_scoped`: **$1** for debugging and smoke runs; **$2** for papers made
  from real reviews (the `6x3n` review and two other finished reviews, each capped at $0.75 on the button's form); **$1** for
  measuring the inference check on its seeded set; **$5** for the increment. Increment 5 spent within its $5.
- **One ledger file per run**, `data/ledger/run_<run_id>.jsonl`, never deleted, truncated or overwritten. The paper stage
  appends to the same run's ledger, so the review's cost and the paper's cost are both on record and shown separately.
- **Independence and freezing.** The audit's frozen files (`data/results/audit_hash_incr5.json`: the listed `vera/audit/` files,
  `vera/literature/questions.py`, `reading.py`, `synthesis.py`, `vera/loop/figures.py`, `tables.py`) are **imported, not
  edited**. New checks go in new modules. `tools/checks/check_carry6.py` blocks a changed frozen file.
- **No self-grading.** Producers are `p3.paper.write` and `p3.paper.interpret`; every verdict on their text comes from the cheap
  judge path, and `StageResult` refuses a judge that equals the producer (0.3 rule).
- **Human scoring is blind and attributed**, helper labels disclosed; Chris scores before the independent scorer runs.
- **Secrets.** APP-C-01/02/03 unchanged; the new endpoint is covered by the existing key scan and the adversarial test.
- **Dogfood.** Overhead logged at the end of every session (`scripts/overhead-due.sh`).
- **Outward-facing actions** need Chris: pushing a commit, publishing a paper on the showcase.

Gate DAG proposed for `.meridian/gates.yaml` after `incr6_scoped` (only `incr6_scoped` is defined now):

```text
incr5_review ─► incr6_scoped ─┬─► evidence_ready ─► paper_stage_ready ─┬─► app_paper_ready ─┐
                (human)       │   (automated)       (automated)         │   (automated)       │
                              └─► inference_set_frozen ─► inference_measured ┘                 │
                                  (automated: set hashed (automated: test run,                 │
                                   before the check runs) rates reported)                      │
   ┌───────────────────────────────────────────────────────────────────────────────────────────┘
   └─► paper_demo ─► rubric6_scored ─► incr6_review
       (human: button,  (human, blind)   (human + Evaluator)
        own key)
```

## Schemas 0.12 (docs/03 first)

`vera/schemas/`, `docs/03-interfaces.md`. Written into docs/03 with a version bump and a changelog line **before** any code
uses them; `vera/schemas/version.py` follows (`gate-schema-version.sh`).

```python
class ClaimLink(BaseModel):  # gains an id; old records without one still load
    id: str | None = None  # "C1", "C2", ... in the order claims appear in the document; interpretation cites these


class PaperSection(BaseModel):
    heading: str
    kind: Literal["summary", "record", "evidence", "interpretation"]
    # summary: the abstract; record: written by VERA from the run's files (method, retrieval statistics, threats from those
    # statistics), no model prose; evidence: sentences each carrying a verified claim, or claim-free transitions;
    # interpretation: statements each naming the claims they rest on, judged to follow from them
    text: str


class Inference(BaseModel):
    id: str  # "I1", "I2", ...
    section: str  # the heading of the interpretation section it is in
    text: str
    premises: list[str]  # claim ids, at least one; each must exist in the paper
    verdicts: list[Verdict] = []  # paper.inference_follows, from a component other than p3.paper.interpret
    status: Literal["pass", "removed"]


class PaperRequest(BaseModel):  # the button's form; extra fields are refused
    max_usd: float  # > 0 and at most 25
    length_words: Literal[3000, 5000] = 3000  # target prose length (record sections not counted)
    emphasis: str | None = None  # optional, plain words, at most 500 characters


class PaperDocument(BaseModel):
    run_id: str  # the review's run; the paper lives in runs/<run_id>/paper/
    question: str  # the confirmed question, unchanged from the review
    title: str
    sections: list[PaperSection]  # in order; at least one evidence and one record section
    claims: list[ClaimLink]  # every one with an id and quote_check "pass"
    inferences: list[Inference]  # only status "pass" appear in the text
    sources: list[SourceRecord]
    retrieval_stats: RetrievalStats | None = None
    evidence_stats: dict[str, int]  # papers read in full, at the abstract only, passages available, passages cited
```

`Finding.check` gains `"inference"`. A `PaperDocument` whose interpretation text cites `[Rn]`, or whose inference names a claim id
that does not exist, raises. `OutputGuidance.format` is left as it is (the app sends `"paper"` for a review, which literature mode
ignores; this increment documents that and does not change it).

**Acceptance:** round-trip tests for each new type, a test that each raising rule raises, and `check_schema_version.py` passing at
0.12.

## Wider evidence for a paper (RSH-F-14)

`vera/literature/paper_evidence.py` (new), `vera/literature/stages.py` (unfrozen). Run once, when the button is pressed.

- **More full texts:** read up to **15** of the kept papers in full where an open-access PDF exists (the review read 6;
  `READ_TOP` and `deps.extra["read_top"]` already allow it). PDFs and parses are cached, so papers the review already read cost
  nothing more. Fetching stays polite (arXiv: one request per three seconds).
- **More passages per paper:** up to **10** per full-text paper, through the frozen `reading.rank_passages(..., top=10)`, which
  already takes the limit as an argument. Abstracts stay one passage each.
- **The widened evidence is a superset**: `paper/passages.jsonl` holds every passage of the review's `passages.jsonl` plus the
  new ones, with the same ids for the old, so every review claim still verifies against it.
- **No new retrieval.** The search is not repeated; the paper says so in its threats section. (Coverage is the weakest rubric
  criterion; a wider search is a candidate for a later increment, not this one.)
- **Section-wise evidence:** each findings section is drafted from the passages ranked for that section's theme (BM25, no model
  call), so the prompt limit of 120 passages per call (`MAX_PASSAGES_IN_PROMPT`) is not the cap on evidence.

**Acceptance:** offline tests with a fake fetcher and parser: the paper's passages are a superset of the review's with unchanged
ids; at most 15 full texts and 10 passages each; a fetch or parse failure falls back to the abstract and is reported; nothing is
re-fetched from cache; `check_carry6.py` shows no frozen file changed. `test_RSH_F_14_…` exists.
**Gate:** `evidence_ready`.

## The paper stage: outline, evidence sections, record sections (RSH-F-12)

`vera/literature/paper.py`, `vera/literature/paper_stage.py` (new); the verify logic of `synthesis_stage.verify_node` moved into a
reusable function in the same (unfrozen) module so the review and the paper use one implementation.

The paper is built in this order, each step a node after `verify` in a second graph that resumes the finished run
(`extend_run`), so the review's stages and spend are never repeated:

1. **Outline** (one generator call, `p3.paper.write`): a title and 3 to 6 findings themes, each with the review claims and the
   passages that bear on it. Deterministic check: every theme has at least two passages from at least two sources; a theme that
   fails is merged or dropped.
2. **Evidence sections** (one call per theme): sentences with claims, exactly as the review's synthesis does them, then the
   **same verify path**: source resolves, the quote is verbatim in a passage of that source, the judge says the passage supports
   the claim, no unanchored connective, no dangling reference, the quote alone states the claim; failures repaired once, then
   removed, every removal counted. An introduction and background section is drafted the same way.
3. **Record sections, written by VERA, not a model:** *Method* (the confirmed question; the queries; candidates retrieved,
   screened, kept, snowballed; papers read in full and at the abstract; passages available and cited; the models and judges
   used); *Threats to validity* (abstract-only share, no repeated search, retrieval recall as last measured, same-family
   grading, one-claim-one-quote limits). Every number in them comes from a run file and is checked against it.
4. **Claim ids** `C1…Cn` are assigned in reading order across the whole paper.

Minimum: at least 15 surviving claims across at least 3 themes, or the stage stops with a best-so-far report saying why (a paper
on less evidence than that would be the review with padding).

**Acceptance:** offline tests with a fake generator and judge: a planted fabricated quote, a wrong-source quote, an unsupported
claim and a stray attribution are removed from an evidence section exactly as in the review; record sections contain no model
text, and every number in them matches its run file; too little evidence stops with the reason; the producer never judges its
own text. `test_RSH_F_12_…` exists.
**Gate:** `paper_stage_ready` (requires `evidence_ready`).

## Interpretation sections, the inference check and its seeded set (RSH-F-13, AUD-F-11)

`vera/literature/paper_interpret.py`, `vera/audit/inference.py` (new; not in the frozen list), `data/seeded_inference/`.

- **Writing.** *Discussion*, *Conclusions* and *A research agenda* are drafted by `p3.paper.interpret`, which sees **only the
  verified claims** (their text, id and source title), never the passages. So nothing unverified can enter as a premise. Each
  statement comes back as `{"text", "premises": ["C3", "C9"]}`.
- **Deterministic checks:** at least one premise; every premise exists; no `[Rn]`, no author or system named in running text (the
  review's stray-attribution rules, reused); no figure that does not appear in a premise claim.
- **Judge check** `paper.inference_follows` (new question, in the new module): shown only the statement and its premise claims,
  "Does the statement follow from these claims without adding facts or overstating their strength?" A confident no removes the
  statement after one repair attempt; an unsure verdict removes it too (a statement nobody could check is not kept).
- **Shown as interpretation:** each such section carries a fixed label, "Interpretation: VERA's reading of claims C…, judged to
  follow from them; not checked against quotes". The premise ids render as links to the claims.
- **Audit (AUD-F-11):** the paper's audit runs the frozen `run_literature_audit` on the paper's evidence sections and claims,
  then `inference.audit` re-checks every kept inference (premises exist, deterministic rules, the judge question) and adds
  `inference` findings. The light's words for a paper say what it covers: *"Green: the citations are real, each claim is
  supported by the passage it quotes, and each interpretation was judged to follow from the claims it names."* The audit
  appendix lists inferences separately from claims.
- **Seeded set, frozen before it is measured:** about 60 items built from the claims of finished reviews. Controls are valid
  inferences. Planted faults: a new fact, an overstated strength ("proves", "always"), a premise that does not bear on the
  statement, a reversed direction, a named source. Split dev/test by review; the test split and the check's source are hashed
  (`data/results/inference_hash_incr6.json`) before the one test run. Detection per fault type and the false-positive rate on
  controls are reported with intervals.

**Acceptance:** offline tests for every deterministic rule and for removal on a no or an unsure verdict; the interpretation writer
is never given a passage (a test inspects its prompt); `inference_set_frozen` blocks unless the hash file predates the test
results; the measured rates are reported whatever they are (no target is set before the first measurement).
`test_RSH_F_13_…` and `test_AUD_F_11_…` exist.
**Gates:** `inference_set_frozen`, then `inference_measured`.

## The button, the reader and the PDF (APP-F-04)

`vera/app/server.py`, `vera/app/pipeline.py`, `vera/app/worker.py`, `vera/app/pdf.py`, `vera/app/static/`, `scripts/build_pages.py`.

- **"Make a paper from this review"** appears on a finished review with a green or amber audit (not red, not stopped). It
  opens a small form: length (about 3,000 or 5,000 words), optional emphasis, a dollar cap (default $0.75), and one sentence on
  what will happen and what it typically costs once measured. `POST /api/runs/{run_id}/paper` with a `PaperRequest` starts a
  worker on the run with the user's key in its environment (the Increment 5 path).
- **Live view:** the paper's stages (widen, outline, write, verify, interpret, audit) with spend against the paper's cap. Stop
  and resume work as for a review.
- **Reader:** a run with a paper shows two tabs, *Review* and *Paper*. In the paper, evidence sentences are dotted as now;
  record sections carry a small "from the run's files" note; interpretation sections are in a labelled box with premise links.
- **PDF:** "VERA · Review paper", the sections in order, the interpretation label and box, the audit with its paper wording,
  Appendix B (claims and quotes) and Appendix C (inferences and their premises).
- **Static showcase:** papers made in this increment can be added as examples. The button is hidden when `window.VERA_STATIC`
  is set, and both modes stay in step.

**Acceptance:** API tests with a fake runner: the endpoint refuses a run that is not finished, a red audit, an unknown field and
a cap outside (0, 25]; the paper runs on the run's ledger with its own cap; stop and resume work; the key scan and adversarial
test pass with the new endpoint; headless-browser tests of the button, the two tabs and the interpretation box in light, dark
and narrow layouts, with screenshots; PDF tests that the label, both appendices and the paper audit wording are present.
`test_APP_F_04_…` exists.
**Gate:** `app_paper_ready` (requires `paper_stage_ready` and `inference_measured`).

## Papers from real reviews (human)

Chris presses the button in the app with his own key on the `how-much-useable-information-about-6x3n` review, and on two other
finished reviews he chooses. Recorded in `data/paper_demo/record.json`: run ids, caps, spend, wall time, audit light, claims
kept and removed, inferences kept and removed, and Chris's own notes on what reads as a paper and what does not.

**Acceptance:** `tools/checks/check_paper_demo.py`: three records, each within its cap, each with a paper audit report, spend
read from the ledger rather than typed.
**Gate:** `paper_demo` (human, requires `app_paper_ready`).

## Rubric scoring of the papers (human, blind)

Each of the three papers is scored beside the review it came from, on the Increment 5 rubric (answers the question, coverage,
correctness, reproducibility, honesty) plus one new criterion, **interpretation follows from evidence**, 1 to 5. Chris scores
first and blind; then an independent scorer (a fresh agent, told not to open Chris's file) scores the same files.

**Acceptance:** `check_rubric6.py`: both score files exist, Chris's is earlier and attributed, and the scorer's is not a copy.
**Gate:** `rubric6_scored` (human, requires `paper_demo`).

## Increment 6 review

`docs/reviews/incr-6.md`: what was built; each acceptance criterion met or not; spend against each cap; the inference check's
measured rates; the two scorers' scores for paper against review; every defect found in a paper that passed its audit;
deviations from this SPEC; what the next increment takes. Plain about what was not shown.

**Acceptance:** `check_dogfood.py` finds an overhead entry for each day a gate passed; traceability passes; the independent
Evaluator passes the review.
**Gate:** `incr6_review` (human + Evaluator).

## Decisions for Chris at incr6_scoped

1. **Caps:** $1 debugging, $2 real papers, $1 inference measurement, $5 for the increment (above).
2. **Renumbering:** the old optional "Increment 6 — P1 on external papers" becomes Increment 7; its requirement rows (AUD-F-01,
   -02, -06, -08) move to 7 so traceability does not demand their tests now. (Done in this draft; revert if you prefer
   another number for this work.)
3. **Lengths** offered by the button: about 3,000 and 5,000 words (a paper on 15 to 30 claims cannot honestly fill much more).
4. **Wider search** (more queries, more sources) is **out**; wider reading is in. Say if you want the search widened too: it
   costs more and touches retrieval, which the paper's evidence depends on.
5. **Freeze:** the plan changes no frozen file. If building shows one must change, the agent stops and asks before changing it.
