# Rubric sheet 6: scoring the review papers (blind)

## What you are scoring

Three **review papers** made through the app in Increment 6, each from a finished literature review. Score **the paper**, reading it
beside **the review it came from**. Each paper gets **six scores from 1 to 5** and **one preference**:

- **1 = poor**: it fails at this, or you would not rely on it.
- **3 = acceptable**: what a careful analyst might hand you after a week's work on the question.
- **5 = excellent**: you could not reasonably ask for more.

| Criterion | Ask yourself |
|---|---|
| 1. Answers the question | Does the paper answer the question that was confirmed for the run? |
| 2. Coverage | Are the important papers and positions there? Does it say what is missing? |
| 3. Correctness | Do the cited sentences match their sources? (Appendix B of the PDF, or click a dotted sentence.) Include the uncited sentences in the evidence sections: do they say only what the cited ones support? |
| 4. Reproducibility | Could someone redo it from what is saved (question, queries, sources, claims, statements, audit)? |
| 5. Honesty about limits | Does it say what it could not establish and where its search and checks are weak? |
| 6. Interpretation follows from evidence | In the Discussion, Conclusions and research agenda: does each statement follow from the claims it names (Appendix C), without overreaching? |

**Preference**: would you rather have the paper or the review it came from? `paper`, `review` or `same`.

A score below 3 is reported as a finding in the review; the paper is not edited to fix it.

## Blind, and help from a model

**Blind** means you score before the independent scorer (a fresh model, run afterwards on the same files, told not to open your file or
the external review) and before reading the review's judgement of these papers. The recording script refuses `--blind` once the
independent scorer's file exists.

**Say if a model helped.** You have read ChatGPT's analysis of P1 (`docs/results/incr6_external_review.md`). That is fine, and it must be
stated: record P1 with `--helped-by "ChatGPT external review"`, and do the same for any paper where a model helped you form a score. The
review reports every score that had help.

## The three papers

| Id | Paper | Its review | Read |
|---|---|---|---|
| P1 | Recovering Reusable Knowledge from Coding-Agent Traces | the agent-traces review | `data/paper_demo/how-much-useable-information-about-6x3n/paper/paper.md` beside `.../literature.md` |
| P2 | The prompting-to-harness evolution paper | the prompting review | `data/paper_demo/discuss-the-evolution-of-prompting-guv8/paper/paper.md` beside `.../literature.md` |
| P3 | The RLM and CLM paper | the RLM and CLM review | `data/paper_demo/rlm-vs-clm-3/paper/paper.md` beside `.../literature.md` |

Easier in the app: My runs, open the run, then the **Review** and **Paper** tabs; or download each PDF (Appendix B: claims and quotes;
Appendix C: interpretation statements, kept and removed).

## Recording your scores

Six numbers in the order of the table, then the preference:

```
uv run python scripts/record_rubric6.py P1 --by Chris --blind 3 3 3 4 4 3 --prefer paper --helped-by "ChatGPT external review" --note "one line on why"
uv run python scripts/record_rubric6.py P2 --by Chris --blind 3 3 3 4 4 3 --prefer paper --note "one line on why"
uv run python scripts/record_rubric6.py P3 --by Chris --blind 3 3 3 4 4 3 --prefer paper --note "one line on why"
```

(The numbers are placeholders.) Then tell Claude Code; it runs the independent scorer, and the gate (`rubric6_scored`) needs your approval.
