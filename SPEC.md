# SPEC — VERA, Increment 3 (topic front end and literature stage)

## Overview

Current-increment features only, in build order. Each `##` below becomes a
tracked feature (`scripts/features-init.sh`); do not add `###` headings.
Source: [docs/07-increments.md](docs/07-increments.md) Increment 3; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.8, with v0.9 proposed in the
first feature; requirements due: RSH-F-08, RSH-F-09, RSH-F-10, AUD-F-03,
AUD-F-04, and AUD-F-10 (new, proposed below), plus everything due earlier
([docs/02-requirements.md](docs/02-requirements.md)); trades to decide: T10
(new: where a problem's baseline comes from), and the four reverse-if
conditions this increment is the first to test (T3 (1), T5 (1), T7 (1), T9 (3)
and (4) stay watched)
([docs/04-trade-studies.md](docs/04-trade-studies.md)). Rewrite this file at
each increment review. The Increment 2 SPEC is in git history; its review is
[docs/reviews/incr-2.md](docs/reviews/incr-2.md).

The product, one step wider: a **topic** in, and out of it a scoped research
question shown for the user's confirmation, a **literature section** in which
every citation resolves to a real record and every claim attributed to a source
links to a passage that supports it, and, for an empirical question, a CPU-scale
parent problem and baseline chosen from that literature (or the reason none
fits). One topic is then carried through the Increment 2 loop end to end, with
the literature section as the paper's related work. Direction B puts an app on
this in Increment 5; nothing here builds UI.

Who does what: Claude Code builds and runs short work; Chris chooses the three
topics and their key papers, confirms each scoped question, launches long runs
from his terminal, approves the human gates, and decides T10 and the reverse-if
conditions with the evidence.

Rules carried from the Increment 2 review:

- **Spend.** Every model call goes through a `Budget` that raises before a
  limit is crossed, inside the $20/month ceiling (ConOps §4; October had $2.66
  of it spent when this SPEC was written). Proposed caps for Chris to confirm at
  `incr3_scoped`: $2 for debugging and smoke runs; $8 for the three topic
  runs (about $2 for each literature-only topic and $4 for the topic carried
  through the loop, whose Increment 2 run cost $0.05, so these are generous
  until the first measurement); $1 for reference-judge calls in the re-test;
  $11 for the increment, each calendar month inside $20. Jev is billed
  separately and counts. The OpenRouter key keeps its credit limit.
  Increment 2 spent $1.05 of its $11; R10 is re-measured per topic here because
  reading papers is the first input-heavy step.
- **One ledger file per run**, `data/ledger/run_<run_id>.jsonl`, never deleted,
  truncated or overwritten; named result ledgers are committed, the rest are
  git-ignored.
- **The cheap judge path is one shared function** (T1: Jev → GLM at 0.7;
  `loop.*` straight to GLM). New `lit.*` question ids are routed by their dev
  results (see "Claim support"), not assumed.
- **Judge configuration is the loop's.** The judge and generators run at
  `reasoning: {effort: minimal}`; every judge measurement in this increment
  uses that setting, not the Increment 1 benchmark's provider default (a
  Increment 2 deviation).
- **No peeking.** The three topics' key-paper lists are written and hashed
  before the first retrieval for that topic; no tuning on a topic's key papers
  after its first retrieval run. The loop's problem spec for the carried-through
  topic never contains ScientistTwo's paper on it or its numbers
  (RSH-P-02, Increment 4).
- **Independence (docs/06 §5).** Seeded-fault and re-test sets are split dev/test
  **by source run or topic** (the Increment 2 seeded set shared two source runs
  between splits), with the test hash recorded before any result on it. **The
  audit's code is frozen before its test run**: the split file records a hash
  of the audit's source tree, and the results record the hash they ran with;
  the check refuses results whose hash differs. A change after a test run
  spends that test set, and a new one is built (the Increment 2 audit changed
  after its first test run, and nothing could see it).
- **Same model grading itself.** Every `StageResult` records the generator and
  the judge backend; the review reports where they coincide.
- **Secrets.** No maintainer key in any artifact (APP-C-01), none reaches the
  sandbox, and no key in any retrieved or cached page. `tests/test_no_secrets.py`
  stays in the suite.
- **Long runs** are resumable and launched from Chris's terminal, or split into
  segments under 10 minutes (the agent's background limit); the runner keeps
  the machine awake (`vera/keepawake.py`).
- **Dogfood.** Overhead hours are logged at the end of every session
  (`bash scripts/dogfood.sh overhead <hours> <note naming the dates and work
  covered>`); gate blocks are labelled. Missed in Increments 0, 1 and 2, so
  `check_dogfood.py` is on `incr3_review` and takes the increment's start from
  the last review gate passed.
- **Outward-facing actions** need Chris: an upstream issue, a pushed commit, a
  request to a bibliographic service beyond polite keyless use.

Gate DAG proposed for `.meridian/gates.yaml` after `incr3_scoped`:

```text
incr2_review ─► incr3_scoped ─┬─► lit_core_ready ──┬─► scoping_ready ─► retrieval_ready ─► literature_ready ─► audit3_ready ─┐
                (human)       │   (automated)      │   (automated;      (automated)        (automated)        (automated)    │
                              └─► topics_chosen ───┘    confirmations                                                        │
                                  (human)               recorded)                                                           │
   ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
   └─► trades_decided_3 ─► topic_runs ─► judge_retest_3 ─► incr3_review
       (human: T10, T3, T5,  (automated)  (automated)       (human + Evaluator)
        T7 reverse-ifs)
```

## Carry-in: schemas v0.9, stage gates, dogfood check

`vera/schemas/`, `vera/loop/`, `tools/checks/`. The Increment 2 fixes and the
types the new stages share, built and tested offline before any stage uses them:

- **Schemas 0.9** (docs/03 first, with a changelog line, then code):
  `Topic` (id, text, key-paper list reference), `ScopedQuestion` (question,
  why researchable, `empirical`, candidate parent or the reason none fits,
  `status` proposed/confirmed/edited, `confirmed_by`, `confirmed_at`),
  `SourceRecord` (id, title, authors, year, venue, source, url, abstract, open
  access PDF link, retrieval query and rank), `ClaimLink` (claim text, source
  key, quoted passage, locator, deterministic-check result, verdicts),
  `LiteratureSection`, and `RunSpec.topic`. `StageResult.gate` becomes a list of
  verdicts (`gates`), the stage decision derived from them, and a stage whose
  decision is reject must show the verdict that caused it (the Increment 2
  experiments stage stored the first "beats baseline?" verdict while its decision
  was reject). The no-self-grading rule applies to every verdict in the list.
- **New requirement AUD-F-10** in docs/02 (proposed with this SPEC, due
  Increment 3, verified by seeded test): every claim a document attributes to a
  retrieved source shall be checked against that source's text, and an
  unsupported claim is a finding with the quote and the source passage as
  evidence. RSH-F-09 is about the literature section and cites this check.
- **`check_dogfood.py`** takes the start of the increment from the most recent
  `incr*_review` gate passed (instead of an argument), so `incr3_review` needs
  no special-casing; its tests cover this.
- **Upstream note:** a drafted issue for ThalesGroup/treehfd (non-deterministic
  `predict`, evidence and reproduction in
  `docs/results/treehfd_baseline_first_runs.md`) in `docs/upstream/`; Chris files
  it or not. The agent does not post it.
- **Provider and router carry-overs closed:** nothing new; recorded as closed in
  the review.

**Acceptance:** schemas round-trip and invalid ones raise (a confirmed
`ScopedQuestion` without `confirmed_by`, a `ClaimLink` without a quote, a
`StageResult` whose reject has no rejecting verdict, a self-graded verdict in the
list); `check_schema_version.py` passes at 0.9; `test_AUD_F_10_` names exist for
the later feature (a placeholder test is not enough: the traceability check needs
the real one at `audit3_ready`); `check_dogfood.py` tests pass for the
last-review rule; the drafted issue exists.
**Gate:** `lit_core_ready`.

## Topics and key papers (human decision, before any retrieval)

Chris chooses three topics. Selection rules, so the three exercise different
paths of RSH-F-08..10: (a) one **empirical topic with a parent problem the loop
can already run** (the harness and sandbox image exist for TreeHFD; the
proposed topic is "tree-ensemble explainability under correlated features",
ConOps S4's example); (b) one **empirical topic with no harness**, to test
whether the literature stage can find a CPU-scale parent and baseline with
public code, or say why none fits (RSH-F-10; the proposed topic is the Increment 0
fallback problem, distributionally robust learning with credal ambiguity sets);
(c) one **non-empirical topic** (a literature-and-analysis paper; the proposed
topic is the reliability of LLM judges on numeric claims, VERA's own domain,
where Chris can judge the quality himself). Proposals only: Chris decides.

For each topic, before its first retrieval: at least 6 **key papers** (title,
year, arXiv id or DOI), written by Chris or proposed by the agent and approved
by him, stored in `data/topics/<id>.json` with a SHA-256 recorded in
`data/topics/manifest.json`; and a one-line statement of what a good scoped
question looks like. The key papers are the recall measure for retrieval (T5
reverse-if (1)); they are never used to tune the retrieval after its first run.

**Acceptance:** `tools/checks/check_topics.py`: three topics, each with at least
6 key papers and a hash that matches; the topics differ by the path above
(empirical with harness, empirical without, non-empirical); the manifest is
committed before `data/` holds any retrieval output for them.
**Gate:** `topics_chosen` (human approval).

## Topic scoping and confirmation (RSH-F-08)

`vera/loop/scoping.py`. The first stage turns a topic and the run's output
guidance into a `ScopedQuestion`: a proposed question, why it is researchable,
whether it is empirical, and a candidate parent problem or the reason there is
none. The question is written by the generator (Sonnet 5.5, T9) and gated by the
shared judge path (`lit.question_scoped`: is it one question, answerable
within the budget and the sandbox's CPU limits if empirical, and not a
restatement of the topic) as a non-producer verdict. **The run then stops**: it
writes `scope.json` with status `proposed`, a checkpoint and a best-so-far
report, spends nothing more, and waits. `scripts/confirm_scope.py <run>`
(`--accept`, or `--edit` with a revised question) records who confirmed and when
and lets the run resume. Scoping has its own cap (default $0.25) enforced by the
budget; nothing beyond scoping is spent before confirmation.

**Acceptance:** `test_RSH_F_08_…`: with fake backends and a counting spy, a
topic yields a `ScopedQuestion` with every field, the run halts at
`proposed` with exactly the scoping calls recorded, a second start does not
repeat them, an `--edit` replaces the question and records it, no stage after
scoping runs without a confirmation record, and a confirmation with no identity
is rejected; the scoping stage's self-graded verdict raises. Live: the three
topics scoped under the debugging cap, each shown to Chris, each confirmed or
edited by him with the record kept (`runs/<run>/scope.json`, committed copies
in `data/topics/scope_<id>.json`); the review reports how many he edited.
**Gate:** `scoping_ready` (requires `lit_core_ready` and `topics_chosen`).

## Retrieval (T5 as decided, and its reverse-if)

`vera/literature/`. From a confirmed question the literature stage generates
queries (a few per question, from the question text and its key terms), retrieves
from **Crossref and arXiv keyless** (T5), and from OpenAlex only when the user's
own key is set (Chris's `.env` key is fine for his runs; never in an artifact).
Records are deduplicated (title similarity, DOI, arXiv id), written to
`retrieved.jsonl` with the query and rank that produced them, and screened for
relevance with a cheap-path verdict (`lit.relevant`: does this title and abstract
bear on the question?) before any full text is fetched. Polite rate limits
(arXiv one request per three seconds; retries on 429 and 5xx); a cached response
is stored with its URL and retrieval date so a rerun does not re-query.

**T5 reverse-if (1) is measured here.** For each topic, **recall of its key
papers** in the retrieved set before and after the relevance screen, and in the
top 30 by rank, with misses classified (not indexed, query missed it, screened
out wrongly, parse error). A recall below 70% of key papers retrieved (a starting
value, not yet a target) opens T5 in the review: then a keyed OpenAlex or
Semantic Scholar becomes the primary.

**Acceptance:** `test_RSH_F_09_…` is built in the next two features, not here;
this feature's tests: queries, deduplication and rate limiting against recorded
HTTP fixtures; no live request in the offline suite; a retrieval log record for
every record used later; a result cache. Live: the three topics retrieved with the
ledger and `retrieved.jsonl` kept, the recall table per topic in
`docs/results/retrieval_recall.md`, and the relevance screen's verdicts against
Chris's judgement on a drawn sample of 15 records per topic (seed recorded;
agreement reported with its interval).
**Gate:** `retrieval_ready`.

## Reading and evidence passages (T3, T7 reverse-if (1))

`vera/literature/reading.py`. For the records that survive the screen, the stage
reads **abstracts for all of them and full text for the top K by relevance
(K = 6 by default)** where an open-access PDF exists. T3 as decided: **GROBID**
for references and bibliographic fields (and its full-text body for prose, which
runs in about 2 s a paper), **Docling** for tables and where GROBID's body text
fails the quote check (about 80 s a paper on CPU). Each full text is cached by
hash with its parser and version. The stage extracts **evidence passages**
(quoted spans with locators) relevant to the question; passages are the only
text the synthesis may quote.

**T7 reverse-if (1) and (2) are measured here.** Every generator call records its
input size, and the cost report adds, per stage, the input share of cost and the
largest prompt. If input exceeds about 50% of a topic's bill, or any prompt passes
20,000 tokens, the prompt-as-variable arm (prime-agent pattern inside VERA's own
nodes) is built and measured against plain state on the synthesis stage, two
repeats per arm, as T7 specified for Increment 2; otherwise T7 stands with the
measurement recorded. T3 reverse-if (1) is tracked: every seeded or live citation
or quote failure records whether the parser or the check caused it.

**Acceptance:** tests on recorded GROBID and Docling output fixtures: references
and body text parsed into passages with locators, a passage that is not a
verbatim (whitespace- and hyphenation-normalised) span of the cached text is
rejected, a cache hit makes no parser call, a paper with no open-access PDF falls
back to its abstract and says so; the cost report shows input size per call.
Live: reading for the three topics, with per-paper parse time and failures.
**Gate:** part of `literature_ready` (below); no separate gate.

## Synthesis with verified claims (RSH-F-09, AUD-F-10) and the claim-support judge

`vera/literature/synthesis.py`. The generator writes a literature section from
the evidence passages only. Every sentence that attributes something to a source
carries a **ClaimLink**: the source key `[Rn]`, a quoted passage, and its
locator. References are built from retrieved records, never from model text
(the Increment 2 rule). Checks, in order, all recorded with evidence links:

1. **Citation resolves:** `[Rn]` is a record in the retrieval log (the audit's
   rule; a title lookup in Crossref and arXiv runs only for text that did not
   come from the log, for example a sentence the user edited).
2. **Quote is real:** the quoted passage is a verbatim normalised span of the
   source's cached text (deterministic).
3. **Claim is supported:** the cheap-path verdict `lit.claim_supported` (Boolean:
   does this passage support this claim?) from a component other than the
   producer. A claim with no quote, a quote that fails (2), or a failed verdict is
   a finding and, in the write-up, a guidance failure that sends the claim back
   for repair once or removes it.

**The claim-support judge is a new judging task and gets its own benchmark**,
built like Increment 1's: items labelled by construction from real passages (a
claim written to restate a passage; the same claim paired with a different
paper's passage; a claim with its direction or a number altered; a claim that
overstates the passage), split dev/test **by topic**, at least 120 items,
test SHA-256 recorded before any backend sees it, Chris checking at least 9
drawn items. Backends: the decided path (Jev → GLM) and Sonnet 5.5 as reference
(two repeats), within the $1 cap, with confidence intervals. The routing of
`lit.*` question ids (default escalation at 0.7, or straight to GLM as for
`loop.*`) is chosen on dev only.

**Acceptance:** `test_RSH_F_09_…` and `test_AUD_F_10_…` on seeded literature
sections (the seeded set below): a claim attributed to a retrieved source that the
source does not support, a fabricated quote, a real quote under the wrong source
key, and a citation that is not in the log are each found and linked to their
evidence; an unmodified control section raises no `fail`; a section whose claims
all carry quotes that pass the three checks is accepted; the benchmark's labels
check and test hash recorded. Live: a literature section for each of the three
topics, every claim checked, the number of claims repaired or removed reported,
cost per topic.
**Gate:** `literature_ready` (requires `retrieval_ready`; its hooks run the
retrieval, reading and synthesis tests and `check_literature.py`: three
sections, every claim has a link, every link's three checks recorded, spend
within the cap).

## Audit v2 and a seeded set that can fail

`vera/audit/`. The Increment 2 audit passed its seeded set, but the set was
mostly deterministic faults from two source runs, and it was tuned after its
first test run. This feature builds the audit for text it cannot trust and a set
that can show it failing:

- **Claim-cell alignment for results claims (the amber class).** A sentence that
  names a method and a dataset (or metric) must match the value in that cell of
  `results.json`; a real number placed on the wrong method, dataset or metric is
  a `fail`, not a warning. A sentence the extractor cannot attribute to one cell
  stays a warning.
- **Literature checks** (AUD-F-03 on the loop's own text now with a real
  retrieval log, AUD-F-10) from the previous feature, in the same
  `AuditReport`.
- **A new seeded set** (`data/seeded_v2/`): faults planted into write-ups from at
  least **4 source runs** (the loop-001 paper, the T9 comparison papers, and the
  three topic papers' literature sections), at least **6 fault types**, with
  **subtle faults** the Increment 2 set lacked: a real number on the wrong method,
  a value rounded beyond tolerance, a swapped method name in a sentence, a
  paraphrase that reverses a comparison, a citation to a real paper that does not
  support the claim, a quote with a changed qualifier. Split dev/test **by source
  run**, at least 24 test faults and 6 controls; test SHA-256 and the audit's
  source-tree hash recorded before the audit runs on any test item.
- **Cause recorded for every miss or false fail:** audit rule, parser (T3 reverse-if
  (1)), source lookup (T5 reverse-if (4)), or label error.

**Acceptance:** `test_AUD_F_03_…`, `test_AUD_F_04_…` and `test_AUD_F_10_…` on the
seeded set: on the test split report the detection rate per fault type with a
confidence interval and the false-fail rate on controls; the SPEC bar is at least
90% flagged and no `fail` on controls (a starting value; AUD-P-01 stays TBD until
Increment 6), and a result below it is reported as it is and opens the audit's
design, not the bar; `check_seeded.py` refuses a test run whose recorded source-tree
hash differs from the one frozen in the split file; dev runs are free, a
changed audit after the test run needs a new test set.
**Gate:** `audit3_ready` (requires `literature_ready`).

## Parent-problem selection (RSH-F-10) and trade T10

`vera/literature/parent.py` and docs/04 T10. For an empirical question the stage
reads the retrieved papers' abstracts and reference lists and proposes up to three
**candidate parent problems**: a method paper with a public repository, a
baseline reproducible on CPU in minutes, and datasets that fit. Each candidate
records the repository URL and licence, the datasets, the stated or inferred
compute (from the inventory's rules: infer when the parent states none), and
whether a harness exists in `docker/` for it. The stage picks one or says why none
fits, in which case the run writes a non-empirical paper. The pick is a
non-producer verdict (`lit.parent_fits`: is the baseline reproducible on CPU
within the limits?) plus deterministic checks (a repository that resolves, a
licence recorded).

**T10 — where a problem's baseline comes from.** Increment 2 runs TreeHFD through a
hand-built harness (`docker/sandbox-treehfd/harness.py`), not a baseline the
loop wrote. Increment 4 needs a second parent problem. This increment records
what selecting parents from the literature actually produces for topics (a) and
(b): how many candidates have public code that runs in the sandbox, how long each
would take to wrap, and whether a model-written baseline script (the Increment 2
SPEC's original wording) is feasible. Options: (a) a harness per problem written
by hand, (b) a model-written baseline in the sandbox with the baseline gate
unchanged, (c) a hybrid: a thin generic harness with the model writing only the
adapter. Decided at `trades_decided_3` by Chris, with **Scores:**, **Decision:**
and **Reverse if:** in docs/04.

**Acceptance:** `test_RSH_F_10_…` is a demonstration (D in docs/02): for topic (b)
the stage returns candidates with every field or states why none fits, with the
reasons, and for topic (a) it selects TreeHFD; Chris reads the candidates'
evidence and says whether the pick or the refusal was right (recorded in
`data/topics/parent_<id>.json`); T10 written in docs/04.
**Gate:** part of `topic_runs` (below).

## Decisions: T10 and the reverse-if conditions

At `trades_decided_3` Chris decides, with the measurements above: T10 (baseline
source); **T5** (does Crossref + arXiv recall the key papers, or does a keyed
source become primary); **T7** (did input or a long prompt trigger the
prompt-as-variable arm, and if built, what did it save); **T3** (did GROBID or
Docling cause the citation and quote failures, so that a parser or repair change
is needed); the **claim-support routing** for `lit.*`; and the generator for the
literature stage (Sonnet 5.5 as decided, unless the cost per topic makes a
cheaper arm worth testing for bring-your-own-key users; T9 reverse-if (2), a
reasoning control that makes MiMo or DeepSeek usable, is **not** in scope here and
moves to Increment 5 where bring-your-own-key makes it matter). Each decision is
written in docs/04 with **Scores:**, **Decision:** and **Reverse if:**.

**Acceptance:** `tools/checks/check_trade_decided.py T3 T5 T7 T10` finds each
section decided or its reverse-if explicitly recorded as "tested, not fired"
with the numbers; the measured spend so far is within the caps (`check_ledger.py`).
**Gate:** `trades_decided_3` (human approval; requires `audit3_ready`).

## Topic runs: cost per topic and one end to end

The three confirmed topics run from Chris's terminal with the decided
configuration: scoping → confirmation → retrieval → reading → synthesis →
(empirical) parent selection → (topic (a) only) baseline, ideas, subset run, with
the literature section as the paper's related work → write-up → final audit.
Each run has its budget, a wall limit, a ledger, a best-so-far report, and a
per-stage cost table in `data/results/run_<run_id>.json` (including input share
and the largest prompt per stage). Topic (a)'s run is the "carried through the
Increment 2 loop end to end" exit criterion. A run that ends in budget
exhaustion or a failed audit is a valid result if it says so, but the gate wants
three runs that reached their final stage (topic (a): the audit), so a second
attempt of a topic is allowed inside the increment cap and every attempt is kept.
No result from ScientistTwo's paper on these topics is read before the runs.

**Acceptance:** `tools/checks/check_topic_runs.py`: for each topic a run with
every stage recorded, its ledger equal to its recorded spend, every verdict from a
component other than its producer, an audit report (green, amber or red, stated),
and the cost table; the cost per topic table (scoping, retrieval, reading,
synthesis, parent selection, the loop for (a)) is in
`docs/results/topic_costs.md`; topic (a) shows every loop stage. The review states
the result honestly, including the literature section's quality as Chris judged it
on a drawn sample of its claims.
**Gate:** `topic_runs` (requires `trades_decided_3`).

## Judge re-test (claim support and the loop's gates)

Two re-tests, within the $1 reference cap, with confidence intervals:

- **`lit.claim_supported`** on the benchmark built in the synthesis feature, with
  its test set untouched since its hash was recorded, plus the **real claims** from
  the three topic runs (labelled by Chris on a drawn sample of at least 30
  claims, seed recorded), reported separately from the constructed items.
- **The loop's gates** on the new real decisions from this increment's runs
  (`loop.*`), as in Increment 2; additionally the **two confident misses** of the
  Increment 2 re-test (`retest-0008`, `retest-0038`) are examined and their tables
  reported (mislabelled, near-tie, or a judge error), and `loop.idea_worth_run`
  verdicts are reported on their own: their distribution and, where the ideas
  were run, whether a higher score went with beating the baseline (N will be tiny,
  so this is descriptive).

Report agreement with labels and the reference, ECE, flip rate, cost and latency;
T1's reverse-if (1) is restated (decided path below 95% agreement with the
reference on the real decisions) with the result for this set.

**Acceptance:** `tools/checks/check_retest.py` (extended to a named re-test set):
items and test hash recorded, results with intervals, spend within the cap, every
`lit.*` and `loop.*` verdict in the ledgers accounted for (used or excluded with a
reason). A failure does not block the gate; it opens T1 or the routing again in
the review.
**Gate:** `judge_retest_3` (requires `topic_runs`).

## Increment 3 review

Write `docs/reviews/incr-3.md` against the docs/07 exit criteria: three topics taken
to a scoped question and a literature section with verified citations; cost per
topic measured; one topic carried through the Increment 2 loop end to end. Also:
what the literature stage got right and wrong (recall of key papers, the claims
repaired or removed, the topics Chris edited, where the audit missed); the
seeded-fault results with the frozen-code rule kept or broken; the claim-support
benchmark and re-test results; the T3, T5, T7, T10 decisions with their evidence;
R10 re-measured per topic; spend against the caps; dogfood overhead per session
(the check now enforces it); same-model overlap; and what changes in the
Increment 4 SPEC (the paper-shaped write-up, ablations, a second parent problem,
and the ScientistTwo comparison, with T10's decision deciding how the second
problem gets its baseline). Carry-overs from the Increment 2 review are closed or
restated: the `StageResult.gate` quirk, the audit's amber class, `idea_worth_run`,
treehfd upstream, per-session overhead, the 4 parents with unknown code, the
corpus likely success-only, the T3 escalation run not spot-checked.

**Acceptance:** `tools/checks/check_dogfood.py` finds an overhead entry for each
calendar day a gate passed since the last review gate; the review passes the
independent Evaluator (`run-evaluator.sh`), fresh per round, with every verdict
kept, and the review's numbers are checked against the ledgers and result files by
the Evaluator.
**Gate:** `incr3_review`.
