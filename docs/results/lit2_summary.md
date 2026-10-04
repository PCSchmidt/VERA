# Literature stage v2: what was measured (2026-10-04)

Written for the Increment 4 review. Numbers are from the tables and files named; nothing here is a model's recollection.

## Retrieval (12 queries over seven angles, up to 120 records, snowballing, relevance screen)

| Topic | Key papers retrieved | Kept by the screen | In the top 30 | Increment 3 retrieved |
|---|---|---|---|---|
| research-agents-eval (fresh) | 4 of 10 (40%) | 2 | 3 | |
| conformal-shift (fresh) | 9 of 10 (90%) | 6 | 4 | |
| tabular-trees-vs-nets (fresh) | 9 of 10 (90%) | 8 | 3 | |
| tree-explain (re-run, not independent) | 5 of 10 (50%) | 4 | 2 | 70% |
| credal-dro (re-run, not independent) | 5 of 8 (62%) | 5 | 2 | 38% |
| llm-judge-numbers (re-run, not independent) | 2 of 10 (20%) | 2 | 2 | 20% |

Pooled over the six topics: 34 of 58 key papers retrieved (59%), 27 kept by the screen (47%). The starting threshold of T5's
reverse-if (70% after retrieval) is met on two of the three fresh topics and on none of the re-runs. The one fresh topic below it,
research-agents-eval, has a key list that is partly off the scoped question (the scoped question names SciReplicate-Bench, CORE-Bench
and the novelty studies, not The AI Scientist), so part of its miss is the list and not the retrieval; the five key papers it missed
are all indexed, so the queries missed them. The re-runs moved the old topics in both directions (credal-dro +24 points, tree-explain
-20), which at ten papers per topic is within what one different query changes: no improvement from the new queries is claimed.
Recall is against key lists fixed and hashed before retrieval (`data/topics/manifest.json`); tables in
`retrieval_recall_lit2.md` and `retrieval_recall_lit2_old.md`.

## Claim anchoring

- The check (editorial connectives the quote lacks, and `lit.quote_covers_claim` shown the quote and the source's title) on the
  42 claims Increment 3 passed: 21 fail (50%, 36-64%). On the 30 labelled real claims: 18 fail (60%, 42-75%); 15 of the 26 labelled
  supported fail anchoring, as do 3 of the 4 labelled unsupported: anchoring is not support (`anchoring_real.json`).
- With the one-assertion rule in the synthesis prompt, the three old sections written again from the same evidence kept 9, 11 and 9
  claims (`anchoring_dev.md`); on the fresh topics the first draft failed the checks on 8 of 19 (research-agents-eval), 3 of 18
  (conformal-shift) and 6 of 13 (tabular) claims, and the repair step fixed or dropped them; every final audit is green.
- A reader of the three fresh reviews found sentences that lean on an earlier one for their subject ("It also reports that this
  advantage grows with tuning time"), which the judge had accepted. A deterministic check (`anchoring.dangling_reference`) and a
  line in the prompt now refuse them; 12 of 75 earlier claim sentences had the fault. The three fresh sections were written again
  from the same evidence; both versions are kept (`data/literature_first/`, `data/literature/`).
- Readability notes on the first versions, which a language-model reader (not necessarily Chris) gave: the conformal review is dense
  and jargon-heavy ("nonsymmetric algorithms", stacked terms in two paragraphs); the research-agents review reads as a list in places.
  Not fixed: a prompt instruction to explain jargon risks claims the quotes do not support.

## Disclosed

- The fresh sections' second versions are one attempt each from the same evidence (retrieval was not repeated), so their recall is
  the first runs'.
- The old-topic re-runs reuse Chris's earlier confirmation of each scoped question (`reused_from` in the run's `scope.json`), not
  a new one; the question the stage proposed this time is kept beside it.
- Two bugs found by running the stage on new topics were fixed: GitHub answers 301 for a renamed repository (the parent check did
  not follow it), and an empty answer from the reference service crashed the snowball step.
