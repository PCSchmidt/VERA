## Literature review

CORE-Bench defines correctness by comparing agent answers with repeated manual reproductions [R11]. Its authors note that building on public repositories allows periodic updates [R11]. A later case study of CORE-Bench reports that it surfaced threats to construct validity in CORE-Bench Hard that are difficult to anticipate with less capable agents [R52].

PaperBench uses an LLM-based judge to automatically grade replication attempts against rubrics [R24]. Its best judge reached an F1 of 0.83 against human gold labels [R24]. The authors themselves say more work is needed on judge accuracy [R24]. SciReplicate-Bench argues that PaperBench and Paper2CodeBench rely substantially on manual assessment criteria and LLM-based correctness judgments, introducing potential inconsistencies and reliability concerns [R28]. SciReplicate-Bench states that its recent publication window was deliberately chosen to minimize the risk of data leakage [R28].

One study finds that pairwise LLM-judge preferences flip across identical runs: on average 13.6% of the time [R30]. Another reports that exact-match agreement overstates judge ability [R62]. A survey of AI-scientist systems finds LLM-as-judge is the most common evaluator [R36].

Another study reports that across six judges, small prompt design choices have large consequences for novelty verdicts [R58]. HindSight reports that LLM-judged novelty correlates negatively with future-impact scores [R87]. OpenNovelty instead grounds assessments in retrieved prior work [R59]. The human ideation study acknowledges that human judgements of novelty can be difficult, even by experts [R107].

On variance, a clinical-agent study notes that benchmarks usually score one run per task [R27]. FIRE-Bench reports high variance across runs [R113]. A contamination survey cautions that an LLM used for automatic evaluation may itself be contaminated [R10].

What is not established: the supplied passages do not test medal cutoffs in MLE-bench for run-to-run variance, nor measure contamination of PaperBench or CORE-Bench specifically. They also do not show that retrieval-grounded novelty checks such as OpenNovelty are validated against expert judgment.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 41 and set aside 79; 6 were read in full text and 35 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R10] Cheng Xu, Shuhao Guan, Derek Greene et al.. Benchmark Data Contamination of Large Language Models: A Survey. 2024. doi:10.48550/arxiv.2406.04244. https://doi.org/10.48550/arxiv.2406.04244
[R11] Zachary S. Siegel, Sayash Kapoor, Nitya Nadgir et al.. CORE-Bench: Fostering the Credibility of Published Research Through a Computational Reproducibility Agent Benchmark. 2024. arXiv:2409.11363. https://arxiv.org/abs/2409.11363
[R24] Giulio Starace, Oliver Jaffe, Dane Sherburn et al.. PaperBench: Evaluating AI's Ability to Replicate AI Research. 2025. arXiv:2504.01848. https://arxiv.org/abs/2504.01848
[R27] Rohith Reddy Bellibatlu, Manpreet Singh, Zhoutian Han et al.. Same Patient, Different Order: Action-Level Reliability of Clinical LLM Agents Under Repeated Runs. 2026. arXiv:2609.13582. https://arxiv.org/abs/2609.13582
[R28] Yanzheng Xiang, Hanqi Yan, Shuyin Ouyang et al.. SciReplicate-Bench: Benchmarking LLMs in Agent-driven Algorithmic Reproduction from Research Papers. 2025. arXiv:2504.00255. https://arxiv.org/abs/2504.00255
[R30] Abel Yagubyan. The Coin Flip Judge? Reliability and Bias in LLM-as-a-Judge Evaluation. 2026. arXiv:2606.13685. https://arxiv.org/abs/2606.13685
[R36] Jemin George. A Survey of 80 "AI Scientist" Systems: From Evaluator Quality to Validated Discovery and Feedback Loops. 2026. doi:10.2139/ssrn.6889440. https://doi.org/10.2139/ssrn.6889440
[R52] Nitya Nadgir, Sayash Kapoor, K. Liu et al.. Life After Benchmark Saturation: A Case Study of CORE-Bench. 2026. arXiv:2606.26158. https://arxiv.org/abs/2606.26158
[R58] Noy Sternlicht, Simra Shahid, Peter Jansen et al.. Old Ideas, Novel Problems: The Instability of LLM-Based Novelty Evaluation. 2026. arXiv:2610.02022. https://arxiv.org/abs/2610.02022
[R59] Ming Zhang, Kexin Tan, Yueyuan Huang et al.. OpenNovelty: An LLM-powered Agentic System for Verifiable Scholarly Novelty Assessment. 2026. doi:10.48550/arxiv.2601.01576. https://doi.org/10.48550/arxiv.2601.01576
[R62] Justin Norman, Michael U. Rivera, D. Alex Hughes. Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge Models Across Agreement, Consistency, and Bias. 2026. arXiv:2606.19544. https://arxiv.org/abs/2606.19544
[R87] Bo Jiang. HindSight: Evaluating LLM-Generated Research Ideas via Future Impact. 2026. arXiv:2603.15164. https://arxiv.org/abs/2603.15164
[R107] Chenglei Si, Diyi Yang, Tatsunori Hashimoto. Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers. 2024. arXiv:2409.04109. https://arxiv.org/abs/2409.04109
[R113] Zhen Wang, Fan Bai, Zhongyan Luo et al.. FIRE-Bench: Evaluating AI Agents on the Rediscovery of Scientific Insights. 2026. doi:10.48550/arxiv.2602.02905. https://doi.org/10.48550/arxiv.2602.02905
