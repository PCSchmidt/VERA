# Audit of topic4-agents-1 (paper): **AMBER**

Checks run: citation, claim_support, inference, sentence. Claims checked: 69. Findings: 0 fail, 5 warn, 0 info. Judge cost $0.00093.

- **warn** (inference) judges disagree (failed in the audit, no on glm-flash at 0.70; the reference judge says yes, yes on sonnet-ref at 0.85): I12 (A research agenda): does not follow from its premises: 'Benchmarks typically score one run per task, and PaperBench reports high variance on the same paper for most agents and recommends several s'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (sentence) S13 (Introduction, claim): the quote of C8 opens with a back-reference, so what it is about is outside it: 'The survey on benchmark data contamination defines it as occurring when language models inadvertently incorporate evaluation benchmark infor'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S25 (Correctness and reproducibility measures in agent benchmarks, claim): the quote of C15 opens with a back-reference, so what it is about is outside it: 'SciReplicate-Bench instead prioritizes execution accuracy, and its authors criticize PaperBench-style approaches for relying on manual crite'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S26 (Correctness and reproducibility measures in agent benchmarks, claim): the quote of C16 opens with a back-reference, so what it is about is outside it: 'SciReplicate-Bench chose a 2024 publication window to minimize the risk of data leakage.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (yes on sonnet-ref at 0.68; the audit's judge said no on glm-flash at 0.80)): S48 (Rubric design, manual criteria, and construct validity concerns, claim): C28 says more than its quote: 'A later CORE-Bench study reports surfacing threats to construct validity in CORE-Bench Hard that are difficult to anticipate with less capab'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 16 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 64 (49 claim, 9 synthesis, 6 transition); 1 failed and 3 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Judge disagreements: 1 (a judge said yes where the audit's judge said no; reported as warnings, not failures).
Unsettled: 1 (the reference judge was unsure, below 0.7, either way; reported as warnings: a failure needs a confident no).
