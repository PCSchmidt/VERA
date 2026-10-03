# Audit of topic-a-loop-2: **RED**

Checks run: citation, numeric. Claims checked: 43. Findings: 14 fail, 1 warn, 0 info. Judge cost $0.00037.

- **fail** (numeric) The table row 'TreeHFD (baseline)' / analytical rho0 / residual_mse_pct has no counterpart in results.json or is not 'mean ± std': '5.54 ± 0.40'.
  - evidence: log `results.json:TreeHFD (baseline)/analytical rho0/residual_mse_pct` matched=False
- **fail** (numeric) The table row 'TreeHFD (baseline)' / analytical rho0 / runtime_s has no counterpart in results.json or is not 'mean ± std': '30.1 ± 1.2'.
  - evidence: log `results.json:TreeHFD (baseline)/analytical rho0/runtime_s` matched=False
- **fail** (numeric) The table row 'TreeHFD (baseline)' / analytical rho95 / residual_mse_pct has no counterpart in results.json or is not 'mean ± std': '1.03 ± 0.022'.
  - evidence: log `results.json:TreeHFD (baseline)/analytical rho95/residual_mse_pct` matched=False
- **fail** (numeric) The table row 'TreeHFD (baseline)' / analytical rho95 / runtime_s has no counterpart in results.json or is not 'mean ± std': '22.0 ± 0.42'.
  - evidence: log `results.json:TreeHFD (baseline)/analytical rho95/runtime_s` matched=False
- **fail** (numeric) The table row 'C3: Residual ridge recalibration' / analytical rho0 / residual_mse_pct has no counterpart in results.json or is not 'mean ± std': '5.69 ± 0.37'.
  - evidence: log `results.json:C3: Residual ridge recalibration/analytical rho0/residual_mse_pct` matched=False
- **fail** (numeric) The table row 'C3: Residual ridge recalibration' / analytical rho0 / runtime_s has no counterpart in results.json or is not 'mean ± std': '34.7 ± 1.1'.
  - evidence: log `results.json:C3: Residual ridge recalibration/analytical rho0/runtime_s` matched=False
- **fail** (numeric) The table row 'C3: Residual ridge recalibration' / analytical rho95 / residual_mse_pct has no counterpart in results.json or is not 'mean ± std': '1.04 ± 0.037'.
  - evidence: log `results.json:C3: Residual ridge recalibration/analytical rho95/residual_mse_pct` matched=False
- **fail** (numeric) The table row 'C3: Residual ridge recalibration' / analytical rho95 / runtime_s has no counterpart in results.json or is not 'mean ± std': '24.9 ± 0.43'.
  - evidence: log `results.json:C3: Residual ridge recalibration/analytical rho95/runtime_s` matched=False
- **fail** (numeric) The table row 'C1: Shallow depth_variable sweep' / analytical rho0 / residual_mse_pct has no counterpart in results.json or is not 'mean ± std': '4.37 ± 0.52'.
  - evidence: log `results.json:C1: Shallow depth_variable sweep/analytical rho0/residual_mse_pct` matched=False
- **fail** (numeric) The table row 'C1: Shallow depth_variable sweep' / analytical rho0 / runtime_s has no counterpart in results.json or is not 'mean ± std': '16.7 ± 4.1'.
  - evidence: log `results.json:C1: Shallow depth_variable sweep/analytical rho0/runtime_s` matched=False
- **fail** (numeric) The table row 'C1: Shallow depth_variable sweep' / analytical rho95 / residual_mse_pct has no counterpart in results.json or is not 'mean ± std': '0.712 ± 0.044'.
  - evidence: log `results.json:C1: Shallow depth_variable sweep/analytical rho95/residual_mse_pct` matched=False
- **fail** (numeric) The table row 'C1: Shallow depth_variable sweep' / analytical rho95 / runtime_s has no counterpart in results.json or is not 'mean ± std': '20.1 ± 0.11'.
  - evidence: log `results.json:C1: Shallow depth_variable sweep/analytical rho95/runtime_s` matched=False
- **warn** (numeric) 5000, 0.95 in the text is not a value in results.json (nor a difference or ratio of two): 'Datasets: Analytical, Analytical rho0 (independent inputs, pairwise correlation 0, same function, noise, n = 5000 and model as Analytical), Analytical rho95 (pa'
  - evidence: log `results.json` matched=False
- **fail** (numeric) A real number on the wrong method or dataset: 4.37 is a value of C1: Shallow depth_variable sweep / analytical_rho0; 5.54 is a value of TreeHFD (baseline) / analytical_rho0; 0.712 is a value of C1: Shallow depth_variable sweep / analytical_rho95; 1.03 is a value of TreeHFD (baseline) / analytical_rho95, not of the cell this sentence names: 'C1 lowered residual MSE on Analytical (2.41 vs 2.79), rho0 (4.37 vs 5.54) and rho95 (0.712 vs 1.03), and lowered runtime on those three.'
  - evidence: log `results.json` matched=False
- **fail** (numeric) 0.95 in a results claim is not a value in results.json (nor a difference or ratio of two): 'The Analytical rho0 and rho95 datasets give two points on the correlation axis (0 and 0.95), but not a sweep, and the metric is residual MSE of the decompositio'
  - evidence: log `results.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
