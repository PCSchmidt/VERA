# Claim anchoring: development measurements (Increment 4, 2026-10-03)

Dev measurements on the three Increment 3 topics' evidence, which is no longer independent (their key lists and retrieval
were tuned after results). The fresh topic is the clean test of this stage; nothing here is claimed as that.

## The check on the claims Increment 3 passed

42 claims (13 tree-explain, 14 credal-dro, 15 llm-judge-numbers), as the synthesis stage passed them (the version before the
audit-driven repair where there was one), through `lit.quote_covers_claim` (shown the quote only) and the editorial-connective
check (`vera/literature/anchoring.py`, `scripts/measure_anchoring.py`, `data/results/anchoring_measure.json`):

| Version of the question | Fail | Rate (95% CI) |
|---|---|---|
| quote and claim only | 31 of 42 | 74% (59–85%) |
| quote, claim and the source's title (the claim is about that source) | 21 of 42 | **50% (36–64%)** |

Four sentences carry an editorial connective ("sits oddly", "but this is", "so this", "rather than") the quote does not. The
rest are claims whose quotes were short fragments under paraphrased sentences. So half of the Increment 3 claims were not
anchored by the standard now set; the Increment 3 audit never claimed they were. The SPEC's reverse-if (a failure rate above
10% on these claims) is met, and the reading is "the Increment 3 synthesis prompt lacked the rule", not "the check is
broken": the rule was then added (`ANCHOR_RULE`: one assertion per sentence, no comparison or inference of the review's
own, the quote the complete sentence of the passage that states it).

## The new rule, on the same evidence, written again

`scripts/resynthesize.py` rewrites each topic's section from the evidence its run gathered, in a new run directory (the
Increment 3 sections are untouched). One attempt each, Sonnet 5.5 and the cheap judge path (about $0.10 each):

| Topic | Drafted | Failed first time | Repaired | Removed | Kept | Final audit | Increment 3 kept |
|---|---|---|---|---|---|---|---|
| tree-explain | 12 | 5 (42%) | 2 | 3 | 9 | green, 0 findings | 13 |
| llm-judge-numbers | 14 | 4 (29%) | 1 | 3 | 11 | green, 0 findings | 15 |
| credal-dro | 11 | 5 (45%) | 3 | 2 | 9 | green, 0 findings | 14 |

The failures at first draft are almost all the anchoring check (11 of 14), and the sections end shorter (9 to 11 claims, against
13 to 15) and clean on the final audit, which had failed 4 claims in the Increment 3 sections. Anchoring has a price: about a
quarter of the claims. Whether the shorter, tighter sections score better on the rubric is not measured here; the fresh
topic and the blind rubric scores are where that shows. Earlier variants of the question (quote only; the first prompt
without the complete-sentence rule) are in the ledgers `anchormeasure-1` and `resynth-*-1` and the table above.

The resynthesized sections are in `data/literature_v2_dev/`. Their retrieval-statistics paragraph says 5 queries because the
Increment 3 retrieval used 5; a new run uses 12.
