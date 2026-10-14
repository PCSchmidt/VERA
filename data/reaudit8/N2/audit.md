# Audit of rlm-vs-clm-2 (paper): **RED**

Checks run: citation, claim_support, inference, sentence. Claims checked: 65. Findings: 3 fail, 0 warn, 0 info. Judge cost $0.00100.

- **fail** (inference) I2 (Discussion): does not follow from its premises: 'The motivation is consistent across sources: serving is shifting toward long-context applications, prefill cost grows rapidly with input len'
  - evidence: log `paper/inferences.jsonl` matched=False
- **fail** (sentence) S4 (Introduction, claim): C3 says more than its quote: "R7 adds that a transformer's KV representation of a token is a function of its entire prefix, so exact reuse is confined to contexts that sh"
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S76 (Unestablished questions and the scope of a CPU-scale companion experiment, claim): C51 says more than its quote: 'The Prompt Cache authors report TTFT reductions of 20× to 70× for CPU inference on LongBench.'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 11 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 65 (51 claim, 3 synthesis, 11 transition); 2 failed and 0 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
