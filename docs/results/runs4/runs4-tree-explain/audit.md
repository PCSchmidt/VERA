# Audit of runs4-tree-explain: **AMBER**

Checks run: citation, numeric, figure, reproduction_basis, method_code, novelty. Claims checked: 152. Findings: 0 fail, 15 warn, 0 info. Judge cost $0.00236.

- **warn** (numeric) Could not confirm the comparison against the table: 'The TreeHFD paper states that the Hoeffding decomposition breaks black-box models into a unique sum of lower-dimensional functions, provided the inputs are inde'
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (numeric) Could not confirm the comparison against the table: 'Since nothing beat the baseline, no ablation was run.'
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (numeric) Every number exists in results.json, but the judge could not confirm the claim: "In Figure 2, its rank stability is lower than TreeHFD's at every Analytical rho and on Airfoil (0.979 vs 0.987)."
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (numeric) Every number exists in results.json, but the judge could not confirm the claim: 'Addressed from the research question: on simulated Analytical data with a known decomposition, component error against the truth and bootstrap rank stability as'
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (method_code) The paper says: 'The aim was to reduce overfitting while keeping each component a function of its own variables only.', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Three ideas were generated; only C2 was run on the subset.', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Ideas were produced and implemented by a language model.', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Registered protocol (written down, dated and hashed before any run): methods TreeHFD, TreeSHAP and C2; Analytical at six rho values and Airfoil; 3 seeds with 5 ', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: "Component error compares components with the true decomposition of the analytical function, which has a closed form checked against the TreeHFD paper's Table 3.", and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Airfoil has no true components.', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Rank stability is the mean Spearman correlation of component importances between bootstrap refits.', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: "TreeSHAP is xgboost's path-dependent TreeSHAP with interaction values.", and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'No cells were invalid.', and the code of C2: Shallower variable selection depth does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The code of C2: Shallower variable selection depth has a function '_residual_mse' that the paper does not describe.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The code of C2: Shallower variable selection depth has a function '_fit_predict' that the paper does not describe.
  - evidence: repo `method.py` matched=False

Skipped checks:
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
