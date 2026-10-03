# SPEC — VERA, Increment 4 (paper quality and the measured comparison)

## Overview

Current-increment features only, in build order. Each `##` below becomes a
tracked feature (`scripts/features-init.sh`); do not add `###` headings.
Source: [docs/07-increments.md](docs/07-increments.md) Increment 4; schemas:
[docs/03-interfaces.md](docs/03-interfaces.md) v0.9, with v0.10 proposed where
a feature needs it; requirements due: RSH-F-04, RSH-F-11, AUD-F-05, AUD-F-07,
RSH-P-02, plus everything due earlier
([docs/02-requirements.md](docs/02-requirements.md)); trades to decide: T10's
measured half (a hand-built harness against a thin generic one, on one problem
done both ways), and the reverse-ifs this increment first tests (T5 (5) and (6),
T7 (4), T1 (1) again on larger N)
([docs/04-trade-studies.md](docs/04-trade-studies.md)). Rewrite this file at each
increment review. The Increment 3 SPEC is in git history; its review is
[docs/reviews/incr-3.md](docs/reviews/incr-3.md).

The goal, as Chris restated it at the Increment 3 review: **very good research on
whatever topic is requested**, not novel research. Increment 3 built a pipeline
that is cheap ($0.14 to $0.22 per topic), traceable and candid, and found where
it is weak: retrieval recalled 70%, 38% and 20% of the key papers; the loop's
paper on the tree-explain topic does not answer the question the user confirmed;
a green audit means citations are real and claims are supported by their
passage, not that every clause is anchored; and the quality measure rests on one
language-model scorer because Chris's own blind scores are missing. This
increment fixes those, then tests the result where it can be measured: **two
complete runs on two parent problems that ScientistTwo also attempted**
(RSH-P-02, MOE-3), with an honest account of where the write-ups fall short of an
academic paper.

The product, one step wider: the loop's experiment stage can run a **registered
protocol** (the experiment the confirmed question describes) as well as generate
and screen ideas; the write-up is paper-shaped, with figures VERA draws from the
results, a related-work section from the verified literature, ablations when
there is a winner, and a final audit that adds method-code alignment and a novelty
check; the literature stage discloses its own retrieval statistics and anchors each
claim to a quote that covers it. Direction B puts an app on this in Increment 5;
nothing here builds UI.

Who does what: Claude Code builds and runs short work; Chris chooses the fresh
topic and its key papers, confirms or edits the second problem, launches long
runs from his terminal, approves the human gates, **scores the outputs blind**,
and reads the ScientistTwo comparison. Chris approves human gates himself;
the agent reports readiness and never approves for him.

Rules carried from the Increment 3 review:

- **Spend.** Every model call goes through a `Budget` that raises before a
  limit is crossed, inside the $20/month ceiling (ConOps §4). Proposed caps for
  Chris to confirm at `incr4_scoped`: $2 for debugging and smoke runs; $6 for the
  end-to-end runs and the fresh topic (a topic and a loop run cost about $0.25
  together in Increment 3, so this is generous until measured); $1 for
  reference-judge calls; $9 for the increment, each calendar month inside $20.
  Jev is billed separately and counts. The OpenRouter key keeps its credit limit.
  Increment 3 spent $1.66 of its $11.
- **One ledger file per run**, `data/ledger/run_<run_id>.jsonl`, never deleted,
  truncated or overwritten (Increment 3 deleted two by accident; a run that must be
  discarded is marked `discarded` in its report, not deleted). Named result
  ledgers are committed, the rest are git-ignored.
- **The cheap judge path is one shared function** (T1: Jev → GLM at 0.7;
  `loop.*` and `lit.*` straight to GLM). Where a computed answer exists a **rule**
  decides, not a judge (see the first feature).
- **Judge and generator configuration is the loop's** (`reasoning: {effort:
  minimal}`); every judge measurement uses that setting.
- **No peeking.** A topic's key-paper list is written and hashed before its
  first retrieval; each registered target and protocol is written, dated and
  hashed before any run on it; the problem specs and prompts of the two runs never
  contain ScientistTwo's paper on the problem or its numbers. The inventory
  (`data/corpus_inventory.csv`) holds my summary of ScientistTwo's reported gains
  (`reported_gain_pct`); choosing the second problem uses only its compute and
  code columns, and **no run's design reads that column**; the comparison reads it
  after both runs, with the comparison protocol fixed first.
- **Independence (docs/06 §5).** Seeded-fault, novelty gold-set and re-test sets are
  split dev/test **by source run or topic**, with the test hash recorded before any
  result on it. **The audit's code is frozen before its test run**: the split file
  records a hash of the audit's source tree and the results record the hash they
  ran with; a change after a test run spends that test set and a new one is built.
  This increment changes the audit (new checks, the dataset-name fix), so the
  Increment 2 and 3 seeded sets stay as the record of the audits they tested and a
  new set (v3) tests the new one.
- **Human scoring is blind and attributed.** Chris's rubric scores are recorded by
  Chris, before he reads the independent scorer's, with `--blind` stated; a file of
  scores that equals the independent scorer's cell for cell is not counted.
  Language-model helpers' labels are disclosed as such wherever they are used.
- **Same model grading itself.** Every `StageResult` records the generator and the
  judge; the review has a section on where families coincide (Sonnet 5.5 writes
  and is the reference judge; the labelling helper is the same family).
- **Secrets.** No maintainer key in any artifact (APP-C-01), none reaches the
  sandbox, none in any retrieved or cached page. `tests/test_no_secrets.py` stays.
- **Long runs** are resumable and launched from Chris's terminal, or split into
  segments under 10 minutes; the runner keeps the machine awake.
- **Dogfood.** Overhead hours are logged **at the end of every session**
  (`bash scripts/dogfood.sh overhead <hours> <note naming the dates and work>`);
  missed in Increments 0 to 3. `check_dogfood.py` treats an entry as covering a day
  only if it was recorded after the last review gate passed, so one carried-over
  entry cannot satisfy a new increment's first day (the Increment 3 loophole).
- **Outward-facing actions** need Chris: an upstream issue, a pushed commit, a
  request to a bibliographic service beyond polite keyless use.

Gate DAG proposed for `.meridian/gates.yaml` after `incr4_scoped`:

```text
incr3_review ─► incr4_scoped ─┬─► carry_in_ready ─► lit2_ready ─────────────────────┐
                (human)       │   (automated)       (automated; needs topics4_chosen)│
                              ├─► topics4_chosen ───────────────┘                    │
                              │   (human: the fresh topic, key list hashed)          │
                              └─► problem2_ready ─► protocol_ready ─► writeup2_ready ┤
                                  (automated:       (automated)       (automated)    │
                                   harness, target)                                  │
   ┌─────────────────────────────────────────────────────────────────────────────────┘
   └─► audit4_ready ─► runs4 ─► comparison4 ─► rubric_scored ─► incr4_review
       (automated;     (automated;  (human reads;  (human: blind     (human + Evaluator)
        seeded v3)      two runs)    protocol set)   scores)
```

## Carry-in: rule gates, audit hygiene, dogfood

`vera/loop/`, `vera/audit/`, `tools/checks/`. Fixes the Increment 3 review named,
built and tested offline before any stage uses them:

- **Rule verdicts where a table decides.** `loop.beats_baseline`,
  `loop.baseline_reproduced` and `loop.best_method` have a computed answer (the
  shadow answer). The gate for each becomes a **rule verdict** (backend `rule`,
  confidence 1.0, as the audit's gate already is), recorded in `gates.jsonl` beside
  the judge's answer, which is kept for measurement only. Reason: the Increment 3
  re-test found both Increment 2 confident misses were near-ties where the table
  says "strictly better" and the judge applied a statistical sense; the rule
  cannot. The judge stays where no rule can decide (guidance met, idea worth a
  run, `lit.*`).
- **Audit table check robust to dataset names.** The table check reads a dataset
  name back from its lower-cased column label, so any name with an underscore
  failed every column (`topic-a-loop-2`). Read the dataset from the run's
  `results.json` datasets by normalised comparison, not from the label.
- **Repair log complete.** `audit_repair.json` appends a record per pass (it kept
  only the last for credal-dro), and a repair that drops a clause from a claim lists
  the dropped text.
- **Per-session overhead.** `scripts/overhead-due.sh`, run at the end of every session, prints the
  overhead command with the dates of gates passed since the last entry; the check
  rule above.
- **Schemas 0.10 (docs/03 first):** `ProtocolSpec` (methods, datasets, metrics,
  seeds, the registered target file and hash), `FigureSpec` (kind, source cells in
  `results.json`, caption), and `LiteratureSection.retrieval_stats` (queries,
  candidates, kept, read in full, dropped by the screen).

**Acceptance:** a seeded near-tie is decided by the rule and the judge's wrong
answer is recorded beside it; a table with an underscore dataset name audits
clean; a repair that drops a clause lists it; `check_dogfood.py` refuses a day
covered only by an older entry; schemas round-trip and invalid ones raise;
`check_schema_version.py` passes at 0.10.
**Gate:** `carry_in_ready`.

## Fresh topic and key papers (human decision, before any retrieval)

`data/topics/`. The key lists of the three Increment 3 topics are no longer
independent evidence: retrieval was changed after seeing them. A fresh topic
tests the retrieval changes honestly. Chris chooses it (the agent proposes up to
three; the proposals follow the Increment 3 rules: a topic with a defensible answer
in the literature, not one the agent has already seen results for), writes or
approves 8 to 10 key papers whose identifiers are checked against arXiv and
Crossref (a metadata check of the listed papers, not a topic search), and the list
is hashed before the first retrieval. Chris chooses whether the topic is empirical
with an existing harness, empirical without one, or non-empirical.

**Acceptance:** `check_topics.py` passes with four topics; the fresh topic's
hash precedes its first retrieval record.
**Gate:** `topics4_chosen` (human approval, token "TOPICS 4 CHOSEN").

## Literature stage v2: retrieval, anchoring, disclosure (T5 reverse-ifs)

`vera/literature/`. T5's reverse-if (5) read on the independent coverage scores
(2, 2, 1, 1) and its remedy moved here from "before the next topic".

- **Query generation from the confirmed question:** several phrasings, the question's
  named methods and datasets, and, where the scoping step names them, venues and
  authors; the Increment 3 queries were few and close to the question's wording, and
  all 16 missed key papers were indexed. Optionally a second keyed source (Semantic
  Scholar) when the user supplies a key; never a maintainer key.
- **Retrieval statistics in the review text:** a paragraph the stage writes from its
  own counts: queries run, candidates retrieved, kept by the screen, read in full,
  and the number the screen dropped, plus the plain statement that a "what is not
  established" paragraph is conditional on what retrieval found. No key-paper figure
  is available for a user's topic, so none is claimed.
- **Claim anchoring:** a claim is one assertion with one quote that covers it. A new
  deterministic check rejects a claim sentence that joins two assertions (a
  conjunction or a comparison clause the quote does not contain), and a new judge
  question `lit.quote_covers_claim` (shown the quote only, not the passage) must
  pass; failures go to the repair step, which lists what it drops.
- **Measured on the fresh topic and re-measured on the three old ones** (reported as
  not independent). Reverse-ifs restated: recall on the fresh topic below 70% again
  opens T5; a claim-anchoring failure rate above 10% on the three old sections' claims
  means the check is too loose or the synthesis prompt needs the one-assertion rule.

**Acceptance:** `test_RSH_F_09_…` extended; recall on the fresh topic and the old three
reported with the key papers found and missed; every review states its retrieval
statistics; the anchoring checks are measured on the 56 existing claims and the 30
labelled real claims.
**Gate:** `lit2_ready`.

## Second parent problem and T10's measured half

`docker/`, `vera/loop/`, `data/topics/`. The second problem is one that ScientistTwo
also attempted and that is CPU-scale. The inventory flags three candidates for the
loop; one is TreeHFD, one is STELLA (a single-GPU model, kept for later), and one is
**credal ambiguity sets** (Chen et al., arXiv 2601.21324, code
`MengqiChenMC/credal-ambiguity-sets-code-repo`), the Increment 0 fallback and the paper
the Increment 3 retrieval missed on the credal-dro topic. Its compute is unresolved
(some of the parent's experiments used 4-GPU nodes).

1. **Feasibility check first** (an hour, no model calls): read the parent's repository
   and paper, find the replications that run on a CPU in minutes, and record the
   result in `docs/results/problem2_feasibility.md` with the evidence. If none do,
   stop and bring Chris the alternatives from the inventory; the choice is his.
2. **Register the target** from the parent paper only (the metric, reference values,
   tolerance, datasets and seeds), dated and hashed before any baseline run.
3. **Harness by hand** (T10 option (a)): a Dockerfile pinned to a commit, a harness with
   validity checks, a baseline-reproduction run, timed in hours and logged.
4. **T10 option (c) measured on the same problem:** a thin generic harness (data
   loading, seeds, the metric and validity checks, taken from the by-hand one) and a
   model-written adapter that calls the parent's code, accepted by the same baseline
   gate. Report whether the gate accepts it, how many generation attempts it took, the
   cost, and what fraction of the by-hand harness was generic.
5. Chris reads the evidence and decides T10 at `runs4` review time (the SPEC's
   review section), with **Scores / Decision / Reverse if** in docs/04.

**Acceptance:** `tools/checks/check_problem2.py`: the feasibility note, the registered
target with its hash predating the first baseline run, a baseline-reproduction result
within the registered tolerance (or a stated, evidenced failure), both harness variants
built, and the timing and cost of each recorded.
**Gate:** `problem2_ready`.

## Protocol experiments: answering the confirmed question

`vera/loop/`, `docker/sandbox-treehfd/`. The Increment 3 paper on tree-explain
tested two post-hoc corrections and said so; the confirmed question asked how
TreeHFD's decomposition compares with TreeSHAP and with the true components as
pairwise correlation rises, and how stable the component importances are under
bootstrap refits. The loop gains a second experiment mode: it runs a **registered
protocol**, the experiment the question describes, and the write-up reports it.

- `ProtocolSpec` for the tree-explain question: methods (TreeHFD, TreeSHAP-based
  decomposition, and each idea that survives the screen); datasets (the analytical
  function at a correlation sweep of at least five values from 0 to 0.95, plus the
  registered public datasets); metrics: error of the recovered components against the
  analytical true components (the TreeHFD paper gives the closed-form decomposition for
  the analytical case, Table 3; the derivation is checked against it before use), rank
  stability of component importances over bootstrap refits (Spearman across refits),
  residual error as before, runtime.
- The sandbox image gains the TreeSHAP implementation, pinned; the harness computes the
  new metrics; validity checks (shape, finite, components depend on their own variables
  only) stay.
- The protocol and its target values (where the paper gives any) are registered, dated and
  hashed before any run. A protocol run produces a results table and figures; the
  write-up cites them; the audit checks every table cell and figure datum against
  `results.json`.
- Ideas still run, judged by the rule gate on the registered primary metric; a protocol
  run does not need an idea to beat anything.

**Acceptance:** tests offline with a fake sandbox; one live run of the protocol on the
tree-explain question inside $1, whose results table has every registered cell valid
(or marked invalid with the reason); the closed-form ground truth reproduces the
paper's Table 3 values for the analytical case within 1% before any method is scored.
**Gate:** `protocol_ready`.

## Paper-shaped write-up and ablations (RSH-F-11, RSH-F-04)

`vera/loop/writeup.py`, a new `vera/loop/figures.py`, `vera/loop/ablation.py`.

- **Paper shape:** abstract, introduction, related work (restating the verified section,
  as now), method (what was run, with the harness and protocol named), results with
  **figures**, limitations, references, following the output guidance and its word
  limit. Figures are drawn by VERA from `results.json` (matplotlib, a fixed style), not
  written by the model; each has a `FigureSpec` naming its source cells, and the model
  writes the caption and the prose around it. The audit checks that a figure's data
  equal its source cells (a figure drawn from altered numbers is a fail), and the
  guidance check requires every figure to be referenced in the text.
- **Reproduction basis stated:** the paper must state which row set (held-out or
  in-sample) the baseline was reproduced on, per dataset, as registered, and must note
  a trend its own baseline row shows (the Increment 3 paper did not remark that
  TreeHFD's residual falls from 5.5% to 1.0% as correlation rises).
- **Ablations (RSH-F-04):** when an idea beats the baseline on at least one registered
  dataset on the primary metric, the loop runs ablations before the write-up (remove or
  disable each described component of the idea, same seeds) and the paper reports them.
  When no idea wins (every run so far), no ablation is run and the paper says so; the
  requirement is verified by a demonstration with a scripted generator whose idea
  provably helps.
- **Honest account:** the review states, per section, where the paper falls short of an
  academic paper (missing baselines, few seeds, no statistical tests, narrow datasets).

**Acceptance:** `test_RSH_F_11_…` and `test_RSH_F_04_…` (demonstrations, D in docs/02);
a produced paper has every required section and its figures match their cells; the
ablation stage runs on the scripted winner and is skipped, with the reason, on a run
with none.
**Gate:** `writeup2_ready`.

## Audit v3: method-code alignment, novelty, a seeded set that can fail

`vera/audit/`, `data/seeded_v3/`, `data/novelty_gold/`. Same discipline as Increment 3:
dev and test split by source, the test hash fixed first, the audit's source frozen by
hash before the one test run.

- **AUD-F-05, method-code alignment (the loop's own code):** each method component the
  paper describes must map to code in the run's `method.py` (and the registered harness
  for the protocol), and each substantial code component must be described. A judge
  question per component with the code excerpt and the paper's description; unmatched
  components are findings.
- **AUD-F-07, novelty:** for the loop's idea, retrieve the closest prior work (the
  literature stage's records, then one targeted search) and judge whether the core
  method is materially distinct. Measured on a **gold set** (A in docs/02): pairs of an
  idea and a known prior method, labelled "distinct" or "not distinct" by construction
  (a published method relabelled, against an unrelated idea) and by Chris on a drawn
  sample; reported with intervals. A "not distinct" verdict is a finding, not a block.
- **Seeded set v3:** the v2 fault types plus method-code faults (a described step with no
  code, code with no description), figure faults (a figure whose data differ from its
  table) and a reproduction-basis fault; at least 24 test faults and 6 controls from at
  least 4 source runs not used for dev; the known misses (`reversed_comparison`,
  `misattributed_number`, `overstated_claim`) are reported again, not tuned for on test.
- The v2 audit remains frozen as the record of what it was tested against; the check for
  v3 refuses results whose audit hash differs from the frozen one.

**Acceptance:** `tools/checks/check_seeded_v3.py` and `check_novelty_gold.py` (test hashes
recomputed, frozen audit hash equal to the run's and the current source, intervals
reported, spend within the cap); the AUD-F-05 and AUD-F-07 tests; the results are
reported, not gated on a level.
**Gate:** `audit4_ready`.

## The two end-to-end runs

The tree-explain run (the question's protocol, with the literature section and the
ideas) and the credal run (the second problem's registered harness and target), each
from the confirmed question through retrieval, parent selection, experiments, the
paper-shaped write-up, ablations if there is a winner, and the final audit. Each has its
budget, a wall limit, a ledger, a best-so-far report and a per-stage cost table
(including input share and the largest prompt per stage). Launched from Chris's terminal.
A run that ends in budget exhaustion or a failed audit is a valid result if it says so,
but the gate wants two runs that reached their final stage; a second attempt is allowed
inside the cap and every attempt is kept. The fresh topic runs through the literature
stage only.

**Acceptance:** `tools/checks/check_runs4.py`: two runs with every stage recorded, each
ledger equal to its recorded spend, every verdict from a component other than its producer,
an audit result stated (green, amber or red), a cost table, and the papers committed;
spend within the cap.
**Gate:** `runs4` (requires `audit4_ready`, `lit2_ready`, `protocol_ready`,
`writeup2_ready`, `problem2_ready`).

## Comparison with ScientistTwo (RSH-P-02, MOE-3)

Fixed before reading ScientistTwo's numbers: the **comparison protocol** is written to
`docs/results/comparison_protocol.md` and hashed first. It names, per problem, the metric
as ScientistTwo reports it, what the loop's run reports on the same metric and row set (or
that the two cannot be put on the same row set, and why), the cost per run on each side as
far as it is known (ScientistTwo's cost is not published per run: the table says so, and
does not estimate it), and what would count as a meaningful fraction of its gain (MOE-3's
wording). Then, and not before, the reported gains are read from the inventory and from
the two papers. Chris reads the result and says whether the comparison is fair enough to
state.

**Acceptance:** the protocol and its hash predate any read of the gain column in a run's
design (the run directories show it); the table covers both problems with the caveats; the
review states what the comparison does and does not show.
**Gate:** `comparison4` (human approval, token "COMPARISON READ"; requires `runs4`).

## Rubric scoring (human, blind)

The Increment 3 review had one independent scorer (a language model) and no human scoring:
the file recorded as Chris's equalled the scorer's cell for cell and was written by a
script. This increment closes that. After `runs4`, Chris scores each output (the fresh and
three old reviews, the two papers) 1 to 5 on the five criteria of the product bar **before
he reads the independent scorer's scores**, with `--blind`; the independent scorer runs
afterwards on the same files. A drawn sample of at least 10 of the labelled real claims is
re-labelled by Chris, and agreement with the helper's labels is reported.

**Acceptance:** `tools/checks/check_rubric.py`: every output has an entry by a named human
marked blind and recorded before the independent scorer's file, the entries are not equal to
the independent scores in every cell, and the claim re-label sample exists.
**Gate:** `rubric_scored` (human; requires `comparison4`).

## Increment 4 review

Write `docs/reviews/incr-4.md` against the docs/07 exit criteria: two complete runs compared
with ScientistTwo; an honest account of where the write-ups fall short of an academic paper.
Also: retrieval on the fresh topic against the Increment 3 topics; the claim-anchoring
results; the protocol run's answer to the confirmed question and what it cannot show; T10
decided with the by-hand and thin-harness evidence; the seeded v3 and novelty gold-set
results with the freeze rule kept or broken; the judge on larger N (T1 reverse-if (1), with
the interval stated); the rubric scores of both scorers; spend against the caps; dogfood
overhead per session (the check now enforces it); same-model overlap; deviations; carry-overs
from the Increment 3 review closed or restated; and what changes in the Increment 5 SPEC
(direction B: the app, bring-your-own-key, the T9 reverse-if (2) reasoning control).

**Acceptance:** `tools/checks/check_dogfood.py` finds an overhead entry recorded after the
last review gate for each calendar day a gate passed; the review passes the independent
Evaluator (`run-evaluator.sh`), fresh per round, with every verdict kept and the review's
numbers checked against the ledgers and result files by the Evaluator.
**Gate:** `incr4_review`.

## Decisions for Chris at incr4_scoped

1. The caps above ($2 / $6 / $1 / $9, inside $20 a month).
2. The second problem: credal ambiguity sets, subject to the feasibility check, or another
   from the inventory.
3. Whether the protocol-experiment mode is in scope (it is the largest piece; without it the
   tree-explain paper again cannot answer its question, and the product bar scores it 2).
4. Your blind scoring and claim re-labelling as part of the increment, as above.
5. Read: this SPEC, the Increment 3 review's open items and its deviations.
