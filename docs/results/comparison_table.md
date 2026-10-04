# Comparison with ScientistTwo (read after the protocol was fixed)

Made under `comparison_protocol.md` (hash `comparison_protocol.sha256`, committed 2026-10-04T17:02Z, before the inventory's gain column, its
notes or ScientistTwo's two papers were read for this purpose). Sources read afterwards: `data/corpus_inventory.csv` (`reported_gain_pct`,
`notes`) and the text of ECTS-HFD and BTV-RDRO (`data/cache/text/scientisttwo/`). The protocol is unchanged.

## TreeHFD (parent: Benard, NeurIPS 2025; ScientistTwo's paper: ECTS-HFD; the loop's run: `runs4-tree-explain`)

| | ScientistTwo (ECTS-HFD, as reported) | The loop (this project's harness) |
|---|---|---|
| Metric | residual reconstruction MSE, % of output variance | the same quantity (residual MSE, %) |
| Row set | **in-sample**: its Table 2 is evaluated on the sample used to fit; the same paper reports a median **test** residual of 12.4% (up to 175.8% on one dataset) | primary: **held-out**; in-sample also measured |
| Datasets | 9 UCI benchmarks and synthetic analytical cases | Analytical (n = 5000, rho 0.5) and Airfoil, plus a correlation sweep of the analytical case |
| Reported gain | 0.0% to 0.5% against TreeHFD's 1% to 4% (the inventory records `unknown`: "range, no single %"); also 3x to 8x lower local attribution variability than TreeSHAP | none: the one idea run, C2 (shallower variable selection depth), was worse than the baseline |
| Gain on the same row set | in-sample, from its own ranges: a reduction of roughly 50% to 100% of TreeHFD's in-sample residual | in-sample: Analytical 0.570 to 3.245 (worse by 469%), Airfoil 1.522 to 4.067 (worse by 167%); held-out (the loop's primary metric): Analytical 2.792 to 4.722 (worse by 69%), Airfoil 4.733 to 6.381 (worse by 35%) |
| 25% line of the protocol | | **not met**: a negative gain is not a meaningful fraction |
| Cost per run | **not published** (no dollar or time figure per run; none estimated here) | model spend $0.10 (ledger), sandbox about 24 minutes of wall time |

The datasets (Analytical, Airfoil) and the in-sample row set coincide, so the two gains can be put side by side on those: ScientistTwo reports a large
in-sample reduction and the loop found none. They are not the same experiment (ScientistTwo's baseline values and method differ; its gain is
self-reported in a generated paper whose experiments were not re-run here), and ScientistTwo's own held-out numbers are far worse than its
in-sample ones, the row set the loop's primary metric uses.

## Credal ambiguity sets (parent: Chen et al.; ScientistTwo's paper: BTV-RDRO; the loop's run: `runs4-credal`)

| | ScientistTwo (BTV-RDRO, as reported) | The loop |
|---|---|---|
| Metric | out-of-sample MSD, 0.5 * (mean + standard deviation) of the newsvendor loss | test MAE (units of 1e4) |
| Row set / data | heavy-tailed Student-t newsvendor benchmark under demand spikes | California Housing under an East-to-West geographic shift |
| Reported gain | up to 6% lower MSD than forward-LV under spike contamination, up to 49x speedup over exact solvers (the inventory: "range, no single %") | none: both ideas (C1 covariate-shift importance reweighting, C2 Huber-quantile hybrid loss) were far worse than LV (MAE 24.6 and 47.4 against 10.7) |
| **Same row set?** | **No: a different problem, dataset and metric** | |
| 25% line | | **cannot be assessed on a common metric**; on the loop's own problem the gain is negative, so it is not met |
| Cost per run | **not published** per run; the generated paper's compute is quoted in the inventory as about 42 core-hours in total (inferred, not a cost) | model spend $0.06 (ledger), sandbox about an hour of wall time (the parent's own baseline batch is most of it) |

The loop's credal run reproduced the parent's baseline (LV MAE 10.68 against the paper's 10.7) and then two model-written ideas lost to it by a large margin, with
spreads of 1e-13 to 1e-5 across 100 replications that point at an implementation fault the loop did not diagnose (the paper says so).

## MOE-3

MOE-3 asks for a meaningful fraction of ScientistTwo's gain at a small fraction of its cost. On TreeHFD the gain half is **not met**: the loop's gain on the
shared datasets and row set is negative. The cost half is **not assessable**, since ScientistTwo's cost per run is not published, so MOE-3 is **not met** and
not reportable as met on either problem. On the credal problem the two sides did not attempt the same experiment, so there is no common-metric comparison to
make; the loop's own gain there is negative.

## What this comparison does and does not show

It does not show that ScientistTwo's reported gains are wrong or that the loop could not reach them: ScientistTwo's numbers are self-reported ranges in generated
papers, on its own choice of in-sample rows and (for the credal problem) a different benchmark, and its own held-out figures are much worse than its headline. It
does not show a cost ratio, because the other side's cost is not published. It shows that, with one run per problem, a three-idea loop at about ten cents of model
spend did not improve either parent's baseline on this project's harness, that it reproduced both baselines, and that its audit and write-up said so plainly.
The comparison is not a fair test of ideas: each side chose different ideas on different data subsets; a negative result from two or three ideas per run is weak
evidence about a method class.
