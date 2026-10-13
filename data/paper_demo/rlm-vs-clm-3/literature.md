## Literature review

The RLM paper describes RLMs as a general inference paradigm in which long prompts are treated as part of an external environment [R8]. A follow-up study (SRLM) treats the long context as an external variable accessible within a sandboxed execution programming environment [R9]. Context-centric approaches instead shrink what the model reads: the In-context Autoencoder compresses a long context into short compact memory slots that can be directly conditioned on by the LLM [R28]. Highlight-Then-Summarize takes a compress-then-reason route, first identifying question-relevant evidence and then integrating it into a compact summary [R1].

The Chained RLM authors state that the RLM approach improves long-context inference without changing model weights [R5]. The survey notes that gist-token methods typically require modifying the parameters of the LLM [R12].

On output quality, the original RLM paper reports strong results against common scaffolds at comparable cost [R8]. Later work qualifies this. SRLM authors report that recursion is not the main driver of RLM performance [R9]. A reproduction study found that deeper recursion degraded performance and inflated time and token costs [R75]. The λ-RLM authors also criticise open-ended REPL code generation as hard to verify and predict [R86].

On cost for the context-centric side, Cartridges match in-context learning with far less memory [R94]. Evidence from coding agents warns that fewer tokens do not guarantee lower cost [R78]. The same study found that aggressive compression reduced successful patch application on a SWE-bench Go subset [R78].

In Chained RLM, intermediate artifacts from each staged computation can be inspected, corrected, and extended by a later fresh inference by the same model [R5]. None of the supplied passages evaluates reuse of RLM execution traces on production coding tasks. Production coding evidence for RLMs specifically is also absent, and no passage compares RLMs and context-compression models head to head on coding quality or billed cost. One paper notes that no published empirical study has tested how codebase scale drives context growth and tool-call degradation in agentic coding systems [R21]. The suitability of either approach for production coding is therefore not established by these sources.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 26 and set aside 94; 6 were read in full text and 20 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R1] Zhaoyuan Xia, Qinghongbing Xie, Yung Xiang Hue et al.. Highlight-Then-Summarize: Learning to Compress Evidence for Long-Context Understanding. 2026. arXiv:2609.31382. https://arxiv.org/abs/2609.31382
[R5] Purbesh Mitra, Şennur Ulukuş. Chained Recursive Language Models for Multi-Iteration Reasoning. 2026. doi:10.48550/arxiv.2608.05124. https://doi.org/10.48550/arxiv.2608.05124
[R8] Alex L. Zhang, T. Kraska, Omar Khattab. Recursive Language Models. 2025. arXiv:2512.24601. https://arxiv.org/abs/2512.24601
[R9] Keivan Alizadeh, Parshin Shojaee, Minsik Cho et al.. Recursive Language Models Meet Uncertainty: The Surprising Effectiveness of Self-Reflective Program Search for Long Context. 2026. arXiv:2603.15653. https://arxiv.org/abs/2603.15653
[R12] Jiaheng Liu, Dawei Zhu, Zhiqi Bai et al.. A Comprehensive Survey on Long Context Language Modeling. 2025. arXiv:2503.17407. https://arxiv.org/abs/2503.17407
[R21] Abrar Shahriar, Qurat-ul-ain Mastoi. Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems. 2026. doi:10.2139/ssrn.7344299. https://doi.org/10.2139/ssrn.7344299
[R28] Tao Ge, Jing Hu, Wang, Lei et al.. In-context Autoencoder for Context Compression in a Large Language Model. 2023. doi:10.48550/arxiv.2307.06945. https://doi.org/10.48550/arxiv.2307.06945
[R75] D. Wang. Think, But Don't Overthink: Reproducing Recursive Language Models. 2026. arXiv:2603.02615. https://arxiv.org/abs/2603.02615
[R78] Sarel Weinberger, Amir Hozez. Token Reduction Is Not Cost Reduction. 2026. doi:10.48550/arxiv.2607.12161. https://doi.org/10.48550/arxiv.2607.12161
[R86] Amartya Roy, Rasul Tutunov, Xiao-Tong Ji et al.. The Y-Combinator for LLMs: Solving Long-Context Rot with λ-Calculus. 2026. arXiv:2603.20105. https://arxiv.org/abs/2603.20105
[R94] Sabri Eyuboglu, Ryan Ehrlich, Simran Arora et al.. Cartridges: Lightweight and general-purpose long context representations via self-study. 2025. arXiv:2506.06266. https://arxiv.org/abs/2506.06266
