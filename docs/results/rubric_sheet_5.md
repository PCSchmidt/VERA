# Rubric sheet 5: scoring what the app produced (blind)

## What a "score" is here

You are rating **three finished outputs** (below). Each gets **five scores from 1 to 5**, one per criterion in the table. That is fifteen
numbers in all. A score is your own judgement of that one thing about that one document, using this scale:

- **1 = poor**: it fails at this, or you would not rely on it.
- **3 = acceptable**: what a careful analyst might hand you after a week's work on the question.
- **5 = excellent**: you could not reasonably ask for more.

A score below 3 on any criterion is reported as a finding in the review; **the document is not edited to fix it.** You do not need to be an
expert in the topic: read as someone who wants their question answered, and notice whether the document says what it could not do.

**Blind** means you give your scores *before* you read the independent scorer's (a separate language-model scorer, run afterwards on the same
files, whose file does not exist yet) and before you read the review's own judgement of these outputs. The recording script refuses a
`--blind` entry once the independent file exists. Your scores are the project's human measure of quality; the independent scorer is a check
on them, not a substitute. If a language model helps you write down a score or a note, say so in the note: the review will state it.

| Criterion | Ask yourself |
|---|---|
| 1. Answers the question | Does it answer the question that was confirmed for the run, in the form asked? |
| 2. Coverage | Are the important papers and positions there? Does it say what is missing? (The retrieval note at its end says what the search found.) |
| 3. Correctness | Do the claims match their sources? Each cited sentence has its quote: click a dotted sentence in the reader, or read Appendix B of the PDF. |
| 4. Reproducibility | Could someone redo it from what is saved? (Question, queries, sources and the audit are recorded with the run.) |
| 5. Honesty about limits | Does it say what it could not establish and where its search and checks are weak? |

## The three outputs

| Id | What | Where to read it |
|---|---|---|
| W1 | The review from the walkthrough run (agentic traces; your own key; the clean clone) | `data/walkthrough/research-agentic-traces-and-their-vi-0svs/literature.md` (its question: `scope.json`) |
| R1 | The review on RLM and CLM | `data/app/live/rlm-vs-clm-2/literature.md` (its question: `scope.json`) |
| R2 | The first agent-traces review (the rehearsal from the development folder) | `data/app/live/how-well-do-agent-traces-record-soft-0kdg/literature.md` (its question: `scope.json`) |

You can also read each in the app (My runs, or the files above in any editor). Each folder has `claims.jsonl` (each claim and its quote),
`audit.md` and `ledger.jsonl` (what it cost).

Known issues you may notice, which the review will report and which you should score as you find them: W1 had one sentence naming a source
(R12) with no citation and no quote, found after the run and since fixed in the pipeline; all three were produced before the app's
redesign, so the pages you may have seen differ from today's; the documents themselves are unchanged.

## Recording your scores

Five numbers in the order of the table, one command per output:

```
uv run python scripts/record_rubric5.py W1 --by Chris --blind 3 2 4 4 4 --note "one line on why"
uv run python scripts/record_rubric5.py R1 --by Chris --blind 3 2 4 4 4 --note "one line on why"
uv run python scripts/record_rubric5.py R2 --by Chris --blind 3 2 4 4 4 --note "one line on why"
```

(The example numbers are placeholders.) Then run `bash scripts/gate-rubric5.sh` only after the independent scorer has run; the gate also
needs your own approval, as before.
