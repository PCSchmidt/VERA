# Audit of discuss-the-evolution-of-prompting-guv8 (paper): **RED**

Checks run: citation, claim_support, inference, sentence. Claims checked: 71. Findings: 2 fail, 0 warn, 0 info. Judge cost $0.00098.

- **fail** (inference) I8 (Discussion): does not follow from its premises: 'Several sources agree that the surrounding execution system matters for measured results: changing it around a fixed model can alter perform'
  - evidence: log `paper/inferences.jsonl` matched=False
- **fail** (sentence) S2 (Introduction, claim): C2 says more than its quote: 'The abstract of R11 states that prompts are also a form of programming that can customize the outputs and interactions with an LLM.'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 18 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 65 (51 claim, 6 synthesis, 8 transition); 1 failed and 0 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
