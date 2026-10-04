# Sandbox image for the credal-ambiguity-sets loop (docs/04 T10, Increment 4). Build context: a clone of
#   https://github.com/MengqiChenMC/credal-ambiguity-sets-code-repo  at commit 506c17fc28e87619e4532afeff8389083e578557
# placed in ./repo (git-ignored: the repository has no licence file, so it is never committed here), plus this directory's
# files, then:   cp docker/sandbox-credal/* data/cache/credal/ && docker build -t vera-sandbox-credal:506c17f data/cache/credal
# Three documented deviations from the parent's own environment (docs/results/problem2_baseline.md):
#   1. MOSEK (a licence tied to a person) is replaced by the open solver Clarabel, and the MOSEK-only solve options the
#      parent passes are dropped (patch_solver.py);
#   2. numpy < 2.3, because the parent's `np.sum(<generator>)` raises in numpy 2.4;
#   3. cvxpy < 1.8, because the parent reads `cp.settings.PARAM_THRESHOLD`, which cvxpy 1.8 and later no longer have.
# The repository pins none of these (`numpy>=1.26.2`, `cvxpy>=1.4.2`).
FROM python:3.11-slim
COPY repo /opt/credal
RUN pip install --no-cache-dir /opt/credal && pip install --no-cache-dir "numpy<2.3" "cvxpy<1.8" && useradd -m -u 1000 sandbox
# the package does not install its SLURM template, which `setup-lv` reads next to main.py
RUN cp /opt/credal/credal_dro/*.slurm "$(python -c 'import credal_dro, os; print(os.path.dirname(credal_dro.__file__))')/"
COPY patch_solver.py /opt/patch_solver.py
RUN python /opt/patch_solver.py "$(python -c 'import credal_dro, os; print(os.path.dirname(os.path.dirname(credal_dro.__file__)))')"
USER sandbox
WORKDIR /work
