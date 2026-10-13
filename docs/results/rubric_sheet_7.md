# Rubric sheet 7: scoring the papers made with the Increment 7 checks (blind)

## What you are scoring

Two **review papers** made through the app in Increment 7, with every sentence checked. Score **the paper**, reading it
beside **the review it came from**. Each paper gets **six scores from 1 to 5** and **one preference**, on the Increment 6
rubric (`docs/results/rubric_sheet_6.md`):

| Criterion | Ask yourself |
|---|---|
| 1. Answers the question | Does the paper answer the question that was confirmed for the run? |
| 2. Coverage | Are the important papers and positions there? Does it say what is missing, and what it searched for by name? |
| 3. Correctness | Do the cited sentences match their quotes (Appendix B)? Do the synthesis sentences follow from the claims they name (Appendix D), and do the other uncited sentences state no facts? |
| 4. Reproducibility | Could someone redo it from what is saved (question, queries, sources, claims, sentences, statements, audit)? |
| 5. Honesty about limits | Does it say what it could not establish and where its search and checks are weak? |
| 6. Interpretation follows from evidence | Does each Discussion, Conclusions and agenda statement follow from the claims it names (Appendix C)? |

**Preference**: the paper or the review it came from: `paper`, `review` or `same`.

## Who scores, and in what order

1. **The first scorer** scores both papers, blind (before the independent scorer's file exists), with their real name in
   `--by`. The SPEC has Chris score first. On 2026-10-13 Chris chose to have an assistant score instead; then `--by` names
   that assistant and `--attribution` says so, and the review states that Increment 7 has no human scores.
2. **The independent scorer** (a fresh Claude agent, told not to open the first scorer's file, the external review or the
   Increment 7 review notes) scores both, and **reads every claim against its quote and every synthesis sentence against
   its premises**, listing each defect by claim, sentence or statement id. Its defect counts are compared with Increment
   6's (P2: 6 of 59 claims).

## The two papers

| Id | Paper | Read |
|---|---|---|
| N1 | P2's paper, made again | `data/paper_rerun/discuss-the-evolution-of-prompting-guv8/paper/paper.md` beside `.../literature.md` |
| N2 | The new RLM and CLM paper | `data/paper_rerun/rlm-vs-clm-2/paper/paper.md` beside `.../literature.md` |

The PDFs (with appendices B to D) are in the app: open the run, then the Paper tab, then Download PDF.

## Recording

```bash
uv run python scripts/record_rubric7.py N1 --by "<name>" --blind 3 3 3 4 4 3 --prefer paper --note "why, in a line" --attribution "<who scored, at whose request>"
uv run python scripts/record_rubric7.py N2 --by "<name>" --blind ...
```
