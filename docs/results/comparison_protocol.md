# Comparison protocol: VERA's loop against ScientistTwo (written before reading ScientistTwo's numbers)

Written 2026-10-04, before the `reported_gain_pct` column of `data/corpus_inventory.csv`, the `notes` column, or ScientistTwo's
generated papers were read for this purpose, and hashed (`comparison_protocol.sha256`) in the same commit. The files that hold
ScientistTwo's numbers are named here so that a later reader can see they were read after this one was fixed. Nothing below is
changed after the gain is read except by a dated entry at the end that says what changed and why.

## What is compared

Two parent problems that ScientistTwo also attempted (the inventory's candidates for the loop):

| Problem | Parent | ScientistTwo's paper on it (named in the inventory) | The loop's run |
|---|---|---|---|
| TreeHFD | Benard, NeurIPS 2025, arXiv 2510.24815 | ECTS-HFD (`general_ml/Others_ECTS-HFD`) | the tree-explain run of `runs4` |
| Credal ambiguity sets | Chen et al., arXiv 2601.21324 | BTV-RDRO (`probabilistic/Others_BTV-RDRO`) | the credal run of `runs4` |

## The metric, and the row set

- **What ScientistTwo's number is**: the percentage gain its paper reports over the parent's baseline, as the inventory's
  `reported_gain_pct` records it, on whatever metric and data its paper states. When the paper is read, the table records, per
  problem, the metric, the dataset(s) and the row set (held-out or in-sample) that gain is on, copied from the paper's own words.
- **What the loop's number is**: on the parent's *registered primary metric* (TreeHFD: held-out residual MSE in per cent, lower is
  better, the metric ideas were compared on; credal: test MAE in units of 1e4, lower is better), the relative reduction of the
  mean over the registered seeds against the reproduced baseline's mean, `100 * (baseline - best) / baseline`, for the best idea
  of the run on the datasets both sides use. A run in which no idea beat the baseline reports its gain as zero or negative, as
  measured, and says so; the best seed is never used.
- **Same row set or not**: the two gains are compared only where the dataset and row set coincide. Where ScientistTwo's paper
  used a different dataset, a different split or a different metric (for example the in-sample residual where the loop compared
  held-out values), the table says "not on the same row set" and the comparison for that problem is qualitative only: it states
  both numbers and does not form a ratio.
- **Where the baseline differs**: if ScientistTwo's baseline value differs from the loop's reproduced baseline by more than the
  registered tolerance of its problem, the table says so (the two gains are then relative to different baselines).

## Cost

The loop's cost per run is the sum of its ledger (model spend in dollars), with the sandbox time reported separately in hours.
ScientistTwo's cost per run is not published per run; the table says "not published" and does not estimate it. The cost half of
MOE-3 ("at a small fraction of its cost") is therefore stated as not assessable unless a cost is found in ScientistTwo's own
materials, in which case it is quoted with its source and not adjusted.

## What counts as a meaningful fraction (MOE-3's wording, fixed here)

A **meaningful fraction of the gain** is a loop gain, on the same metric and row set, of at least **25%** of ScientistTwo's reported
gain on that problem (a quarter: an arbitrary, stated line, chosen before the number is known). A zero or negative gain is not a
meaningful fraction, whatever the other side reports. MOE-3 is **met** on a problem only if the gain half holds on the same row
set and the cost half is assessable and shows the loop at under a tenth of ScientistTwo's cost; with the cost not published, the
most the comparison can say is that the gain half holds or does not, and that the cost half is open.

## Caveats the table must carry

- ScientistTwo's gain is self-reported in a generated paper whose experiments this project did not re-run, and the loop's is
  measured by this project's harness with its own seeds.
- The two systems chose different ideas on different data subsets; a larger or smaller gain is not evidence about ability.
- The loop's runs are few (one per problem plus the attempts kept); no interval on the loop's gain is claimed beyond the seed
  spread in the results table.
- Chris reads the result and says whether the comparison is fair enough to state (`comparison4`, token "COMPARISON READ").

## Dated changes

(none)
