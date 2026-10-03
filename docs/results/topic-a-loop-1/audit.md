# Audit of topic-a-loop-1: **AMBER**

Checks run: citation, numeric. Claims checked: 27. Findings: 0 fail, 1 warn, 0 info. Judge cost $0.00015.

- **warn** (numeric) 0.95 in the text is not a value in results.json (nor a difference or ratio of two): 'They do not vary pairwise correlation from 0 to 0.95, do not compare against TreeSHAP, do not measure error against ground-truth components, do not test bootstr'
  - evidence: log `results.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6
