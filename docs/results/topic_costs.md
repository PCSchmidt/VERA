# Cost per topic

From each run's own ledger (`data/ledger/run_<id>.jsonl`); regenerate with `scripts/topic_costs.py`.
Stage costs are the spend between a stage's checkpointed result and the one before it; the judge path's
calls (`p2.cheap_path`) inside a stage are part of that stage's cost. Input share is input tokens over
all tokens.

| topic | run | total (USD) | earlier attempts (USD) | loop run | loop (USD) | topic + loop (USD) |
|---|---|---|---|---|---|---|
| credal-dro | scope-credal-dro-2 | 0.0903 | 0.0075 | - | - | 0.0903 |
| llm-judge-numbers | scope-llm-judge-numbers-3 | 0.1062 | 0.0130 | - | - | 0.1062 |
| tree-explain | scope-tree-explain-2 | 0.1703 | 0.0056 | - | - | 0.1703 |

## credal-dro (scope-credal-dro-2)

| stage | decision | cost (USD) | verdicts |
|---|---|---|---|
| scope | accept | 0.0087 | 1 |
| retrieve | accept | 0.0156 | 100 |
| read | accept | 0.0000 | 1 |
| synthesize | accept | 0.0608 | 15 |
| parent | accept | 0.0052 | 1 |

Components of the topic run:

| component | calls | cost (USD) | input tokens | output tokens | input share | largest prompt (tokens) |
|---|---|---|---|---|---|---|
| p2.cheap_path | 343 | 0.0079 | 149723 | 7989 | 0.949 | 1956 |
| p3.parent | 1 | 0.0051 | 1426 | 227 | 0.863 | 1426 |
| p3.retrieve | 4 | 0.0081 | 1520 | 509 | 0.749 | 380 |
| p3.scope | 1 | 0.0087 | 553 | 755 | 0.423 | 553 |
| p3.synthesize | 1 | 0.0605 | 20005 | 2051 | 0.907 | 20005 |

## llm-judge-numbers (scope-llm-judge-numbers-3)

| stage | decision | cost (USD) | verdicts |
|---|---|---|---|
| scope | accept | 0.0064 | 1 |
| retrieve | accept | 0.0132 | 60 |
| read | accept | 0.0000 | 1 |
| synthesize | accept | 0.0866 | 16 |

Components of the topic run:

| component | calls | cost (USD) | input tokens | output tokens | input share | largest prompt (tokens) |
|---|---|---|---|---|---|---|
| p2.cheap_path | 257 | 0.0065 | 119026 | 6315 | 0.95 | 884 |
| p3.retrieve | 4 | 0.0072 | 1256 | 464 | 0.73 | 314 |
| p3.scope | 1 | 0.0063 | 495 | 534 | 0.481 | 495 |
| p3.synthesize | 2 | 0.0862 | 31959 | 2231 | 0.935 | 16012 |

## tree-explain (scope-tree-explain-2)

| stage | decision | cost (USD) | verdicts |
|---|---|---|---|
| scope | accept | 0.0072 | 1 |
| retrieve | accept | 0.0632 | 100 |
| read | accept | 0.0000 | 1 |
| synthesize | accept | 0.0618 | 14 |
| parent | accept | 0.0381 | 1 |

Components of the topic run:

| component | calls | cost (USD) | input tokens | output tokens | input share | largest prompt (tokens) |
|---|---|---|---|---|---|---|
| p2.cheap_path | 342 | 0.0079 | 172970 | 7366 | 0.959 | 1973 |
| p3.parent | 3 | 0.0379 | 11002 | 1586 | 0.874 | 4452 |
| p3.retrieve | 4 | 0.0082 | 1680 | 483 | 0.777 | 420 |
| p3.scope | 1 | 0.0072 | 509 | 618 | 0.452 | 509 |
| p3.synthesize | 2 | 0.1091 | 33624 | 4189 | 0.889 | 21074 |
