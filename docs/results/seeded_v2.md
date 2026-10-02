# Seeded-fault set v2: audit v2 results

The test split was fixed by source document before the audit ran on it (test hash in `data/seeded_v2/split.json`). The audit's
source was frozen (SHA-256 `8258bbe1…`) before the one test run; the run recorded the same hash. Cost of the test run: $0.015.

## Test split (6 documents: 4 write-ups, 2 literature sections; 43 planted faults, 6 controls)

| | red (a `fail` finding) | flagged (fail or warn) |
|---|---|---|
| all planted faults | 33/43 = 77% (95% CI 62-87%) | 41/43 = 95% (85-99%) |
| deterministic faults (8 types) | 24/26 = 92% (76-98%) | |
| subtle faults (6 types) | 9/17 = 53% (31-74%) | |
| write-up faults | 21/31 = 68% (50-81%) | |
| literature faults | 12/12 = 100% (76-100%) | |
| controls: false fails | 1/6 | 3/6 flagged at all |

By type (red/n): fabricated_citation 4/4, unretrieved_citation 4/4, altered_reference 4/4, numeric_table 4/4,
numeric_prose 2/4, misattributed_number 2/4, **reversed_comparison 0/4**, swapped_method 1/3; literature: unresolved_citation 2/2,
moved_citation 2/2, fabricated_quote 2/2, changed_qualifier 2/2, overstated_claim 2/2, swapped_claim_text 2/2.
(Per-type n is 2-4: the intervals are wide, and the literature types rest on two documents.)

## What the numbers say

- The deterministic checks hold on unseen documents (24/26); the two misses are `numeric_prose` faults that landed amber.
- The subtle write-up faults are the weak part. A flipped direction word (`reversed_comparison`) was never a `fail`: 0/4, flagged
  amber in 3 of 4. This is the known miss from the dev run, unchanged on test; nothing was tuned on test.
- The literature audit caught every planted fault (12/12), but on only two documents and with a quote check that sees
  most of what the seeding does (the quote or key is changed). It says little about faults that leave quote and key consistent.
- One of 6 controls failed: on the `topic-llm-judge-numbers` section the `lit.claim_supported` judge rejected a claim
  that is a faithful paraphrase of a hedged survey sentence. That is a judge false positive, at the rate 1/6 (95% CI 3-56%),
  too few controls to say more. A control flagged amber (3/6) means the audit's warnings are not clean on correct documents either.
- Dev vs test: red 24/30 (80%) on dev, 33/43 (77%) on test; the audit did not overfit dev visibly.

## Not shown

Nothing here measures faults the seeding does not plant. Faults are planted by string edits in documents the loop produced, so
they are easier to detect than errors a model makes unprompted; real-world recall will be lower.
