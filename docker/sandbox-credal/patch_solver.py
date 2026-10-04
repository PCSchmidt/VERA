# ruff: noqa: E501
"""Replace the commercial MOSEK solver by the open one, Clarabel, in a local clone of the credal-ambiguity-sets repository.

Why: the repository's baselines name `cp.MOSEK` / "MOSEK" in about twenty places, and a MOSEK licence is tied to a person, so
it cannot be baked into an image. Clarabel is an open conic solver cvxpy supports. This is a documented modification of
the parent's code (docs/results/problem2_feasibility.md, option (a), accepted by Chris 2026-10-04): values and times can
differ slightly from the paper's MOSEK runs, which is why the reproduction tolerance is registered before any run.

Usage: python patch_solver.py <clone dir>   (run at image build time; prints how many substitutions it made)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
total = 0
for path in sorted((root / "credal_dro").glob("*.py")):
    text = path.read_text(encoding="utf-8")
    new, n1 = re.subn(r"cp\.MOSEK\b", "cp.CLARABEL", text)
    new, n2 = re.subn(r'"MOSEK"', '"CLARABEL"', new)
    new = new.replace('preferred_solvers = ["CLARABEL", "GUROBI", "ECOS", "OSQP", "SCS"]', 'preferred_solvers = ["CLARABEL", "SCS"]')
    if new != text:
        path.write_text(new, encoding="utf-8")
        print(f"{path.name}: {n1 + n2} substitutions")
        total += n1 + n2
print(f"total {total}")
