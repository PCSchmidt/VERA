# Second parent problem: feasibility of credal ambiguity sets (2026-10-03)

Parent: Chen et al., "Bulk-Calibrated Credal Ambiguity Sets: Fast, Tractable Decision Making under Out-of-Sample
Contamination", arXiv 2601.21324. Code: `MengqiChenMC/credal-ambiguity-sets-code-repo`, commit
`506c17fc28e87619e4532afeff8389083e578557` (main, pushed 2026-05-13). No model calls were made for this note.

## What runs on a CPU, and how long

From the paper's own text (appendix, experiments):

- **Student-t newsvendor (Section 5.1; Figure 3, Table 2).** "CPU nodes ... AMD EPYC (64 cores / 128 threads) and 384 GB RAM.
  Unless stated otherwise, each run used a single CPU core (one thread) and 10 GB of memory." Table 2, seconds per
  replication (mean, SD over 100 replications): LV (the paper's method) 1.3 total (1.0 sampling, 0.3 solve), KL-BASPP 3.6,
  KL-BDRO 2.4; the other baselines are in the same range. Three runs (test contamination 0%, 10%, 20%) of 100 replications each:
  minutes per method on one core.
- **California Housing East to West shift (Section 5.2; Tables 3, 4).** Table 4, seconds per replication: LV 1.44 total, CVaR
  5.47, Wasserstein 6.16 (the cross-validation dominates the baselines). 100 replications.
- **CivilComments (WILDS)**: "GPU nodes ... 4x NVIDIA GPUs (48 GB)", model training about 90% of the time. Not CPU-scale: out.
- Two appendix items run for hours (the SAA convergence diagnostic): out.

So two CPU-scale experiments exist, both with a registered-able primary result (the out-of-sample mean and SD in Figure 3 and
Table 3, and the runtimes). Compute is not the blocker the Increment 0 review feared.

## What blocks a run today

Tested in a clean `python:3.11-slim` container (`pip install -e .` from the repository, then `credaldro setup-lv
lv_newsvendor_student_t ...` and `credaldro batch ... 0 3`, with the replications set to 2):

1. **The install works** (about 4 minutes: cvxpy 1.9.3, gurobipy 13.0.3, Mosek 11.2.5, jax, dro 0.3.3, Clarabel 0.11.1 present;
   `cvxpy.installed_solvers()` lists MOSEK, CLARABEL, SCS, GUROBI, SCIPY, HIGHS, OSQP) and the experiment configs are written.
2. **The first run fails: `rescode.err_missing_license_file(1008): License cannot be located.`** The baselines name
   `cp.MOSEK` or `"MOSEK"` in about twenty places in `credal_dro/main.py`; the LV method's own solver call prefers
   `["MOSEK", "GUROBI", "ECOS", "OSQP", "SCS"]` and would fall back. MOSEK is commercial: free for academics, a 30-day trial for
   anyone, and a licence file is tied to the person who requests it (it cannot be committed or shared).
3. **The repository has no licence** (`license: null` on GitHub; `pyproject.toml` says BSD-3-Clause, the repository has no LICENSE
   file). Reading and running it locally for a reproduction is ordinary research use; copying it into this repository or an image
   others pull is not clearly permitted. The sandbox image would be built locally from a clone and not committed.
4. `gurobipy`'s bundled licence is size-limited; it may or may not cover the newsvendor problems (untested).

## Options

- **(a) Substitute the solver in the harness.** At image-build time, patch `cp.MOSEK` and `"MOSEK"` to `CLARABEL` (an open
  conic solver cvxpy supports) in a local clone, and register the reproduction tolerance knowing times and values will differ
  slightly from the paper's MOSEK runs. A documented modification of the parent code; this is also exactly the kind of adapter
  T10's option (c) would have a model write, so the two harness variants can be compared on it.
- **(b) Get a MOSEK licence** (a trial or academic licence, requested by Chris under his own name, mounted into the sandbox, never
  committed). Closest to the paper; an outward-facing step that is Chris's to take.
- **(c) Pick another problem.** The inventory flags only TreeHFD, STELLA (single GPU) and this one for the loop.

**Recommendation: (a)**, starting with the newsvendor experiment; if Clarabel results fall outside a tolerance registered from the
paper's Table 2 and Figure 3 before any run, say so and ask Chris for (b). The decision is Chris's, and so is the question of
whether running an unlicensed repository locally is acceptable to him.
