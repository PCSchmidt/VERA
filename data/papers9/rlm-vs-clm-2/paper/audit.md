# Audit of rlm-vs-clm-2 (paper): **RED**

Checks run: citation, claim_support, inference, sentence. Claims checked: 59. Findings: 2 fail, 4 warn, 0 info. Judge cost $0.00098.

- **warn** (inference) unsettled (the reference judge was unsure (yes on sonnet-ref at 0.68; the audit's judge said no on glm-flash at 0.90)): I13 (A research agenda): does not follow from its premises: 'Examine whether traces from each approach can be replayed or reused under harnesses that re-prefill on every edit.'
  - evidence: log `paper/inferences.jsonl` matched=False
- **fail** (sentence) S28 (Context Language Models: context as an updatable file, Suffix Cache Reuse, and reported FLOP savings, claim): C22 says more than its quote: 'Suffix Cache Reuse is the serving co-design that reuses cached states of surviving tokens after an edit.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.50; the audit's judge said no on glm-flash at 0.70)): S42 (Serving-side KV-cache reuse for in-place edits and non-prefix contexts, claim): C32 says more than its quote: 'The SMem authors report that deletion beats suffix recomputation by 8.5x at 512 blocks, while describing the setting as probing the cost mod'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (yes on sonnet-ref at 0.60; the audit's judge said no on glm-flash at 0.70)): S51 (Context management in coding agents: token-level evidence and its limits, claim): C36 says more than its quote: 'The Context Language Models paper describes reinforcement learning in which, because context edits change the input across turns, stepwise G'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S68 (Implications for a CPU-scale companion experiment and its transfer limits, claim): C45 says more than its quote: 'The Context Language Models paper introduces Suffix Cache Reuse (SCR), under which an edit that replaces B with B′ reuses the cached states '
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S72 (Implications for a CPU-scale companion experiment and its transfer limits, claim): the quote of C47 opens with a back-reference, so what it is about is outside it: 'The CacheTune authors report that, in their experiments, the optimized CPU-cache path preserves the benefits of reuse despite the additional'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 12 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 58 (47 claim, 3 synthesis, 8 transition); 4 failed and 1 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Unsettled: 3 (the reference judge was unsure, below 0.7, either way; reported as warnings: a failure needs a confident no).
