# Tree-explain protocol: results (tree-explain-1)

Registered 2026-10-04T13:13:35Z (target sha256 `3ba3df6662a2`), image `vera-sandbox-treehfd:dd02152`. No value here is a figure from ScientistTwo's paper.

Cells re-run after a harness bug fix (TreeSHAP's component keys assumed six variables, so its Airfoil run was invalid) replace the first run's: treehfd on airfoil (from protocol_tree-explain-1-airfoil.json); treeshap on airfoil (from protocol_tree-explain-1-airfoil.json).

Mean ± std over 3 seeds; stability from 5 bootstrap refits each.

**Component error against the true decomposition (% of signal variance)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ |
|---|---|---|---|---|---|---|
| TreeHFD | 8.52 ± 0.23 | 7.15 ± 0.35 | 5.99 ± 0.21 | 3.93 ± 0.22 | 3.05 ± 0.23 | 2.99 ± 0.27 |
| TreeSHAP | 7.94 ± 0.40 | 20.4 ± 0.56 | 34.0 ± 2.8 | 29.9 ± 0.44 | 27.1 ± 2.9 | 28.2 ± 2.1 |

**Rank stability of component importances across bootstrap refits (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ | Airfoil ↑ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 0.867 ± 0.037 | 0.948 ± 0.017 | 0.937 ± 0.010 | 0.936 ± 0.018 | 0.866 ± 0.019 | 0.800 ± 0.052 | 0.987 ± 0.0024 |
| TreeSHAP | 0.877 ± 0.022 | 0.923 ± 0.0018 | 0.913 ± 0.00032 | 0.907 ± 0.019 | 0.914 ± 0.0081 | 0.872 ± 0.012 | 0.988 ± 0.0037 |

**Rank agreement of component importances with the true ones (Spearman)** (↑: higher is better)

| Method | Analytical, rho 0 ↑ | Analytical, rho 0.25 ↑ | Analytical, rho 0.5 ↑ | Analytical, rho 0.75 ↑ | Analytical, rho 0.9 ↑ | Analytical, rho 0.95 ↑ |
|---|---|---|---|---|---|---|
| TreeHFD | 0.397 ± 0.051 | 0.881 ± 0.0071 | 0.639 ± 0.034 | 0.636 ± 0.010 | 0.684 ± 0.074 | 0.699 ± 0.072 |
| TreeSHAP | 0.415 ± 0.033 | 0.869 ± 0.034 | 0.643 ± 0.017 | 0.778 ± 0.039 | 0.682 ± 0.030 | 0.712 ± 0.043 |

**Residual MSE against the fitted ensemble (%)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 5.54 ± 0.40 | 3.80 ± 0.52 | 2.79 ± 0.32 | 1.66 ± 0.084 | 1.11 ± 0.19 | 1.03 ± 0.022 | 4.73 ± 0.11 |
| TreeSHAP | 0.0000000000556 ± 0.0000000000055 | 0.0000000000608 ± 0.0000000000052 | 0.0000000000523 ± 0.0000000000088 | 0.0000000000418 ± 0.0000000000098 | 0.0000000000495 ± 0.0000000000012 | 0.0000000000620 ± 0.000000000015 | 0.00000000265 ± 0.00000000023 |

**Runtime of the decomposition call (s)** (↓: lower is better)

| Method | Analytical, rho 0 ↓ | Analytical, rho 0.25 ↓ | Analytical, rho 0.5 ↓ | Analytical, rho 0.75 ↓ | Analytical, rho 0.9 ↓ | Analytical, rho 0.95 ↓ | Airfoil ↓ |
|---|---|---|---|---|---|---|---|
| TreeHFD | 35.4 ± 0.81 | 34.6 ± 1.5 | 32.5 ± 1.3 | 29.7 ± 0.85 | 26.7 ± 0.29 | 25.0 ± 1.0 | 2.83 ± 0.12 |
| TreeSHAP | 2.46 ± 0.16 | 2.62 ± 0.074 | 2.17 ± 0.35 | 2.65 ± 0.20 | 2.37 ± 0.20 | 2.56 ± 0.31 | 0.164 ± 0.016 |

## The expectations written down before any run

- **E1: did NOT hold.** E1: TreeHFD's component_mse_pct is below TreeSHAP's at every analytical correlation (the paper's claim that TreeHFD targets the HFD and TreeSHAP a different decomposition). Failed if TreeSHAP is lower at any rho.
  - 0: TreeHFD 8.52 vs TreeSHAP 7.94; 0.25: TreeHFD 7.15 vs TreeSHAP 20.4; 0.5: TreeHFD 5.99 vs TreeSHAP 34; 0.75: TreeHFD 3.93 vs TreeSHAP 29.9; 0.9: TreeHFD 3.05 vs TreeSHAP 27.1; 0.95: TreeHFD 2.99 vs TreeSHAP 28.2
- **E2 (TreeHFD): did NOT hold.** E2: both methods' component_mse_pct rises with rho (the dependence makes the targets harder to separate). Failed if the value at 0.95 is not above the value at 0.
  - rho 0: 8.520737924788497; rho 0.95: 2.9942712624216425
- **E2 (TreeSHAP): held.** E2: both methods' component_mse_pct rises with rho (the dependence makes the targets harder to separate). Failed if the value at 0.95 is not above the value at 0.
  - rho 0: 7.93667529066292; rho 0.95: 28.221505545502065
- **E3: did NOT hold.** E3: TreeHFD's rank_stability is at least 0.8 at every rho. Failed if any is below.
  - 0: 0.867; 0.25: 0.948; 0.5: 0.937; 0.75: 0.936; 0.9: 0.866; 0.95: 0.8
- **E4: held.** E4: TreeSHAP's decomposition fails the own-variables-only check (its attributions depend on the whole row). Failed if it passes.
  - TreeSHAP own_variables_only: analytical@0=False, analytical@0.25=False, analytical@0.5=False, analytical@0.75=False, analytical@0.9=False, analytical@0.95=False, airfoil=False
