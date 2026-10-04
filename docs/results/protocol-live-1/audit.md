# Audit of protocol-live-1: **AMBER**

Checks run: citation, numeric. Claims checked: 131. Findings: 0 fail, 5 warn, 0 info. Judge cost $0.00155.

- **warn** (numeric) Could not confirm the comparison against the table: 'We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions.'
  - evidence: log `results.json (rendered table)` matched=None
- **warn** (numeric) Could not confirm the comparison against the table: 'A language-model-driven loop generated 3 ideas and ran 1 of them on a subset: C2, deeper variable selection (a higher depth_variable).'
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (numeric) Could not confirm the comparison against the table: 'In the registered protocol on correlated analytical data, TreeHFD recovered the true components far better than TreeSHAP at moderate to high correlation.'
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (numeric) 0.570, 1.52 in the text is not a value in results.json (nor a difference or ratio of two): "Baseline in-sample residual MSE (the paper's convention) was 0.570% on Analytical and 1.52% on Airfoil; the results table reports held-out values, which are hig"
  - evidence: log `results.json` matched=False
- **warn** (numeric) Every number exists in results.json, but the judge could not confirm the claim: 'Question coverage: the experiments address the analytical-data part of the research question for xgboost only: component error against true components and boots'
  - evidence: log `results.json (rendered table)` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
