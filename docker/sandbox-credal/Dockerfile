# Sandbox image for the credal-ambiguity-sets loop (docs/04 T10, Increment 4). Build context: a clone of
#   https://github.com/MengqiChenMC/credal-ambiguity-sets-code-repo  at commit 506c17fc28e87619e4532afeff8389083e578557
# placed in ./repo (git-ignored: the repository has no licence file, so it is never committed here), plus this directory's
# files, then:   cp docker/sandbox-credal/* data/cache/credal/ && docker build -t vera-sandbox-credal:506c17f data/cache/credal
# MOSEK is replaced by Clarabel (patch_solver.py): see its docstring.
FROM python:3.11-slim
COPY repo /opt/credal
COPY patch_solver.py /opt/patch_solver.py
RUN python /opt/patch_solver.py /opt/credal \
    && pip install --no-cache-dir /opt/credal \
    && useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /work
