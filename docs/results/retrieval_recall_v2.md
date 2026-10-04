# Retrieval v2: recall of the key papers on the fresh topics
Key papers fixed and hashed before any retrieval for the topic. Starting threshold 70% (T5 reverse-if (1)), not a target. Retrieval v2: 12 queries over seven angles, up to 120 records.

## research-agents-eval
Run `topic4-agents-1`: 12 queries, 160 candidates, 41 kept by the screen, 19 claims drafted, 18 kept (first-draft failures 8).

| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 4 of 10 | 40% |
| Kept by the screen | 2 | 20% |
| In the top 30 by rank | 3 | 30% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| The AI Scientist: Towards Fully Automated Open-Ended Scientific Discov | yes | no | 6 | screened out |
| The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via | no | no |  | indexed, queries missed it |
| MLE-bench: Evaluating Machine Learning Agents on Machine Learning Engi | yes | no | 21 | screened out |
| PaperBench: Evaluating AI's Ability to Replicate AI Research | yes | yes | 24 |  |
| MLAgentBench: Evaluating Language Agents on Machine Learning Experimen | no | no |  | indexed, queries missed it |
| CycleResearcher: Improving Automated Research via Automated Review | no | no |  | indexed, queries missed it |
| Agent Laboratory: Using LLM Agents as Research Assistants | no | no |  | indexed, queries missed it |
| Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with | yes | yes | 107 |  |
| MLR-Copilot: Autonomous Machine Learning Research based on Large Langu | no | no |  | indexed, queries missed it |
| SciCode: A Research Coding Benchmark Curated by Scientists | no | no |  | indexed, queries missed it |

Recall after retrieval 40% (BELOW 70%).

## conformal-shift
Run `topic4-conformal-2`: 12 queries, 160 candidates, 57 kept by the screen, 18 claims drafted, 18 kept (first-draft failures 3).

| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 9 of 10 | 90% |
| Kept by the screen | 6 | 60% |
| In the top 30 by rank | 4 | 40% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Conformal Prediction Under Covariate Shift | yes | yes | 29 |  |
| Conformal prediction beyond exchangeability | yes | yes | 12 |  |
| Adaptive Conformal Inference Under Distribution Shift | yes | yes | 8 |  |
| A Gentle Introduction to Conformal Prediction and Distribution-Free Un | yes | no | 44 | screened out |
| Conformalized Quantile Regression | yes | no | 130 | screened out |
| Distribution-Free Predictive Inference For Regression | yes | yes | 122 |  |
| Adaptive Conformal Predictions for Time Series | yes | yes | 18 |  |
| Distribution-free uncertainty quantification for classification under  | yes | yes | 153 |  |
| Conformal prediction for time series | no | no |  | indexed, queries missed it |
| Predictive inference with the jackknife+ | yes | no | 125 | screened out |

Recall after retrieval 90% (at or above 70%).
