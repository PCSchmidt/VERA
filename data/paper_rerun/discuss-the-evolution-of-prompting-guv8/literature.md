## Literature review

The prompt-engineering sources define the practice as instruction design that leaves model parameters untouched [R1]. A catalog of prompt patterns frames prompts as a form of programming that can customize outputs and interactions [R11]. The Prompt Report describes the field as suffering from conflicting terminology and a fragmented ontological understanding [R48]. A practitioner-based study calls prompt engineering a critical yet loosely defined skill [R39].

For context engineering, the sources describe a shift beyond the prompt text itself. A survey of prompt and context engineering describes analyzing the shift from input-level linguistic control to system-level contextual orchestration [R2]. An oncology commentary argues that the future lies in better context, not just better prompts [R105]. The ACE framework defines context adaptation as modifying inputs with instructions, strategies, or evidence rather than weight updates [R94]. A production-oriented survey lists context engineering alongside dynamic tool retrieval, execution methods, memory, and evaluation [R44]. Empirical work attributes degradation to context itself, naming context rot as the progressive degradation of agent reasoning quality as the context window fills [R20].

The harness literature defines the harness as the structure around a fixed model. One survey understands the agent harness as the external execution support structure built around the model [R29]. Another source names the memory substrate, context constructor, skill-routing layer, orchestration loop, and verification-and-governance layer as harness components [R26]. A modular harness for games composes perception, memory, and reasoning components [R28]. A harness for tool-integrated agents is described as scaffolding determining which tools are exposed and how they are described [R42]. The externalization review presents harness engineering as the unification layer coordinating memory, skills, and protocols [R87]. The same review traces a historical progression from weights to context to harness [R87].

Sources on agentic harnesses stress the loop and orchestration of multiple agents. The agent-loop survey takes the observe-decide-act loop as its unit of analysis [R8]. HeavySkill describes agentic harnesses as orchestration frameworks coordinating multiple agents with memory, skills, and tool use [R30]. Agentic RAG is described as going beyond the limits of traditional RAG by embedding autonomous AI agents into the RAG pipeline [R17].

Evaluation is the clearest component attributed to the harness stage. A harness-aware evaluation survey reports that changing the execution system around a fixed model can reverse model rankings [R6]. UniACE reports that a benchmark score reflects a complete model–harness–environment configuration [R84].

Several limits remain. The sources do not establish a shared definition separating context engineering from harness engineering, and the stage boundaries are drawn differently by each author. Their evidence is mostly surveys, small or synthetic experiments, and single-domain cases, so generalizing component attributions across stages is not supported. One context-rot paper explicitly says no published study has tested its joint hypothesis [R20].

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 46 and set aside 74; 6 were read in full text and 40 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R1] Pranab Sahoo, Ayush Singh, Sriparna Saha et al.. A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications. 2024. arXiv:2402.07927. https://arxiv.org/abs/2402.07927
[R2] Tonmoy Debnath, Md Nurul Absar Siddiky, Muhammad Enayetur Rahman et al.. A comprehensive survey of prompt engineering and context engineering techniques in large language models. 2026. doi:10.1016/j.cosrev.2026.100979. https://doi.org/10.1016/j.cosrev.2026.100979
[R6] Ahmed Y. Radwan, Athanasios V. Vasilakos, Shaina Raza. Harness-Aware Evaluation of LLM Agents: Systems, Benchmarks, and Protocols. 2026. doi:10.20944/preprints202609.2140.v1. https://doi.org/10.20944/preprints202609.2140.v1
[R8] Jungseob Lee, Chanjun Park. The Agent Loop: A Survey of Control Strategies, Skills, and Harnesses for LLM Agents. 2026. doi:10.2139/ssrn.7186738. https://doi.org/10.2139/ssrn.7186738
[R11] Jules White, Quchen Fu, Sam Hays et al.. A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT. 2023. doi:10.48550/arxiv.2302.11382. https://doi.org/10.48550/arxiv.2302.11382
[R17] Aditi Singh, Abul Ehtesham, Saket Kumar et al.. Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG. 2025. doi:10.48550/arxiv.2501.09136. https://doi.org/10.48550/arxiv.2501.09136
[R20] Abrar Shahriar, Qurat-ul-ain Mastoi. Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems. 2026. doi:10.2139/ssrn.7344299. https://doi.org/10.2139/ssrn.7344299
[R26] Shangding Gu. From Model Scaling to System Scaling: Scaling the Harness in Agentic AI. 2026. arXiv:2605.26112. https://arxiv.org/abs/2605.26112
[R28] Yuxuan Zhang, Haoyang Yu, Lanxiang Hu et al.. General Modular Harness for LLM Agents in Multi-Turn Gaming Environments. 2025. arXiv:2507.11633. https://arxiv.org/abs/2507.11633
[R29] Jieni Li, Yuan Wu, Yi Chang. Harness Engineering for LLM Agents: A Survey of Harness Component Taxonomy, Evaluation, and Model–Harness Coevolution. 2026. doi:10.20944/preprints202606.2203.v1. https://doi.org/10.20944/preprints202606.2203.v1
[R30] Jianing Wang, Linsen Guo, Zhengyu Chen et al.. HeavySkill: Heavy Thinking as the Inner Skill in Agentic Harness. 2026. arXiv:2605.02396. https://arxiv.org/abs/2605.02396
[R39] Dominic Vincent Ligot. Prompting in the Wild: A Qualitative Taxonomy of Practitioner-Driven Prompt Engineering Methods. 2026. doi:10.2139/ssrn.6129946. https://doi.org/10.2139/ssrn.6129946
[R42] Kyungmin Kim, Youngbin Choi, Seoyeon Lee et al.. The Interplay of Harness Design and Post-Training in LLM Agents. 2026. doi:10.48550/arxiv.2606.25447. https://doi.org/10.48550/arxiv.2606.25447
[R44] Elias Lumer, Anmol Gulati, Faheem Nizar et al.. Tool and Agent Selection for Large Language Model Agents in Production: A Survey. 2026. doi:10.1109/CAI68641.2026.11536377. https://doi.org/10.1109/CAI68641.2026.11536377
[R48] Sander Schulhoff, Michael Ilie, Nishant Balepur et al.. The Prompt Report: A Systematic Survey of Prompt Engineering Techniques. 2024. doi:10.48550/arxiv.2406.06608. https://doi.org/10.48550/arxiv.2406.06608
[R84] Pengyu Zhu, Lijun Li, Yaxing Lyu et al.. UniACE: A Unified Framework for Evaluating LLM Agentic Capabilities. 2026. doi:10.48550/arxiv.2605.27898. https://doi.org/10.48550/arxiv.2605.27898
[R87] Chenyu Zhou, Huacan Chai, Wenteng Chen et al.. Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering. 2026. arXiv:2604.08224. https://arxiv.org/abs/2604.08224
[R94] Qizheng Zhang, Changran Hu, Shubhangi Upasani et al.. Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models. 2025. arXiv:2510.04618. https://arxiv.org/abs/2510.04618
[R105] Nikhil Thaker, Sanjay Juneja. From Prompt Engineering to Context Engineering: Why Precision Oncology Needs Context. 2025. doi:10.1177/2993091x251388462. https://doi.org/10.1177/2993091x251388462
