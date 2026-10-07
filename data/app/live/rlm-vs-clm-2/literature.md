## Literature review

The RLM paper proposes a general inference paradigm in which long prompts become part of an external environment that the model examines and recursively queries [R32]. No KV-cache reuse or latency measurement for RLMs appears in the supplied abstract, and nothing in it addresses production coding workloads or trace reuse. An independent reproduction found that applying deeper recursion (depth=2) or using RLMs on simple retrieval tasks degrades performance and inflates execution time and token costs [R112]. That reproduction used S-NIAH and OOLONG, so it is again long-context evaluation rather than coding. RLM-Extended, a systems-oriented extension of RLMs, adds local LLM backend support through an Ollama-based interface [R69].

The CLM paper treats the context as a file that the model may update without restriction [R17]. The CLM authors report that, on the terminal-coding benchmark TerminalBench 2.1, CLM matches the strongest baseline's accuracy with 29.5% fewer FLOPs [R17]. The CLM authors also report that Suffix Cache Reuse lowers server-side compute relative to standard SGLang serving [R17]. RLM is among the baselines in the CLM comparison, which used a shared Mini-SWE-Agent backbone [R17]. The reported metric is prefix-reuse FLOPs, not wall-clock latency or token counts, and the evidence supplied does not show a head-to-head RLM versus CLM result on tokens or latency in isolation.

Serving-side work shows why in-place edits are a cache problem: Leyline states that production agentic harnesses fall back to re-prefill on every edit [R118]. Leyline reports that its splice kernel raises replay cache hits and cuts latency [R118]. SMem, an architecture in which deletion is an exact update, reports that deletion beats suffix recomputation by 8.5× at 512 blocks and 452× at 4096 blocks [R7]. Non-prefix reuse in general risks quality loss, as CacheTune's authors state [R3].

Other context-management work on coding agents gives token-level evidence. Focus reports a token reduction with identical accuracy on a very small sample [R83]. Scroll reports token counts rather than latency or dollar cost [R18].

Overall, the evidence establishes that CLM reports FLOP savings on coding and agentic benchmarks and that RLM reports comparable cost on long-context tasks. It does not establish RLM cost on coding workloads, RLM or CLM latency under a common serving setup, or reuse of traces across tasks. A CPU-scale experiment comparing token and prefix-cache cost would therefore address a real gap, though its results would not transfer directly to the large models used in the cited studies.

## Retrieval and its limits

This review rests on 12 search queries, which retrieved 120 candidate papers. A relevance screen kept 31 and set aside 89; 6 were read in full text and 25 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R3] Fei li, Song Liu, Yan Liu et al.. Adaptive KV Cache Reuse for Fast Long-Context LLM Serving. 2026. arXiv:2605.24022. https://arxiv.org/abs/2605.24022
[R7] Shengyao Wang, Jiang Liu. Memory as a cache: Exact context reuse and deletion by construction. 2026. arXiv:2609.32395. https://arxiv.org/abs/2609.32395
[R17] Rulin Shao, Shannon Zejiang Shen, Junjie Oscar Yin et al.. Context Language Models. 2026. arXiv:2609.37725. https://arxiv.org/abs/2609.37725
[R18] Yin Lin, Elaine Ang, Erkang Zhu et al.. Context as an Environment: Programmatic Context Management for Long-Horizon Agents. 2026. arXiv:2608.21690. https://arxiv.org/abs/2608.21690
[R32] Alex Zhang, Tim Kraska, Omar Khattab. Recursive Language Models. 2025. arXiv:2512.24601. https://arxiv.org/abs/2512.24601
[R69] Devashish Komiya. RLM-Extended: Deterministic and Local-Model Inference for Recursive Language Models. 2026. doi:10.5281/zenodo.18317149. https://doi.org/10.5281/zenodo.18317149
[R83] Nikhil Verma. Active Context Compression: Autonomous Memory Management in LLM Agents. 2026. arXiv:2601.07190. https://arxiv.org/abs/2601.07190
[R112] D. Wang. Think, But Don't Overthink: Reproducing Recursive Language Models. 2026. arXiv:2603.02615. https://arxiv.org/abs/2603.02615
[R118] Bole Ma, Jan Eitzinger, Harald Koestler. Leyline: KV Cache Directives for Agentic Inference. 2026. doi:10.48550/arxiv.2606.01065. https://doi.org/10.48550/arxiv.2606.01065
