# Rubric sheet 4: scoring the eight Increment 4 outputs (blind)

Eight things to score, each 1 to 5 on the five criteria below. **1** = poor, **3** = acceptable for a careful analyst's week of work, **5** = excellent.
The goal is very good research on a requested topic, not novelty. A score below 3 on any criterion is reported as a finding in the review; the document
is not edited to fix it. You do not need to be an expert: read each as a reader who wants the question answered, and check whether it says what it could
not do.

**Blind means:** score before you read the independent scorer's scores (`data/results/rubric4_evaluator.json`, which does not exist yet and will be made
after yours) and before you read the review's own judgement of these outputs. The script refuses a `--blind` entry once that file exists.

| Criterion | Ask yourself |
|---|---|
| 1. Answers the question | Does it answer the question you confirmed, in the form asked? |
| 2. Coverage | Are the important papers and positions there? Does it say what is missing? (key-paper lists are in `data/topics/<topic>.json`; recall in `docs/results/retrieval_recall_lit2.md` and `_old.md`) |
| 3. Correctness | Do the claims match their sources (and, for a paper, its numbers)? Each review claim has its quote in `claims.jsonl`. |
| 4. Reproducibility | Could someone redo it from what is committed? |
| 5. Honesty about limits | Does it say what it could not establish and where its retrieval and checks are weak? |

## The outputs

| Id | What | Read |
|---|---|---|
| L1 | research-agents-eval literature review (fresh topic) | `data/literature/research-agents-eval/literature.md`; question `data/topics/scope_research-agents-eval.json` |
| L2 | conformal-shift literature review (fresh) | `data/literature/conformal-shift/literature.md`; `scope_conformal-shift.json` |
| L3 | tabular-trees-vs-nets literature review (fresh) | `data/literature/tabular-trees-vs-nets/literature.md`; `scope_tabular-trees-vs-nets.json` |
| L4 | tree-explain literature review (stage v2, re-run) | `data/literature_lit2/tree-explain/literature.md`; question `data/topics/scope_tree-explain.json` |
| L5 | credal-dro literature review (stage v2, re-run) | `data/literature_lit2/credal-dro/literature.md`; `scope_credal-dro.json` |
| L6 | llm-judge-numbers literature review (stage v2, re-run) | `data/literature_lit2/llm-judge-numbers/literature.md`; `scope_llm-judge-numbers.json` |
| P1 | tree-explain research paper (the loop run, with its protocol and figures) | `docs/results/runs4/runs4-tree-explain/paper.md` (figures beside it), `results.json`, `audit.md` |
| P2 | credal research paper (the loop run) | `docs/results/runs4/runs4-credal/paper.md`, `results.json`, `audit.md` |

Each folder also has `claims.jsonl` and `audit.md` (the final audit). The first versions of the three fresh reviews are in `data/literature_first/`; the
ones above are the second versions (written again after a reader found sentences leaning on an earlier one).

## Recording your scores

Five numbers in the order of the table: answers the question, coverage, correctness, reproducibility, honesty.

```
uv run python scripts/record_rubric4.py L1 --by Chris --blind 3 2 4 4 4 --note "one line on why"
```

and the same for L2 to L6, P1 and P2.

## The claim re-labels (twelve claims)

`data/claim_bench/relabel_sheet.csv` has twelve real claims drawn from the review sections, each with the passage that holds its quote. For each, write
`yes` (the passage states or clearly implies the claim as written, including direction, numbers and qualifiers) or `no` in the last column, without opening
`real_claims_labels.csv` (the AI helper's labels) first. Then:

```
uv run python scripts/record_relabels.py --by Chris
```
