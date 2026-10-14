# Audit of rlm-vs-clm-3 (paper): **RED**

Checks run: citation, claim_support, inference, sentence. Claims checked: 73. Findings: 20 fail, 17 warn, 0 info. Judge cost $0.00118.

- **fail** (inference) I1 (Discussion): does not follow from its premises: 'The RLM and context-compression literatures share a goal: working over inputs larger than a model can comfortably handle in one pass. RLMs t'
  - evidence: log `paper/inferences.jsonl` matched=False
- **fail** (inference) I3 (Discussion): does not follow from its premises: 'Chained RLM sits between the two. It passes a summary, blackboard and durable artifacts to a fresh root of the same model, because the worki'
  - evidence: log `paper/inferences.jsonl` matched=False
- **fail** (inference) I14 (A research agenda): does not follow from its premises: 'Compare RLMs and compression methods on coding tasks by billed cost and patch success, not token counts alone, because token removal has rai'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (sentence) S2 (Introduction, claim): the quote of C2 opens with a back-reference, so what it is about is outside it: 'The straightforward approach of placing everything in the context has a stated limitation: the entire problem-solving process has to occur i'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S4 (Introduction, unrecorded): absence: 'no published empirical study' belongs in the record sections, not the evidence: 'That same paper states that no published empirical study has tested how codebase scale drives context growth and tool-call degradation, so t'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S7 (Introduction, claim): C6 says more than its quote: 'Follow-up work qualifies this picture: the SRLM study finds that recursion itself is not the primary driver of performance in RLM [R9].'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S9 (Introduction, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The context-centric side of the question covers methods that compress or condition on large contexts.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S12 (Introduction, unrecorded): names a source without a claim: 'Shao and colleagues': 'The Context Language Models paper by Shao and colleagues introduces models that natively manage their own context, treating the context as a'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S13 (Introduction, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The supplied passages also do not directly compare RLMs and CLMs on production coding cost or on the reuse of execution traces.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S15 (Externalized context and recursive decomposition in RLMs, claim): the quote of C11 opens with a back-reference, so what it is about is outside it: "Chained RLM's authors note that Recursive Language Models improve long-context inference without changing model weights, but the global work"
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S18 (Externalized context and recursive decomposition in RLMs, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The sources disagree about whether recursion itself drives the gains.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S23 (Externalized context and recursive decomposition in RLMs, unrecorded): absence: 'passages do not cover' belongs in the record sections, not the evidence: 'The supplied passages do not cover the Context Language Models paper, so any comparison of CLMs with RLMs, and any evidence on production co'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S24 (Context-centric models: compression, memory and context management, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The sources show several mechanisms for compressing or managing context, and they differ in where the compression is stored.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S27 (Context-centric models: compression, memory and context management, claim): the quote of C20 opens with a back-reference, so what it is about is outside it: 'A survey notes that gist-token methods carry a cost in model modification [R12].'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S28 (Context-centric models: compression, memory and context management, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'Other work moves compression offline or hands it to the model itself.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S29 (Context-centric models: compression, memory and context management, claim): C21 says more than its quote: 'The Cartridges authors train a small KV cache per corpus from synthetic conversations with a context-distillation objective [R94].'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S33 (Context-centric models: compression, memory and context management, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'Evidence on the limits of long context is mixed with the compression results above.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S34 (Context-centric models: compression, memory and context management, claim): C25 says more than its quote: 'The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed p'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S35 (Context-centric models: compression, memory and context management, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The passages supplied do not include the paper on Context Language Models that treats the context as an editable file, so no comparison with'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S36 (Context-centric models: compression, memory and context management, unrecorded): states a fact that does not follow from its section's claims (does not follow from its premises): 'They also give no direct measurement of coding quality, cost or trace reuse for these compression methods.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S37 (Mechanistic overlap and differences between RLMs and CLMs, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The Context Language Models paper named in the brief is not among the supplied passages, so what follows covers RLMs and neighbouring contex'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S39 (Mechanistic overlap and differences between RLMs and CLMs, claim): the quote of C27 opens with a back-reference, so what it is about is outside it: 'Chained RLM states that RLMs improve long-context inference without changing model weights [R5].'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S41 (Mechanistic overlap and differences between RLMs and CLMs, unrecorded): states a fact that does not follow from its section's claims (does not follow from its premises): 'The compression line instead modifies or trains parameters to shrink context.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S46 (Mechanistic overlap and differences between RLMs and CLMs, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'Evidence on RLM quality and cost is mixed.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S49 (Mechanistic overlap and differences between RLMs and CLMs, claim): C35 says more than its quote: 'A billing study of coding agents finds that user-side context layers account for only about 6% of cost [R78].'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S50 (Mechanistic overlap and differences between RLMs and CLMs, unrecorded): absence: 'None of the supplied passages' belongs in the record sections, not the evidence: 'None of the supplied passages evaluates RLMs or CLMs on production coding, and none examines reuse of execution traces across tasks, so thos'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S51 (Output quality: gains, caveats and degradation with long context, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'The sources describe output quality under long context as a mix of gains and degradation, and they do not settle how far these results carry'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S54 (Output quality: gains, caveats and degradation with long context, claim): judge unsure whether C38 says more than its quote: 'The SRLM authors also conclude that recursion is not the primary driver of RLM performance [R9].'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S55 (Output quality: gains, caveats and degradation with long context, claim): C39 says more than its quote: 'The λ-RLM authors report that a typed functional runtime outperformed standard RLM in most model-task comparisons [R86].'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S56 (Output quality: gains, caveats and degradation with long context, unrecorded): states a fact without naming its premises; judged to follow from its section's claims: 'On the context side, the evidence shows that long inputs themselves hurt, and that compression can help.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S60 (Output quality: gains, caveats and degradation with long context, unrecorded): states a fact that does not follow from its section's claims (does not follow from its premises): 'For coding specifically, the evidence is thin: the context-rot paper only proposes a study, and the passages supplied say nothing about the '
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S62 (Cost efficiency: token reduction versus billed cost, claim): C44 says more than its quote: 'The central finding on this theme comes from a study of token-reduction tools for coding agents, which separates tokens removed from money s'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S65 (Cost efficiency: token reduction versus billed cost, unrecorded): states a fact that does not follow from its section's claims (does not follow from its premises): 'Work on compressing contexts reports efficiency in different units, namely latency and memory rather than billed spend.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S70 (Cost efficiency: token reduction versus billed cost, unrecorded): absence: 'passages do not include' belongs in the record sections, not the evidence: 'The supplied passages do not include the Context Language Models paper itself, so its cost behavior is not assessed here.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S71 (Cost efficiency: token reduction versus billed cost, unrecorded): absence: 'None of the compression studies' belongs in the record sections, not the evidence: 'None of the compression studies above reports provider-billed cost per successful coding task, and no passage covers recursive language mode'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S72 (Production coding, trace reuse and evidence gaps, unrecorded): states a fact that does not follow from its section's claims (does not follow from its premises): 'The sources supplied here say little about production coding as such, and none of them is the Context Language Models paper the reader named'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on glm-flash at 0.80; the reference judge says yes, yes on sonnet-ref at 0.70): S80 (Production coding, trace reuse and evidence gaps, unrecorded): states a fact that does not follow from its section's claims (does not follow from its premises): 'Taken together, the passages supply no head-to-head comparison of RLMs and CLMs on production coding quality, cost, or trace reuse.'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 16 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 80 (57 claim, 23 unrecorded); 18 failed and 16 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Judge disagreements: 1 (a sentence or statement that passed a judge question when it was written failed the same question in the audit; reported as warnings, not failures).
