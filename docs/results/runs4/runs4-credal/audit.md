# Audit of runs4-credal: **AMBER**

Checks run: citation, numeric, figure, reproduction_basis, method_code, novelty. Claims checked: 52. Findings: 0 fail, 14 warn, 0 info. Judge cost $0.00099.

- **warn** (numeric) Could not confirm the comparison against the table: 'We tried to improve LV, a bulk-calibrated credal-ambiguity-set method for robust linear regression, on California Housing under an East-to-West geographic shift'
  - evidence: log `results.json (rendered table)` matched=False
- **warn** (numeric) 50, 30 in the text is not a value in results.json (nor a difference or ratio of two): 'Data: California Housing, trained on the Eastern 50% and tested on the Western 20%, with a 30% gap between them.'
  - evidence: log `results.json` matched=False
- **warn** (numeric) 0.5 in the text is not a value in results.json (nor a difference or ratio of two): '**C2, Huber-quantile hybrid loss.** The absolute loss is replaced by a Huberized quantile loss at tau=0.5.'
  - evidence: log `results.json` matched=False
- **warn** (numeric) 200 in the text is not a value in results.json (nor a difference or ratio of two): 'Relation to the research question: that question concerns credal, Wasserstein and mean-covariance ambiguity sets under a common tuning rule, with sample sizes o'
  - evidence: log `results.json` matched=False
- **warn** (method_code) The paper says: 'Ideas: three were generated and two were run on the subset.', and the code of C1: Covariate-shift importance reweighting does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: '**C2, Huber-quantile hybrid loss.** The absolute loss is replaced by a Huberized quantile loss at tau=0.5.', and the code of C1: Covariate-shift importance reweighting does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'It is quadratic for small residuals and linear beyond a cross-validated threshold, and is solved by scipy least_squares or IRLS.', and the code of C1: Covariate-shift importance reweighting does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The code of C1: Covariate-shift importance reweighting has a function 'fit_predict' that the paper does not describe.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Ideas: three were generated and two were run on the subset.', and the code of C2: Huber-quantile hybrid loss does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: '**C1, covariate-shift importance reweighting.** A logistic classifier (sklearn) separates eastern training rows from western unlabeled test covariates.', and the code of C2: Huber-quantile hybrid loss does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: 'Its predicted odds serve as density-ratio weights, clipped to a robust cap, in the absolute-loss fit.', and the code of C2: Huber-quantile hybrid loss does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The paper says: '**C2, Huber-quantile hybrid loss.** The absolute loss is replaced by a Huberized quantile loss at tau=0.5.', and the code of C2: Huber-quantile hybrid loss does not do it.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The code of C2: Huber-quantile hybrid loss has a function '_design' that the paper does not describe.
  - evidence: repo `method.py` matched=False
- **warn** (method_code) The code of C2: Huber-quantile hybrid loss has a function 'fit_predict' that the paper does not describe.
  - evidence: repo `method.py` matched=False

Skipped checks:
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
