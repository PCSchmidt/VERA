## Literature review

The evidence supplied does not include passages on MLE-bench's medal cutoffs, so that measure cannot be assessed here. The CORE-Bench authors describe their correctness rule for reproduction tasks [R11]. A study of novelty judges reports that prompt wording can strongly change verdicts [R11]. A later case study of CORE-Bench reports that the benchmark had construct-validity problems [R52].

PaperBench grades replications against hierarchical rubrics with an LLM judge [R24]. The PaperBench authors report how well their best judge matches human graders [R24]. The PaperBench authors also acknowledge that judge accuracy needs further work [R24]. SciReplicate-Bench addresses contamination by its choice of paper dates [R28].

Work on judge reliability shows that single judgments can be unstable. A study of repeated identical evaluations found that pairwise preferences flip often [R30]. Work on clinical agents argues that benchmarks typically score one run per task [R27]. FIRE-Bench reports high variance across runs for research agents [R113]. The sources do not show whether PaperBench or MLE-bench medal results change across repeated runs.

RQ-Bench found that LLM judges consistently rate model-generated research questions as highly novel, which the authors call a novelty mirage [R2]. The CORE-Bench authors say that building the benchmark on public repositories permits periodic updates [R58]. HindSight reports that its future-impact scores correlate negatively with LLM-judged novelty [R87]. A large human study found LLM ideas were judged more novel than expert ideas [R107]. OpenNovelty instead grounds novelty assessments in retrieved prior work [R59]. The supplied passages give no validation showing that retrieval-grounded novelty checking is accurate.

A survey of 80 AI-scientist systems states that LLM judging is the dominant evaluator [R36]. A contamination survey cautions that an LLM used for evaluation may itself be contaminated [R10]. Contamination of these particular agent benchmarks is not measured in the supplied evidence.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 160 candidate papers. A relevance screen kept 41 and set aside 119; 6 were read in full text and 35 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R2] Soumitra Sinhahajari, Navonil Majumder, Soujanya Poria. On the Limits of LLM-as-Judge for Scientific Novelty Assessment. 2026. arXiv:2606.12071. https://arxiv.org/abs/2606.12071
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
[R87] Bo Jiang. HindSight: Evaluating LLM-Generated Research Ideas via Future Impact. 2026. arXiv:2603.15164. https://arxiv.org/abs/2603.15164
[R107] Chenglei Si, Diyi Yang, Tatsunori Hashimoto. Can LLMs Generate Novel Research Ideas? A Large-Scale Human Study with 100+ NLP Researchers. 2024. arXiv:2409.04109. https://arxiv.org/abs/2409.04109
[R113] Zhen Wang, Fan Bai, Zhongyan Luo et al.. FIRE-Bench: Evaluating AI Agents on the Rediscovery of Scientific Insights. 2026. doi:10.48550/arxiv.2602.02905. https://doi.org/10.48550/arxiv.2602.02905
