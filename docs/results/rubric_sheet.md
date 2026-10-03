# Rubric sheet: scoring the three topic outputs

Four things to score (the TreeHFD topic has a review and a paper). Each is scored 1 to 5 on the five criteria below.
**1** = poor, **3** = acceptable for a careful analyst's week of work, **5** = excellent. The goal is very good
research on a requested topic, not novelty. A score below 3 on any criterion is reported as a finding in the review;
the document is not edited to fix it.

You do not need to be an expert in the topic. Read each output as a reader who wants the question answered, and check
whether it says what it could not do.

| Criterion | Ask yourself |
|---|---|
| 1. Answers the question | Does it answer the question you confirmed, in the form asked? |
| 2. Coverage | Are the important papers and positions there? Does it say what is missing? (The key-paper list fixed before retrieval is `data/topics/<topic>.json`; recall is in `docs/results/retrieval_recall.md`.) |
| 3. Correctness | Do the claims match their sources (and, for the paper, its numbers)? Each review claim has its quote in `claims.jsonl`. |
| 4. Reproducibility | Could someone redo it from what is committed? |
| 5. Honesty about limits | Does it say what it could not establish and where its retrieval and checks are weak? |

## The outputs

| Id | What | Read |
|---|---|---|
| A-lit | tree-explain literature review | `data/literature/tree-explain/literature.md` (question: `data/topics/scope_tree-explain.json`) |
| A-paper | tree-explain research paper (the loop run) | `docs/results/topic-a-loop-3/paper.md`, `results.json`, `audit.md` |
| B | credal-dro literature review | `data/literature/credal-dro/literature.md` (question: `data/topics/scope_credal-dro.json`) |
| C | llm-judge-numbers literature review | `data/literature/llm-judge-numbers/literature.md` (question: `data/topics/scope_llm-judge-numbers.json`) |

Useful background: each folder under `data/literature/<topic>/` also has `claims.jsonl` (claim, source, quote), `audit.md`
(the final audit) and, for B and C, the version before the audit-driven repair (`literature.pre_audit_repair.md`).

## Recording your scores

The five numbers go in the order of the table: answers the question, coverage, correctness, reproducibility, honesty.

```
uv run python scripts/record_rubric.py A-lit --by Chris 3 2 4 4 4 --note "one line on why"
uv run python scripts/record_rubric.py A-paper --by Chris ...
uv run python scripts/record_rubric.py B --by Chris ...
uv run python scripts/record_rubric.py C --by Chris ...
```

(The numbers above are placeholders, not suggestions.) Scores are kept in `data/results/rubric_chris.json`; recording an
output again adds an entry and never replaces one. An independent reviewer scored the same four outputs without reading
this project's own assessments: `data/results/rubric_evaluator.json`. Both sets go into the review unedited.
