# The first live run through the app (2026-10-07)

A real topic, run through the local app with the key from the maintainer's `.env`, before any other person used it. Chris chose the topic.
Evidence is committed in `data/app/live/rlm-vs-clm-2/` (the review, its claims with quotes, the audit, the scope record, the run's ledger).
This is one run; it shows that the path works end to end and what broke on the way. It is not a measure of quality, and Chris's blind scores
of it are separate (`rubric_scored`).

**Topic as submitted:** RLM (recursive language models) versus CLM (Context Language Models): overlaps, similarities, distinctions, and
validity as improvements for production coding (quality, cost efficiency, ability to reuse traces, similar practical criteria). Cap $1.

## What happened

| Step | Result |
|---|---|
| Attempt 1 (`rlm-vs-clm-1`), the topic as first written | Scoping proposed a two-part question and read "CLM" as "context-conditioned" models. The scoping check rejected it as not specific enough. **The app then showed a dead end** with no way to edit the question. Spent $0.0073. |
| Fix | A question the check rejects now goes to "waiting for you", with a note, so it can be edited or confirmed (test: `test_APP_F_01_a_question_the_judge_rejected_can_be_edited_and_the_run_continues`). |
| Attempt 2 (`rlm-vs-clm-2`), definitions of RLM and CLM added to the topic text | Scoped and passed the check. Chris confirmed the question at 14:16:19Z. |
| Crash at the snowball step, 9 minutes after confirmation | A PDF parser fragment ("Apri") reached a year comparison (`int("Apri")`). The app said "could not continue" and kept the traceback in the run's own log. |
| Fix and resume | The year comparison tolerates an unreadable year (test added). **Resume** restarted from the last checkpoint without repeating paid work; the run finished 6 minutes later. |
| Final | Complete. Spent $0.1849 of the $1 cap (219 ledger records, 214 of them judge calls). Audit **green**: 22 claims checked, no findings. |

## What the review shows

- Retrieval: 12 queries, 120 candidates before the snowball step (160 records in the log after it), 31 kept by the relevance screen, 6 read in
  full text and 25 at the abstract only. Both papers the topic is about were retrieved (the RLM paper, arXiv:2512.24601, and the CLM paper,
  arXiv:2609.37725), together with an independent reproduction of RLM (the record of which came from Semantic Scholar).
- The text separates what the papers report from what they do not: no head-to-head RLM versus CLM result on tokens or latency in isolation, no
  RLM cost on coding workloads, no reuse of traces across tasks. It says the CLM authors' metric is prefix-reuse FLOPs, not wall-clock latency.
- **Checked by hand against the CLM paper's own text (the PDF Chris supplied):** the 29.5% fewer FLOPs on TerminalBench 2.1 at matched accuracy;
  RLM among the baselines on a shared Mini-SWE-Agent backbone; the metric named prefix-reuse FLOPs. All three are in the paper. Not checked: the
  other 20 claims, and the claims about papers other than the CLM paper.
- The question the scoper proposed also contained a "small CPU-scale companion experiment"; the app cannot run experiments, so the review is
  a literature review only.

## What it does not show

- It says nothing about answer quality beyond the claims above; Chris's blind rubric scores are the quality measure.
- A green audit means the citations are real and each claim is supported by the passage it quotes. It does not mean the review is complete.
- One topic, one run, run by the builder. The new-user walkthrough is the test of whether a person who did not build it can do this.
