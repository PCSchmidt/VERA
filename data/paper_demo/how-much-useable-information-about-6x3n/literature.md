## Literature review

The supplied sources describe several categories of information that could in principle be recovered from agent and software artifacts, but most evidence concerns the artifacts around agents rather than agent traces themselves. The SWE-agent authors released trajectories as part of their open-source artifacts [R28]. An empirical study of agent trajectories examined the execution traces that capture the steps agents take when resolving issues [R35].

For failure and repair history, the trajectory studies report behavioural regularities. One study found that failed trajectories differ in length and variance from successful ones [R35]. The same study found that agents that gather context before editing and invest in validation succeed more often [R81]. Work on failure attribution reports that diagnoses derived from trajectories can feed back into agent improvement [R39]. A trace-debugging method reported that, calibrated against a deterministic replay oracle across 37 trace families, a single learning-to-rank gradient-boosted predictor raises per-trace localization (Branch Recall@5) from 0.73 to 0.93 on held-out families at zero oracle-replay cost [R57].

For design rationale, the evidence comes from issue logs, not agent traces. DRMiner reported that rationales mined from Jira logs improved LLM-based repair [R13]. A practice report from scientific software states that off-the-shelf coding agents leave decision trails that are hard to reconstruct [R59].

For requirements traceability, the literature shows LLM-based recovery is promising but imperfect. One proposal notes that agent-driven development produces no intermediate artifacts, so traceability cannot be established [R67]. A bidirectional-recovery traceability technique reported that its bidirectional convergence approach increased use-case recovery coverage from 65.5% to 75.1%, a gain of 9.6 percentage points, and improved trace-link recall [R67]. An ensemble study of small LLMs for inter-requirements traceability reported that, while its LLM-based ensemble approach achieves comparable F2-scores to IR methods, it lags in precision [R11]. A traceability overview noted that conversational LLM interfaces are an intuitive way to create and explain trace links, but it is not yet clear how these approaches will scale [R20].

For test intent and specification, sources describe inference of intent as the hard part. The AutoCodeRover authors state where the difficulty of repair lies [R10]. A survey of test-driven LLM work cautions that passing tests is insufficient evidence [R107]. An OSS-Fuzz study found code similarity does not measure patch quality [R90].

Overall, the sources do not establish that design rationale, requirements links or test intent can be reliably recovered from agent traces specifically. They also do not show that such recovered information improves long-term maintainability or robustness, and the cited benchmark evidence concerns issue resolution. SWE-bench-Live evaluated state-of-the-art agent frameworks and LLMs and reported a substantial performance gap compared to static benchmarks like SWE-bench, even under controlled evaluation conditions [R29].

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 48 and set aside 72; 6 were read in full text and 42 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R10] Yuntong Zhang, Haifeng Ruan, Zhiyu Fan et al.. AutoCodeRover: Autonomous Program Improvement. 2024. arXiv:2404.05427. https://arxiv.org/abs/2404.05427
[R11] Dominik Fuchß, Stefan Schwedt, Jan Keim et al.. Beyond Retrieval: A Study of Using LLM Ensembles for Candidate Filtering in Requirements Traceability. 2025. doi:10.1109/REW66121.2025.00006. https://doi.org/10.1109/REW66121.2025.00006
[R13] Jiuang Zhao, Zi-Tian Yang, Li Zhang et al.. DRMiner: Extracting Latent Design Rationale from Jira Issue Logs. 2024. doi:10.1145/3691620.3695019. https://doi.org/10.1145/3691620.3695019
[R20] Jin L. C. Guo, Jan-Philipp Steghöfer, Andreas Vogelsang et al.. Natural Language Processing for Requirements Traceability. 2024. arXiv:2405.10845. https://arxiv.org/abs/2405.10845
[R28] Yang, John, Jimenez, Carlos E., Alexander Wettig et al.. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. 2024. arXiv:2405.15793. https://arxiv.org/abs/2405.15793
[R29] Linghao Zhang, Shilin He, Chaoyun Zhang et al.. SWE-bench Goes Live!. 2025. arXiv:2505.23419. https://arxiv.org/abs/2505.23419
[R35] Oorja Majgaonkar, Zhiwei Fei, Xiang Li et al.. Understanding Code Agent Behaviour: An Empirical Study of Success and Failure Trajectories. 2025. doi:10.48550/arxiv.2511.00197. https://doi.org/10.48550/arxiv.2511.00197
[R39] Bo Deng, Xinlei Zheng, Yi Wei et al.. DeFA: Dependency-Guided Failure Attribution for LLM Agents. 2026. arXiv:2610.01256. https://arxiv.org/abs/2610.01256
[R57] Hyeonjeong Cha, Daein Weon, Dong Ho Kang. Knowledge-Based Zero-Replay Debugging of Multi-Agent LLM Traces. 2026. arXiv:2606.14805. https://arxiv.org/abs/2606.14805
[R59] Landung Setiawan, Anant Mittal, Cordero Core et al.. LLMoxie: Exploring Agentic AI for Scientific Software Development. 2026. arXiv:2607.02703. https://arxiv.org/abs/2607.02703
[R67] Jinhyup Lee, Janghwan Kim, Chaeyun Seo et al.. Requirement Traceability based on Bidirectional Convergence of Intermediate Artifact Recovery for AI Software Development. 2026. doi:10.30693/smj.2026.15.8.89. https://doi.org/10.30693/smj.2026.15.8.89
[R81] Tural Mehtiyev, Wesley K. G. Assunção. Beyond Resolution Rates: Behavioral Drivers of Coding Agent Success and Failure. 2026. doi:10.48550/arxiv.2604.02547. https://doi.org/10.48550/arxiv.2604.02547
[R90] Yuntong Zhang, Jiawei Wang, Dominic Berzin et al.. Fixing Security Vulnerabilities with AI in OSS-Fuzz. 2024. arXiv:2411.03346. https://arxiv.org/abs/2411.03346
[R107] Yunhao Liang, Chengguang Gan, Ruixuan Ying et al.. Test-Driven Approaches to Software Engineering with Large Language Models: A Survey of Phases, Tasks, and Agent Skills. 2026. https://openalex.org/W7213372607. https://openalex.org/W7213372607
