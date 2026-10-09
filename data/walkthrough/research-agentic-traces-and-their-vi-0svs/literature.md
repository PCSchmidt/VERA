## Literature review

The survey literature frames structured traces as a foundation for accountability in LLM agents. The R3 survey states that final-answer accuracy alone cannot explain how an output was produced [R3]. The AgentOps paper reports that most existing DevOps tools for agents focus on LLM-specific metrics and prompt management [R10]. The Traccia paper argues that general observability tools record physical execution but lack semantic insight [R42].

Trajectory studies in software engineering suggest that traces carry information that outcome metrics hide. The R4 study concludes that agent trajectories encapsulate behavioural insights often obscured by outcome-only evaluation [R4]. The two studies thus differ on trajectory length as a failure signal, although R4 examined three agents and R12 a much larger set.

Scale and usability of trace analysis are recurring concerns. The SeaView authors note that SWE agent trajectories are hard to analyze because they sometimes exceed LLM sequence length [R123]. The R44 authors built an LLM-as-a-Judge pipeline to make annotation of multi-agent traces scalable [R44]. Work on conventional distributed tracing reports a measurable cost, with throughput reductions of 19-80% in one study [R109]. The Tracezip authors say sampling forces a trade-off between completeness of tracing and system overhead [R80].

Several sources remain proposals rather than evidence of viability at scale. The Clinical AgentOps paper states that whether its trajectory-level controls work is open [R46]. The llmmas-otel tool reports only initial validation on a minimal demo workflow and one real multi-agent system [R69]. The passages do not establish that structured traces summarize or audit high-volume software-development agent workflows at production scale, and they give no cost figures for agent-specific tracing.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 39 and set aside 81; 6 were read in full text and 33 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R3] Yiqi Wang, Jiaqi Zhang, Zhangkai Wu et al.. From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents. 2026. arXiv:2606.04990. https://arxiv.org/abs/2606.04990
[R4] Oorja Majgaonkar, Zhiwei Fei, Xiang Li et al.. Understanding Code Agent Behaviour: An Empirical Study of Success and Failure Trajectories. 2025. arXiv:2511.00197. https://arxiv.org/abs/2511.00197
[R10] Dong, Liming, Qinghua Lu, Zhu, Liming. AgentOps: Enabling Observability of LLM Agents. 2024. arXiv:2411.05285. https://arxiv.org/abs/2411.05285
[R42] Nutan Kumar Naik, Aditya Kumar Saroj, Vijay Prasad Poudel et al.. Traccia: An OpenTelemetry-Based Governance Platform for AI Systems. 2026. arXiv:2607.14309. https://arxiv.org/abs/2607.14309
[R44] M. Cemri, Melissa Z. Pan, Shuyi Yang et al.. Why Do Multi-Agent LLM Systems Fail?. 2025. arXiv:2503.13657. https://arxiv.org/abs/2503.13657
[R46] Kamal Bisht, Raj Kumar. Clinical AgentOps: Runtime Governance for Autonomous AI Healthcare Agents. 2026. doi:10.36948/ijfmr.2026.v08i04.85225. https://doi.org/10.36948/ijfmr.2026.v08i04.85225
[R69] Zahra Seyedghorban, Egor Klimov, A. van Deursen et al.. Observability and Fault Injection for LLM-Based Multi-Agent Systems in Software Engineering. 2026. arXiv:2608.24271. https://arxiv.org/abs/2608.24271
[R80] Zhuangbin Chen, Junsong Pu, Zibin Zheng. Tracezip: Efficient Distributed Tracing via Trace Compression. 2025. doi:10.1145/3728888. https://doi.org/10.1145/3728888
[R109] Anders Nõu, Sacheendra Talluri, Alexandru Iosup et al.. Investigating Performance Overhead of Distributed Tracing in Microservices and Serverless Systems. 2025. doi:10.1145/3680256.3721316. https://doi.org/10.1145/3680256.3721316
[R123] Timothy Bula, Saurabh Pujar, Luca Buratti et al.. SeaView: Software Engineering Agent Visual Interface for Enhanced Workflow. 2025. doi:10.48550/arxiv.2504.08696. https://doi.org/10.48550/arxiv.2504.08696
