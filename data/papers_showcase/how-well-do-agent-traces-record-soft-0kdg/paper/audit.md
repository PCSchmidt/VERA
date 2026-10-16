# Audit of how-well-do-agent-traces-record-soft-0kdg (paper): **RED**

Checks run: citation, claim_support, inference, sentence. Claims checked: 73. Findings: 1 fail, 10 warn, 0 info. Judge cost $0.00115.

- **warn** (inference) unsettled (the reference judge was unsure (no on sonnet-ref at 0.68; the audit's judge said no on glm-flash at 0.80)): I11 (Conclusions): does not follow from its premises: "How edits, test results, and commit history are encoded in each harness's own trace remains unanswered, although one benchmark pipeline maps"
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (inference) unsettled (the reference judge was unsure (no on sonnet-ref at 0.68; the audit's judge said no on glm-flash at 0.90)): I12 (A research agenda): does not follow from its premises: 'Compare the native trace schemas of the named harnesses field by field, covering edits, test outcomes, task status, and commits, since the c'
  - evidence: log `paper/inferences.jsonl` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on glm-flash at 0.80; the reference judge says yes, yes on sonnet-ref at 0.93): S19 (How traces represent development progress: edits, tests, and task state, claim): C15 says more than its quote: 'A later study of CLI coding agent trajectories reports that Bouzenia et al. normalized agent logs into thought-action-result triples over 12'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.62; the audit's judge said no on jev at 0.74)): S24 (How traces represent development progress: edits, tests, and task state, claim): C17 says more than its quote: "SWE-agent's failure analysis found that Failed Edit Recovery, where models fail to generate well-formed edits, made up 23.4% of unresolved i"
  - evidence: log `paper/paper.json` matched=False
- **fail** (sentence) S29 (Trajectory and log formats across SWE-agent, OpenHands, and other harnesses, claim): C19 says more than its quote: 'Bouzenia and colleagues unified the interaction logs of RepairAgent, AutoCodeRover, and OpenHands into a common format, capturing 120 trajec'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) judges disagree (failed in the audit, no on jev at 0.72; the reference judge says yes, yes on sonnet-ref at 0.90): S30 (Trajectory and log formats across SWE-agent, OpenHands, and other harnesses, claim): C20 says more than its quote: 'A later study describes that earlier work as normalizing agent logs into thought-action-result triples over 120 trajectories.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.68; the audit's judge said no on glm-flash at 0.85)): S34 (Trajectory and log formats across SWE-agent, OpenHands, and other harnesses, claim): C23 says more than its quote: 'A survey of provenance states that logs give chronological observability but may not show which tool output changed the plan.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.68; the audit's judge said no on jev at 0.71)): S45 (Claude Code session storage and memory retrieval without vector indexes, claim): C33 says more than its quote: 'A broader software-engineering survey describes embedding-based memory as a storage format used by other agents.'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.62; the audit's judge said no on glm-flash at 0.90)): S46 (Claude Code session storage and memory retrieval without vector indexes, claim): C34 says more than its quote: 'The survey describes a key-value pair memory format in which information received from agents is stored in an external memory, with a key ex'
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (yes on sonnet-ref at 0.62; the audit's judge said no on glm-flash at 0.90)): S63 (Git-native and structured-log approaches to history and coordination, claim): C47 says more than its quote: "The grite study also reports that every agent's copy of the log converges to the same state with no write silently dropped, where a file-bas"
  - evidence: log `paper/paper.json` matched=False
- **warn** (sentence) unsettled (the reference judge was unsure (no on sonnet-ref at 0.68; the audit's judge said no on jev at 0.71)): S72 (Gaps in the evidence: Aider, Codex CLI, and vector-database mining, claim): C53 says more than its quote: 'A study of CLI agent failures names Codex alongside Claude Code and Gemini CLI as examples of terminal-based products.'
  - evidence: log `paper/paper.json` matched=False

Skipped checks:
- method_code: AUD-F-05: method-code alignment arrives in Increment 4
- spec_leakage: AUD-F-06: leakage checks arrive in Increment 6
- novelty: AUD-F-07: novelty against retrieved literature arrives in Increment 4
- rerun: AUD-F-08: re-running experiments is optional, Increment 6

Interpretation statements re-checked: 15 (judged to follow from the claims they name; not checked against quotes).

Sentences re-checked: 69 (59 claim, 6 synthesis, 4 transition); 9 failed and 0 were flagged. Claims were checked to say no more than their quotes; sentences without a claim were checked to state no fact, or to follow from the claims they rest on.
Judge disagreements: 2 (a judge said yes where the audit's judge said no; reported as warnings, not failures).
Unsettled: 8 (the reference judge was unsure, below 0.7, either way; reported as warnings: a failure needs a confident no).
