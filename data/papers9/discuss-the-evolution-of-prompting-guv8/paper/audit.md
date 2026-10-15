# Audit of discuss-the-evolution-of-prompting-guv8 (paper): **RED**

Checks run: citation, claim_support, inference, sentence. Claims checked: 78. Findings: 1 fail, 4 warn, 0 info. Judge cost $0.00118.

- **warn** (sentence) S18 (Prompt engineering: definitions, scope, and terminological fragmentation, claim): the quote of C10 opens with a back-reference, so what it is about is outside it: 'A separate wireless-networks overview defines the perspective as designing prompts to guide LLMs to generate desired output without updating'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on jev at 0.75; the reference judge says yes, yes on sonnet-ref at 0.72): S36 (Context engineering: moving from prompt text to system-level context, claim): C22 says more than its quote: 'R20 describes context rot as the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the contex'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) S46 (Harness engineering: the structure built around a fixed model, claim): judge unsure whether C29 says more than its quote: "The externalization review describes the harness's layered model boundary as a structured form of context engineering."
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (yes on sonnet-ref at 0.62; the audit's judge said no on glm-flash at 0.75)): S60 (Agentic harnesses: loops, multi-agent orchestration, and agentic RAG, claim): C40 says more than its quote: 'For multi-agent orchestration, the TDD governance paper has the orchestration engine retain authority over state while models only propose.'
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S61 (Agentic harnesses: loops, multi-agent orchestration, and agentic RAG, claim): C41 says more than its quote: 'The MemTool paper offers autonomous, workflow and hybrid modes, showing that the degree of agent autonomy is a design variable.'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 18 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 73 (57 claim, 9 synthesis, 7 transition); 3 failed and 2 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Judge disagreements: 1 (a judge said yes where the audit's judge said no; reported as warnings, not failures).
Unsettled: 1 (the reference judge was unsure, below 0.7, either way; reported as warnings: a failure needs a confident no).
