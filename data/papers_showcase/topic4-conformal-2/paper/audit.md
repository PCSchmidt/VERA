# Audit of topic4-conformal-2 (paper): **AMBER**

Checks run: citation, claim_support, inference, sentence. Claims checked: 72. Findings: 0 fail, 8 warn, 0 info. Judge cost $0.00094.

- **warn** (inference) unsettled (the reference judge was unsure (no on sonnet-ref at 0.62; the audit's judge said no on glm-flash at 0.70)): I14 (A research agenda): does not follow from its premises: 'Reconcile the training-conditional extension to estimated ratios with the reports of degradation by stating which coverage notion and condit'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (inference) judges disagree (failed in the audit, no on glm-flash at 0.85; the reference judge says yes, yes on sonnet-ref at 0.80): I15 (A research agenda): does not follow from its premises: 'Study label-shift reweighting where density ratios come from pseudo-labels, measuring coverage loss as shift strengthens.'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (inference) unsettled (the reference judge was unsure (yes on sonnet-ref at 0.68; the audit's judge said no on jev at 0.80)): I17 (A research agenda): does not follow from its premises: 'Evaluate in the same experiments the fine-grained approach, which pairs identifiable covariate shift with an f-divergence ball on the condit'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.62; the audit's judge said no on jev at 0.76)): S17 (Weighted conformal prediction under covariate shift: guarantees with known versus estimated likelihood ratios, claim): C14 says more than its quote: 'A later tabular-regression paper restates the known-ratio result as marginal coverage of at least 1 - alpha under covariate shift, provided '
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.60; the audit's judge said no on jev at 0.84)): S51 (Adaptive conformal inference for temporal drift: long-run coverage without data-process assumptions, claim): C35 says more than its quote: 'The abstract of the follow-up work by Gibbs and Candès states that ACI requires knowledge of the rate of change of the data-generating mecha'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.68; the audit's judge said no on jev at 0.84)): S60 (Robust conformal methods under f-divergence and worst-case shift, claim): C42 says more than its quote: 'The fine-grained framework splits the problem differently, reweighting training samples for an identifiable covariate shift while protecting'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on jev at 0.77; the reference judge says yes, yes on sonnet-ref at 0.85): S63 (Robust conformal methods under f-divergence and worst-case shift, claim): C44 says more than its quote: 'Gibbs and Candès describe the f-divergence method of Cauchois et al. as forming prediction sets that are valid whenever P 1 and P 0 are clos'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on glm-flash at 0.90; the reference judge says yes, yes on sonnet-ref at 0.80): S70 (Gaps in the proofs: estimated weights, mixed shifts, and unidentifiable conditional shift, claim): C49 says more than its quote: 'A label-shift Bayesian score paper reports coverage loss under stronger shift because density ratios are estimated from pseudo-labels.'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 16 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 63 (52 claim, 5 synthesis, 6 transition); 5 failed and 0 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Judge disagreements: 3 (a judge said yes where the audit's judge said no; reported as warnings, not failures).
Unsettled: 5 (the reference judge was unsure, below 0.7, either way; reported as warnings: a failure needs a confident no).
