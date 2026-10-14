# Audit of discuss-the-evolution-of-prompting-guv8 (paper): **AMBER**

Checks run: citation, claim_support, inference, sentence. Claims checked: 71. Findings: 0 fail, 2 warn, 0 info. Judge cost $0.00097.

- **warn** (inference) I8 (Discussion): judge_unsure: 'Several sources agree that the surrounding execution system matters for measured results: changing it around a fixed model can alter perform'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on jev at 0.72; the reference judge says yes, yes on sonnet-ref at 0.88): S3 (Introduction, claim): C3 says more than its quote: 'The authors of R2 report that prompt engineering is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical f'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 18 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 65 (51 claim, 6 synthesis, 8 transition); 1 failed and 0 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Judge disagreements: 1 (a sentence or statement that passed a judge question when it was written failed the same question in the audit; reported as warnings, not failures).
