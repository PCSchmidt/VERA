## Literature review

The AgentOps taxonomy study states that tasks in agent traces carry a status field [R3]. The same study reports that every tool it surveyed supports tracing [R3]. The survey on evidence tracing notes that OpenTelemetry models executions as traces and spans [R40]. AgentTelemetry reports that OpenTelemetry's GenAI conventions leave several orchestration phases without span-level representation [R117].

For SWE-agent, the authors released their trajectories and evaluation execution traces [R5]. A study of three agents, RepairAgent, AutoCodeRover, and OpenHands, reports that its authors unified their interaction logs into a common format, capturing 120 trajectories and 2,822 LLM interactions [R114]. Another study describes earlier work as normalizing agent logs into thought-action-result triples [R15]. The OpenHands SDK paper mentions event sourcing overhead, which points to event-based state [R72].

Source-level analysis of Claude Code describes its session storage as append-oriented [R12]. The Claude Code source analysis states that the system does not use embeddings or a vector similarity index for memory retrieval; it uses an LLM-based scan of memory-file headers to select up to five relevant files on demand [R12]. The grite coordination work describes a substrate that stores its records inside git itself, with an append-only, signed event log that captures the coordination process directly [R84].

The supplied passages do not establish how Aider or Codex CLI structure their traces, since the Codex CLI entry is only a short introduction. The passages also give no report of traces from these harnesses being stored or mined in vector databases, and they do not compare commit-history representation across harnesses.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 20 and set aside 100; 6 were read in full text and 14 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R3] Dong, Liming, Qinghua Lu, Zhu, Liming. AgentOps: Enabling Observability of LLM Agents. 2024. arXiv:2411.05285. https://arxiv.org/abs/2411.05285
[R5] Yang, John, Jimenez, Carlos E., Alexander Wettig et al.. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. 2024. arXiv:2405.15793. https://arxiv.org/abs/2405.15793
[R12] Jiacheng Liu, Xiaohan Zhao, Xinyi Shang et al.. Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems. 2026. arXiv:2604.14228. https://arxiv.org/abs/2604.14228
[R15] X Zhao, Han Li, Shuaiting Li et al.. Failure as a Process: An Anatomy of CLI Coding Agent Trajectories. 2026. doi:10.48550/arxiv.2607.09510. https://doi.org/10.48550/arxiv.2607.09510
[R40] Yiqi Wang, Jiaqi Zhang, Zhangkai Wu et al.. From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents. 2026. arXiv:2606.04990. https://arxiv.org/abs/2606.04990
[R72] Xingyao Wang, Simon Rosenberg, Juan Michelini et al.. The OpenHands Software Agent SDK: A Composable and Extensible Foundation for Production Agents. 2025. arXiv:2511.03690. https://arxiv.org/abs/2511.03690
[R84] Dipankar Sarkar. Before the Pull Request: Mining Multi-Agent Coordination. 2026. doi:10.48550/arxiv.2606.19616. https://doi.org/10.48550/arxiv.2606.19616
[R114] Islem Bouzenia, Michael Pradel. Understanding Software Engineering Agents: A Study of Thought-Action-Result Trajectories. 2025. arXiv:2506.18824. https://arxiv.org/abs/2506.18824
[R117] Krishna Chaitanya Balusu. AgentTelemetry: A Fault Detection Benchmark and Toolkit for LLM Agent Observability. 2026. doi:10.1145/3805760.3814931. https://doi.org/10.1145/3805760.3814931
