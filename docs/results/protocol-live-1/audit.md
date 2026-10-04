# Audit of protocol-live-1: **AMBER**

Checks run: citation, numeric, figure. Claims checked: 134. Findings: 0 fail, 3 warn, 0 info. Judge cost $0.00156.

- **warn** (numeric) Could not confirm the comparison against the table: 'We tried to improve TreeHFD, a method that decomposes an xgboost model into main effects and second-order interactions.'
  - evidence: log `results.json (rendered table)` matched=None
- **warn** (numeric) 0.570, 1.52 in the text is not a value in results.json (nor a difference or ratio of two): "The reproduction used the paper's in-sample convention on both datasets: residual MSE was 0.570 on Analytical and 1.52 on Airfoil."
  - evidence: log `results.json` matched=False
- **warn** (numeric) Could not confirm against the table (the judge was not confident): 'Relative to the research question, these experiments address component error against known components and bootstrap rank stability across rho 0 to 0.95, on an a'
  - evidence: log `results.json (rendered table)` matched=None

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
