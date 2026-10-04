# Retrieval v2: recall of the key papers on the fresh topics
Key papers fixed and hashed before any retrieval for the topic. Starting threshold 70% (T5 reverse-if (1)), not a target. Retrieval v2: 12 queries, seven angles, 120 records.

## tree-explain
Run `lit2-tree-explain`: 12 queries, 160 candidates, 37 kept by the screen, 12 claims drafted, 10 kept (first-draft failures 3).

| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 5 of 10 | 50% |
| Kept by the screen | 4 | 40% |
| In the top 30 by rank | 2 | 20% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Tree Ensemble Explainability through the Hoeffding Functional Decompos | yes | yes | 32 |  |
| Explainable AI for Trees: From Local Explanations to Global Understand | no | no |  | indexed, queries missed it |
| A Unified Approach to Interpreting Model Predictions | no | no |  | indexed, queries missed it |
| Explaining individual predictions when features are dependent: More ac | yes | yes | 19 |  |
| Purifying Interaction Effects with the Functional ANOVA: An Efficient  | no | no |  | indexed, queries missed it |
| SHAFF: Fast and consistent SHApley eFfect estimates via random Forests | no | no |  | indexed, queries missed it |
| Generalized Hoeffding-Sobol Decomposition for Dependent Variables - Ap | yes | yes | 111 |  |
| Generalized Functional ANOVA Diagnostics for High-Dimensional Function | yes | yes | 47 |  |
| Predictive learning via rule ensembles | no | no |  | indexed, queries missed it |
| Exact Functional ANOVA Decomposition for Categorical Inputs Models | yes | no | 2 | screened out |

Recall after retrieval 50% (BELOW 70%).

## credal-dro
Run `lit2-credal-dro-b`: 12 queries, 160 candidates, 65 kept by the screen, 6 claims drafted, 6 kept (first-draft failures 1).

| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 5 of 8 | 62% |
| Kept by the screen | 5 | 62% |
| In the top 30 by rank | 2 | 25% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Bulk-Calibrated Credal Ambiguity Sets: Fast, Tractable Decision Making | no | no |  | indexed, queries missed it |
| Data-driven Distributionally Robust Optimization Using the Wasserstein | yes | yes | 4 |  |
| Quantifying Distributional Model Risk via Optimal Transport | yes | yes | 150 |  |
| Learning Models with Uniform Performance via Distributionally Robust O | yes | yes | 19 |  |
| Certifying Some Distributional Robustness with Principled Adversarial  | no | no |  | indexed, queries missed it |
| Aleatoric and Epistemic Uncertainty in Machine Learning: An Introducti | no | no |  | indexed, queries missed it |
| Robust Solutions of Optimization Problems Affected by Uncertain Probab | yes | yes | 122 |  |
| Distributionally Robust Optimization Under Moment Uncertainty with App | yes | yes | 124 |  |

Recall after retrieval 62% (BELOW 70%).

## llm-judge-numbers
Run `lit2-llm-judge-numbers-b`: 12 queries, 160 candidates, 25 kept by the screen, 15 claims drafted, 15 kept (first-draft failures 7).

| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 2 of 10 | 20% |
| Kept by the screen | 2 | 20% |
| In the top 30 by rank | 2 | 20% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | yes | yes | 20 |  |
| Large Language Models are not Fair Evaluators | no | no |  | indexed, queries missed it |
| LLM Evaluators Recognize and Favor Their Own Generations | no | no |  | indexed, queries missed it |
| Replacing Judges with Juries: Evaluating LLM Generations with a Panel  | no | no |  | indexed, queries missed it |
| Judging the Judges: Evaluating Alignment and Vulnerabilities in LLMs-a | no | no |  | indexed, queries missed it |
| A Survey on LLM-as-a-Judge | yes | yes | 3 |  |
| FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long | no | no |  | indexed, queries missed it |
| Fact or Fiction: Verifying Scientific Claims | no | no |  | indexed, queries missed it |
| TabFact: A Large-scale Dataset for Table-based Fact Verification | no | no |  | indexed, queries missed it |
| G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment | no | no |  | indexed, queries missed it |

Recall after retrieval 20% (BELOW 70%).
