# Increment 0 review — know your data

Date: 2026-09-30 · Reviewer: Chris (decisions and human gates) · Author: Claude Code
Gates passed: `confirmed`, `scaffold_ready`, `corpus_fetched`,
`inventory_verified`, `parser_decided`. This review is the evidence for
`incr0_review`.

## Outcome

All six exit criteria in docs/07 are met. The ScientistTwo corpus is 86
generated papers, each mapped to a distinct parent among the 107 accepted
papers ScientistTwo used as inputs. No generated paper publishes code, so
P1 v1 leaves out method–code checks on the corpus. The Increment 2 loop will
run on TreeHFD. Increment 1 (P2 minimum viable judge) is confirmed.

## Exit criteria

| Criterion (docs/07) | Status | Evidence |
|---|---|---|
| Inventory complete for all generated papers (unknowns marked, not blank) | **Met** | `data/corpus_inventory.csv`: 86 rows, no blank cells; `tools/checks/check_inventory.py` passes. Spot-check 0/10 on round 2 (below). |
| Code-availability rate known; decide whether P1 v1 includes method–code checks | **Met** | Rates below. Decision: not on the corpus (see Decisions). |
| 2–3 CPU/single-GPU parent problems identified; one chosen for Increment 2 | **Met** | Candidates flagged in the inventory: STELLA (single_gpu), TreeHFD (cpu), credal ambiguity sets (cpu). Chosen: TreeHFD. |
| Schemas implemented (docs/03 v0.1 → v0.3) with passing tests | **Met** | `vera/schemas/`, `SCHEMA_VERSION = "0.3"` equals docs/03; 98 tests pass, ruff clean. |
| Parser chosen | **Met** | Trade T3 decided in docs/04 (GROBID for references, Docling for tables); gate `parser_decided` approved by Chris. |
| Monthly spend ceiling set | **Met** | ConOps §4: $20.00/month (set 2026-09-29). Increment 0 made no model API calls. |

## Corpus facts

- **Source.** The site publishes no data file; the listing is `paperData` in
  its `index.html`, cross-checked against the site repository (identical 86
  PDFs). All 86 downloaded with provenance (FND-C-02).
- **Parents.** ScientistTwo's paper (arXiv 2609.19644, App. A.1) lists 107
  inputs: 38 NeurIPS 2025, 5 ICLR 2026, 64 ICML 2026 spotlights. The 86
  gallery papers map to 86 distinct parents (49 ICML, 33 NeurIPS, 4 ICLR),
  consistent with the site's "86 of 107" headline. The gallery therefore
  likely shows only successful runs (an inference; the site doesn't say):
  a success-only corpus, which matters for any base-rate claim P1 makes.
- **Venue evidence.** Every parent's venue is quoted from its own
  camera-ready page (proceedings footer or ICLR header) or the authors'
  arXiv record (`data/parent_versions.csv`), not only from ScientistTwo's
  appendix.
- **Compute (parent problems).** 44 single_gpu, 25 cpu, 17 multi_gpu.
- **Reported gains.** Only 7 of 86 generated papers state a single
  percentage gain over their parent; the rest report speedups, ranges or
  several metrics (claims quoted in the inventory notes).

## Rates

**Code availability** (`none` = checked, no public code; `unknown` = not
determined):

| | URL | none | unknown |
|---|---|---|---|
| Generated papers (86) | 0 (0%) | 86 (100%) | 0 |
| Parent papers (86) | 82 (95.3%) | 0 | 4 (4.7%) |

Generated-paper `none` rests on: no code links in any generated PDF (text or
link annotations; reproducible with `scripts/pdf_links.py`), none on the
site, and no repository other than the site under the `scientist-two`
GitHub account (checked 2026-09-29 via the GitHub API; recorded in
`data/README.md`).

**Spot-check error rate** (target ≤ 10%; `inventory_verified`):

| Round | Sample | Incorrect | What it found |
|---|---|---|---|
| 1 | seed 291699 | 5/10 (50%) as judged | 1 data error found by the checker (LD-RPB-OM parent code missed: URL split across lines); 4 venue verdicts caused by the checking sheet, which sent the checker to arXiv first pages that still say "preprint". By the standard adopted later (camera-ready versions), 3 more sampled rows were wrong on parent code: DRO-ROCP, SPECTRA and SMBTT-CCDB (links only in the camera-ready), so the sample held **4 data errors** that round 1's instructions couldn't reveal. |
| 1, re-judged (option B) | same | 1/10 as recorded; 2/10 after a later finding | The 4 venue rows were re-judged correct, but on metadata the pipeline wrote, so not independent. DRO-ROCP was then found wrong on its code URL (present only in the camera-ready version); that finding is recorded in commit 780c3ea's message, not in the file. Not accepted. |
| 2 (option A) | seed 180984 | **0/10 (0%)** | Drawn after moving all parents to camera-ready versions (PMLR v306 for ICML; OpenReview for NeurIPS where needed), re-sweeping code URLs and quoting venues from the papers. Parent code URLs corrected since round 1: 8 (7 present only in the camera-ready: commits 31bf2d1, d20d95d; 1 split across lines in the arXiv PDF: LD-RPB-OM). |

Round 2 was judged by an assistant working from the PDFs, with Chris
spot-checking (Chris's account, 2026-09-30). Commit 344374a's message says
Chris judged all 10; that message is wrong, and this review is the record.
Round 2 therefore rests on an assistant's judgement plus a partial human
spot-check. Records: `data/inventory_spotcheck.csv` (round 2);
`data/inventory_spotcheck_round1.csv` holds the option-B re-judgement, and
the original round-1 verdicts (5/10) are in git history (commits 04ae25a,
780c3ea).

## Decisions

- **P1 v1 and method–code checks (AUD-F-05): excluded for the corpus.**
  Generated-paper code availability is 0%, so the check cannot run on
  ScientistTwo's papers. AUD-F-05 stays in Increment 4, scoped to code the
  checker can access: VERA's own loop outputs, with parent repositories
  (95% available) as reference. docs/02 → v0.2.
- **R1 updated** (docs/05): occurred, so likelihood 2 → 3; trigger fired
  (0% < 25%); impact 3 → 2 by the scoping above. R1 also covers re-run
  checks: the optional re-run (AUD-F-08, Increment 4) cannot re-run
  generated papers' experiments on the corpus, only parent baselines from
  their repositories; the requirement is already optional and is unchanged.
- **RSH-P-02 set: ≥ 2 parent problems** (docs/02), matching R6's limit of two
  problems before the Increment 5 review.
- **Increment 2 problem: TreeHFD** — "Tree Ensemble Explainability through
  the Hoeffding Functional Decomposition and TreeHFD Algorithm" (Benard,
  NeurIPS 2025; arXiv 2510.24815; code `ThalesGroup/treehfd`). Chosen over
  the other candidates because its experiments finish in seconds to minutes
  on a laptop CPU (xgboost, 100 trees, n = 5000, small public datasets), it
  has a clear quality metric (decomposition residual / reconstruction error),
  and ScientistTwo's paper on it (ECTS-HFD) states a comparable result (0.0–0.5%
  residual against TreeHFD's 1–4%), giving MOE-3 a concrete target.
  Fallback: credal ambiguity sets (CPU, seconds per replication; some
  experiments used 4-GPU nodes; unresolved, to check before any switch).
  STELLA: the 30 s (one RTX 4090) / 141 s (CPU) in the shortlist is the
  parent's time per training *epoch* on GlobalWind (its Table 2), not per
  run; the parent's abstract gives about one hour of training for its
  results across five datasets. A loop that runs many candidate experiments
  over five datasets would take hours per cycle, so STELLA is kept for the
  second problem (Increment 5), when longer runs are budgeted. (The
  inventory note said "trains in 30 s"; corrected to per epoch.)
- **TBDs not set here.** JDG-P-01..03 and AUD-P-01..02 stay TBD until the
  Increment 1–2 benchmarks; the inventory doesn't inform them.
- **Increment 1 confirmed** as planned in docs/07 (see Next SPEC).

## Findings for P1 (from inventory work)

Recorded in the inventory notes (all 86 rows) and `data/inventory_flags.json`
(the agents' review flags for the 81 non-pilot rows, plus header counts over
all 86):

- **False publication claims:** 13/86 generated papers carry "Published as a
  conference paper at ICLR 2025" with a placeholder author ("Ambitious AI
  Researcher"); the other 73 say "under review".
- **Uncited or misattributed parents:** about a dozen papers describe the
  parent method they build on without citing it, credit it to another paper,
  or cite it with a wrong arXiv id (e.g. ALOT-DRO, BTV-RDRO, DAGP-HDP-HMM).
- **Weak baselines:** some papers compare against a reproduced baseline below
  the parent's published number (e.g. SAVVY-Vortex, DR-LEF).

These are cheap, high-value first targets for P1's citation and
numeric-consistency checks.

## Process lessons

- **Versions matter.** arXiv preprints lacked content the accepted versions
  have (7 parent code links; venue footers). Parent evidence now comes from
  camera-ready versions.
- **Human-gate instructions are agent output too.** Round 1 failed partly on
  the checking sheet. The sheet is now generated by `scripts/spotcheck_sheet.py`
  and points only at source documents.
- **Checker evidence must be independent of the pipeline.** Option B leaned
  on pipeline-written metadata; it was recorded and not accepted.
- **PDF structure is the hard part** (T3): text extraction is easy; reference
  boundaries, tables and URLs split across lines are not.
- **Network on this machine is flaky** (intermittent DNS); every network
  script retries with backoff. OpenReview refuses scripted PDF downloads;
  15 papers were saved by hand and adopted with provenance.
- **Meridian dogfood:** gate log and lessons in `docs/meridian-dogfood.md`.
  `scripts/dogfood.sh report` shows 0 hook stops and no overhead hours
  logged; blocks this increment came from the human gate, which the tool
  doesn't count. Overhead hours need logging from Increment 1.

## Open items

- 4 parents with `unknown` code (no own repository in any version held).
- The corpus is likely success-only (above); state it wherever P1 reports
  rates on the corpus.
- The T3 escalation run was not spot-checked by Chris; approval rests on the
  first-pass spot-check.
- The fallback problem (credal ambiguity sets) has an unresolved compute
  question (some experiments on 4-GPU nodes).
- Commit 344374a's message misstates who judged round 2 (see Rates).
- `tmp/render/` (page images made during checking) is local and untracked.

## Next SPEC (Increment 1 — P2 minimum viable judge)

Rewrite `SPEC.md` for Increment 1 and add its gates to `.meridian/gates.yaml`
after this gate passes. Changes to carry in:

- Scope per docs/07: router, two backends, ledger, LangGraph helpers,
  benchmark harness; decide T1 (cheap backend) and T2 (runtime).
- The benchmark's judging task is drawn from the TreeHFD loop's gate
  decisions (e.g. "does this result beat TreeHFD's residual?"), so P2 is
  measured on the decisions Increment 2 needs.
- Process: every human-gate checking sheet is generated from source
  documents; spot-check rounds are numbered and kept; dogfood overhead
  hours are logged per session.
