# Retrieval: recall of the key papers
Recall is measured against the key-paper lists fixed and hashed before the first retrieval (`data/topics/manifest.json`). T5 reverse-if (1): a recall after retrieval below 70% opens T5. Starting value, not a target.

## credal-dro
Run `scope-credal-dro-2`: 100 candidates retrieved, 32 kept by the relevance screen, 25 unsure.
| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 3 of 8 | 38% |
| Kept by the screen | 3 | 38% |
| In the top 30 by rank | 1 | 12% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Bulk-Calibrated Credal Ambiguity Sets: Fast, Tractable Decision Making | no | no |  | indexed, queries missed it |
| Data-driven Distributionally Robust Optimization Using the Wasserstein | yes | yes | 7 |  |
| Quantifying Distributional Model Risk via Optimal Transport | no | no |  | indexed, queries missed it |
| Learning Models with Uniform Performance via Distributionally Robust O | no | no |  | indexed, queries missed it |
| Certifying Some Distributional Robustness with Principled Adversarial  | no | no |  | indexed, queries missed it |
| Aleatoric and Epistemic Uncertainty in Machine Learning: An Introducti | no | no |  | indexed, queries missed it |
| Robust Solutions of Optimization Problems Affected by Uncertain Probab | yes | yes | 69 |  |
| Distributionally Robust Optimization Under Moment Uncertainty with App | yes | yes | 66 |  |

Verdict on the starting threshold: recall after retrieval 38% (BELOW 70%).

## llm-judge-numbers
Run `scope-llm-judge-numbers-3`: 60 candidates retrieved, 11 kept by the relevance screen, 6 unsure.
| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 2 of 10 | 20% |
| Kept by the screen | 1 | 10% |
| In the top 30 by rank | 1 | 10% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | no | no |  | indexed, queries missed it |
| Large Language Models are not Fair Evaluators | no | no |  | indexed, queries missed it |
| LLM Evaluators Recognize and Favor Their Own Generations | no | no |  | indexed, queries missed it |
| Replacing Judges with Juries: Evaluating LLM Generations with a Panel  | no | no |  | indexed, queries missed it |
| Judging the Judges: Evaluating Alignment and Vulnerabilities in LLMs-a | no | no |  | indexed, queries missed it |
| A Survey on LLM-as-a-Judge | yes | no | 45 | screened out |
| FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long | no | no |  | indexed, queries missed it |
| Fact or Fiction: Verifying Scientific Claims | no | no |  | indexed, queries missed it |
| TabFact: A Large-scale Dataset for Table-based Fact Verification | yes | yes | 14 |  |
| G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment | no | no |  | indexed, queries missed it |

Verdict on the starting threshold: recall after retrieval 20% (BELOW 70%).

## tree-explain
Run `scope-tree-explain-2`: 100 candidates retrieved, 31 kept by the relevance screen, 13 unsure.
| | Key papers found | Share |
|---|---|---|
| Retrieved (before the screen) | 7 of 10 | 70% |
| Kept by the screen | 7 | 70% |
| In the top 30 by rank | 4 | 40% |

| Key paper | Found | Kept | Position | Miss, classified |
|---|---|---|---|---|
| Tree Ensemble Explainability through the Hoeffding Functional Decompos | yes | yes | 5 |  |
| Explainable AI for Trees: From Local Explanations to Global Understand | no | no |  | indexed, queries missed it |
| A Unified Approach to Interpreting Model Predictions | yes | yes | 66 |  |
| Explaining individual predictions when features are dependent: More ac | no | no |  | indexed, queries missed it |
| Purifying Interaction Effects with the Functional ANOVA: An Efficient  | yes | yes | 62 |  |
| SHAFF: Fast and consistent SHApley eFfect estimates via random Forests | no | no |  | indexed, queries missed it |
| Generalized Hoeffding-Sobol Decomposition for Dependent Variables - Ap | yes | yes | 58 |  |
| Generalized Functional ANOVA Diagnostics for High-Dimensional Function | yes | yes | 11 |  |
| Predictive learning via rule ensembles | yes | yes | 13 |  |
| Exact Functional ANOVA Decomposition for Categorical Inputs Models | yes | yes | 15 |  |

Verdict on the starting threshold: recall after retrieval 70% (at or above 70%).
