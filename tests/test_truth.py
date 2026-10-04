"""The closed-form HFD of the TreeHFD analytical case reproduces the paper's Table 3 before any method is scored."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docker" / "sandbox-treehfd"))
import truth  # noqa: E402


@pytest.mark.parametrize("rho", [0.0, 0.25, 0.5, 0.75, 0.9, 0.95])
def test_the_solved_hfd_matches_the_papers_table_3_within_one_percent(rho: float) -> None:
    r = truth.table3_check(rho)
    assert r["max_relative_difference"] < 0.01
    assert r["max_abs_of_components_listed_as_zero"] < 1e-9


def test_the_true_components_sum_to_the_function_and_satisfy_hierarchical_orthogonality() -> None:
    rho = 0.5
    rng = np.random.default_rng(1)
    cov = np.full((6, 6), rho)
    np.fill_diagonal(cov, 1.0)
    X = rng.multivariate_normal(np.zeros(6), cov, size=200_000)
    eta0, comps = truth.true_components(rho, X)
    m = np.sin(2 * np.pi * X[:, 0]) + X[:, 0] * X[:, 1] + X[:, 2] * X[:, 3]
    assert np.allclose(eta0 + sum(comps.values()), m, atol=1e-9)
    assert abs(float(comps[(0, 1)].mean())) < 0.01  # centred
    # E[eta_12 | x1] = 0: the pair is orthogonal to every function of x1 alone
    assert abs(float(np.mean(comps[(0, 1)] * (X[:, 0] ** 2 - 1)))) < 0.02
    assert abs(float(np.mean(comps[(0, 1)] * X[:, 1]))) < 0.02
