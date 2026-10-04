"""The true Hoeffding functional decomposition (HFD) of the TreeHFD paper's analytical function, in closed form.

m(X) = sin(2 pi X1) + X1 X2 + X3 X4, X ~ N(0, S) in R^6 with unit variances and all pairwise correlations rho.

The HFD (paper Section 2; hierarchical orthogonality) is the unique sum of components, one per variable subset J, with
E[eta_J(X_J) | X_K] = 0 for every proper subset K of J. It is linear in m, so:

- sin(2 pi X1) is additive and sums to zero, so it is entirely the main effect of X1;
- X1 X2 + X3 X4 is a polynomial of degree 2, and the HFD of a polynomial of degree 2 has components that are
  polynomials of degree at most 2 in their own variables. They are found exactly by solving a small linear system:
  unknown coefficients, hierarchical-orthogonality conditions (conditional expectations of a polynomial under a Gaussian
  are polynomials in the conditioning variable), and the identity "components sum to the polynomial".

`true_components(rho)` solves it for any rho (nothing is read from the paper); `TABLE_3` holds the paper's Table 3
formulas for the HFD column, and `table3_check` compares the two. Pure numpy, no model fitted, used by the harness
inside the sandbox and by the tests.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np

DIM = 6
PAIRS = list(combinations(range(DIM), 2))


def _layout() -> tuple[dict, int]:
    """Index of every unknown: eta0; main effect j: (d0, d1, d2) for 1, x, x^2; pair (a, b): c0..c5 for
    1, xa, xb, xa^2, xb^2, xa*xb."""
    idx, n = {"eta0": 0}, 1
    for j in range(DIM):
        idx[(j,)] = n
        n += 3
    for p in PAIRS:
        idx[p] = n
        n += 6
    return idx, n


def solve(rho: float) -> dict:
    """Coefficients of the HFD of X1 X2 + X3 X4 as {'eta0': float, (j,): [d0, d1, d2], (a, b): [c0..c5]}."""
    idx, n = _layout()
    s = 1.0 - rho**2
    rows, rhs = [], []

    def add(terms: dict[int, float], value: float = 0.0) -> None:
        r = np.zeros(n)
        for k, v in terms.items():
            r[k] += v
        rows.append(r)
        rhs.append(value)

    for j in range(DIM):  # E eta_j = 0
        o = idx[(j,)]
        add({o: 1.0, o + 2: 1.0})
    for p in PAIRS:  # E[eta_ab | x_a] = 0, E[eta_ab | x_b] = 0, E eta_ab = 0
        o = idx[p]
        add({o: 1.0, o + 4: s})
        add({o + 1: 1.0, o + 2: rho})
        add({o + 3: 1.0, o + 4: rho**2, o + 5: rho})
        add({o: 1.0, o + 3: s})
        add({o + 2: 1.0, o + 1: rho})
        add({o + 4: 1.0, o + 3: rho**2, o + 5: rho})
        add({o: 1.0, o + 3: 1.0, o + 4: 1.0, o + 5: rho})
    # components sum to P = x1 x2 + x3 x4, monomial by monomial
    target = {(0, 1): 1.0, (2, 3): 1.0}
    const = {0: 1.0}
    for j in range(DIM):
        const[idx[(j,)]] = 1.0
    for p in PAIRS:
        const[idx[p]] = 1.0
    add(const, 0.0)  # constant term of the sum
    for j in range(DIM):
        lin = {idx[(j,)] + 1: 1.0}
        sq = {idx[(j,)] + 2: 1.0}
        for a, b in PAIRS:
            if j == a:
                lin[idx[(a, b)] + 1] = 1.0
                sq[idx[(a, b)] + 3] = 1.0
            elif j == b:
                lin[idx[(a, b)] + 2] = 1.0
                sq[idx[(a, b)] + 4] = 1.0
        add(lin, 0.0)
        add(sq, 0.0)
    for p in PAIRS:
        add({idx[p] + 5: 1.0}, target.get(p, 0.0))
    a_mat, b_vec = np.array(rows), np.array(rhs)
    sol, *_ = np.linalg.lstsq(a_mat, b_vec, rcond=None)
    if np.linalg.matrix_rank(a_mat) != n or not np.allclose(a_mat @ sol, b_vec, atol=1e-10):
        raise RuntimeError("the HFD system has no unique exact solution")  # pragma: no cover
    out = {"eta0": float(sol[0])}
    for j in range(DIM):
        out[(j,)] = sol[idx[(j,)] : idx[(j,)] + 3].tolist()
    for p in PAIRS:
        out[p] = sol[idx[p] : idx[p] + 6].tolist()
    return out


def true_components(rho: float, X: np.ndarray) -> tuple[float, dict[tuple[int, ...], np.ndarray]]:
    """(eta0, {J: eta_J(X_J) on the rows of X}) for the analytical function at pairwise correlation rho. Every
    main effect and pair is present (zeros included); no component of higher order exists."""
    c = solve(rho)
    comps: dict[tuple[int, ...], np.ndarray] = {}
    for j in range(DIM):
        d = c[(j,)]
        comps[(j,)] = d[0] + d[1] * X[:, j] + d[2] * X[:, j] ** 2
    comps[(0,)] = comps[(0,)] + np.sin(2 * np.pi * X[:, 0])
    for a, b in PAIRS:
        k = c[(a, b)]
        xa, xb = X[:, a], X[:, b]
        comps[(a, b)] = k[0] + k[1] * xa + k[2] * xb + k[3] * xa**2 + k[4] * xb**2 + k[5] * xa * xb
    return c["eta0"], comps


# The paper's Table 3, HFD column (S-Mat B.2), as functions of rho; None marks components the table lists as 0.
def _table3(rho: float) -> tuple[float, dict]:
    q = rho / (1 + rho**2)
    main = lambda x: q * (x**2 - 1)  # noqa: E731
    comps = {
        (0,): lambda X: np.sin(2 * np.pi * X[:, 0]) + main(X[:, 0]),
        (1,): lambda X: main(X[:, 1]),
        (2,): lambda X: main(X[:, 2]),
        (3,): lambda X: main(X[:, 3]),
    }
    for a, b in ((0, 1), (2, 3)):
        const = rho * (1 - rho**2) / (1 + rho**2)
        comps[(a, b)] = lambda X, a=a, b=b, c=const: c - q * (X[:, a] ** 2 + X[:, b] ** 2) + X[:, a] * X[:, b]
    return 2 * rho, comps


def table3_check(rho: float, n: int = 4000, seed: int = 0) -> dict:
    """Relative difference between the solved components and the paper's Table 3 formulas on a Gaussian sample:
    per component max|difference| / max|table value|, the largest over the listed components, and the largest
    absolute value of any component the table lists as 0 (variables 5 and 6, all other pairs)."""
    rng = np.random.default_rng(seed)
    cov = np.full((DIM, DIM), rho)
    np.fill_diagonal(cov, 1.0)
    X = rng.multivariate_normal(np.zeros(DIM), cov, size=n)
    eta0, mine = true_components(rho, X)
    t0, table = _table3(rho)
    worst = abs(eta0 - t0) / max(abs(t0), 1e-12) if t0 else abs(eta0)
    for k, f in table.items():
        ref = f(X)
        worst = max(worst, float(np.abs(mine[k] - ref).max() / max(float(np.abs(ref).max()), 1e-9)))
    zeros = max((float(np.abs(v).max()) for k, v in mine.items() if k not in table), default=0.0)
    return {"rho": rho, "max_relative_difference": worst, "max_abs_of_components_listed_as_zero": zeros}
