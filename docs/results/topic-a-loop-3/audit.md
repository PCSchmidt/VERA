# Audit of topic-a-loop-3: **AMBER**

Checks run: citation, numeric. Claims checked: 42. Findings: 0 fail, 4 warn, 0 info. Judge cost $0.00046.

- **warn** (numeric) 5000 in the text is not a value in results.json (nor a difference or ratio of two): 'Uncorrelated: the analytical function with independent inputs (pairwise correlation 0), same noise, n = 5000 and model.'
  - evidence: log `results.json` matched=False
- **warn** (numeric) 0.95, 5000 in the text is not a value in results.json (nor a difference or ratio of two): 'Correlated95: the analytical function with pairwise correlation 0.95 between all six Gaussian inputs, same noise, n = 5000 and model.'
  - evidence: log `results.json` matched=False
- **warn** (numeric) 0.95 in the text is not a value in results.json (nor a difference or ratio of two): 'Relation to the literature research question: the Uncorrelated and Correlated95 datasets give two correlation levels (0 and 0.95), not a sweep.'
  - evidence: log `results.json` matched=False
- **warn** (numeric) Could not confirm the comparison against the table: 'They bear on the question only by showing that two post-hoc corrections do not reduce residual error at either correlation level.'
  - evidence: log `results.json (rendered table)` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
