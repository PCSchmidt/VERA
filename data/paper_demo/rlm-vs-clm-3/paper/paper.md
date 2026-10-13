# Recursive and Context-Centric Language Models: Mechanisms, Evidence on Quality and Cost, and Open Questions for Production Coding

## Abstract

Recursive Language Models (RLMs) and context-centric language models (CLMs) both aim to work over inputs larger than a model can comfortably handle in one pass, but they differ in mechanism. RLMs keep the long prompt external and let the model examine, decompose, and recursively call itself over snippets with code. Compression approaches instead use memory slots (ICAE), a small KV cache trained offline per corpus (Cartridges), or a question-conditioned summary of selected evidence (Highlight-Then-Summarize). Chained RLM sits between the two, passing a summary, blackboard, and durable artifacts to a fresh root. Evidence on whether recursion is the useful ingredient diverges. The original paper reports inputs up to two orders of magnitude beyond context windows. Follow-up work finds recursion is not the primary driver, often degrades performance within the window, and at depth 2 degrades performance and inflates time and token costs, while depth-1 RLMs boost accuracy on complex reasoning tasks. For coding, the evidence is thin. The context-rot authors report that the link from codebase scale to tool-call degradation is untested. Cost evidence is cautionary: one compression setup cut tool-output tokens yet raised the bill and reduced patch success. Saved predecessor trajectories in Chained RLM are not automatically reused, and no evaluation of that reuse is described. Suitability for production coding remains unestablished. Open questions include billed-cost and patch-success comparisons, trajectory injection, and matched-budget harness comparisons.

## Introduction

Long-context reasoning is described as a central direction in building agentic systems that work over large documents, codebases, transcripts, and multi-step data [R5]. The straightforward approach of placing everything in the context has a stated limitation: the entire problem-solving process has to occur inside one interaction trace [R5]. For coding in particular, one paper reports that context rot is the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions [R21]. That same paper states that no published empirical study has tested how codebase scale drives context growth and tool-call degradation, so the evidence on production coding is thin.

Recursive Language Models are presented as a general inference paradigm that treats long prompts as part of an external environment [R8]. The RLM authors report that RLMs process inputs up to two orders of magnitude beyond model context windows [R8]. Follow-up work qualifies this picture: the SRLM study finds that recursion itself is not the primary driver of performance in RLM [R9]. Chained RLM addresses the limitation of RLMs by passing a plain-text summary, blackboard, and durable artifacts to a fresh root of the same model [R5].

The context-centric side of the question covers methods that compress or condition on large contexts. The In-context Autoencoder compresses a long context into short compact memory slots that the LLM can condition on directly [R28]. Highlight-Then-Summarize is a compress-then-reason paradigm that first identifies question-relevant evidence and then integrates it into a compact summary [R1]. The Context Language Models paper by Shao and colleagues introduces models that natively manage their own context, treating the context as a file that the model may update without restriction, but the supplied passages do not include that paper's text beyond this description, so its mechanism and results cannot be reported here. The supplied passages also do not directly compare RLMs and CLMs on production coding cost or on the reuse of execution traces.

## Method

The question this paper answers was proposed by VERA from the user's topic and confirmed by the user: Based on the published literature on Recursive Language Models (RLMs, in which a model programmatically decomposes and recursively calls itself over an externalized long prompt) and on context-centric language models (CLMs, which condition on or compress large contexts), how do the two approaches overlap and differ in mechanism, and what does the existing evidence say about their suitability for production coding with respect to output quality, cost efficiency, and reuse of execution traces?

Search. 12 queries were sent to the paper-search services: “Recursive Language Models long prompt externalized environment”; “recursive self-calls language model REPL long context”; “context-centric language models long context compression”; “context compression prompt compression large language models”; “retrieval-augmented generation versus long context comparison”; “agentic coding repository-level code generation long context”; “long context benchmark needle in a haystack evaluation”; “survey long context language models efficient”; “lost in the middle long context failure modes”; “context rot performance degradation long inputs”; “reusing agent trajectories execution traces code agents”; “cost efficiency inference token usage recursive decomposition agents”. They retrieved 120 candidate papers. A relevance screen, judged on titles and abstracts, kept 26 and set aside 94.

Reading. Every kept paper was read at its abstract; 15 were also read in full text, and 11 at the abstract only. This gave 174 evidence passages, the only text the paper may quote.

Writing and checking. The evidence sections were drafted sentence by sentence; every sentence that attributes something to a source carries a quote copied from one of those passages. Each quote was checked to be verbatim in its source, and a judge other than the writer checked that the passage supports the sentence and that the quote alone states it; sentences that failed were repaired once or removed. 57 claims from 16 sources survived. Interpretation sections, where present, rest only on those claims and are labelled as such.

Models. Written by anthropic/claude-sonnet-5.5; judged by z-ai/glm-5.3-flash.

## Externalized context and recursive decomposition in RLMs

The original RLM paper describes a general inference paradigm in which long prompts are treated as part of an external environment [R8]. Chained RLM's authors note that Recursive Language Models improve long-context inference without changing model weights, but the global working state still largely lives inside one orchestration trajectory [R5]. One follow-up describes the externalized prompt as a variable inside a sandboxed execution environment [R9]. The original paper reports that RLMs handle inputs far beyond model context windows [R8].

The sources disagree about whether recursion itself drives the gains. The SRLM authors report that recursion is not the primary driver of RLM performance [R9]. A reproduction study reports that deeper recursion degrades performance and inflates time and token costs [R75]. The λ-RLM work criticizes the open-ended REPL on verifiability grounds [R86].

On reuse of traces, Chained RLM saves predecessor trajectories but does not inject them automatically into later prompts [R5]. The supplied passages do not cover the Context Language Models paper, so any comparison of CLMs with RLMs, and any evidence on production coding cost, is left open here.

## Context-centric models: compression, memory and context management

The sources show several mechanisms for compressing or managing context, and they differ in where the compression is stored. The ICAE authors describe compressing a long context into memory slots that the model can condition on directly [R28]. The ICAE authors report about 1% added parameters and 4x compression on Llama, with latency and GPU memory gains [R28]. A survey notes that gist-token methods carry a cost in model modification [R12].

Other work moves compression offline or hands it to the model itself. The Cartridges authors train a small KV cache per corpus from synthetic conversations with a context-distillation objective [R94]. The Cartridges authors report matching in-context learning on long-context benchmarks with far less memory and higher throughput [R94]. The MemGPT authors describe a system in which the model edits and searches its own memory [R146]. MemGPT also keeps a recursive summary of evicted messages at the head of its queue [R146].

Evidence on the limits of long context is mixed with the compression results above. The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed perfect [R158]. The passages supplied do not include the paper on Context Language Models that treats the context as an editable file, so no comparison with it can be drawn here. They also give no direct measurement of coding quality, cost or trace reuse for these compression methods.

## Mechanistic overlap and differences between RLMs and CLMs

The Context Language Models paper named in the brief is not among the supplied passages, so what follows covers RLMs and neighbouring context-compression work only. The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt [R8]. Chained RLM states that RLMs improve long-context inference without changing model weights [R5]. Chained RLM responds by passing a summary, blackboard, and durable artifacts to a fresh root of the same model [R5].

The compression line instead modifies or trains parameters to shrink context. The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes [R28]. The Cartridges work trains a smaller KV cache offline for each corpus [R94]. The Cartridges authors report that self-study Cartridges match ICL performance while using 38.6x less memory and enabling 26.4x higher throughput [R94]. H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary [R1].

Evidence on RLM quality and cost is mixed. SRLM's authors conclude that recursion itself is not the primary driver of performance in RLM [R9]. A reproduction study reports that depth-2 recursion degrades performance and inflates execution time and token costs [R75]. A billing study of coding agents finds that user-side context layers account for only about 6% of cost [R78]. None of the supplied passages evaluates RLMs or CLMs on production coding, and none examines reuse of execution traces across tasks, so those questions remain open here.

## Output quality: gains, caveats and degradation with long context

The sources describe output quality under long context as a mix of gains and degradation, and they do not settle how far these results carry over to production coding. The reproduction study of recursive language models reports that depth-1 RLMs effectively boost accuracy on complex reasoning tasks, while deeper recursion degrades performance [R75]. The SRLM authors report that for context lengths within the model's window, RLMs with recursion often degrade performance relative to the base model [R9]. The SRLM authors also conclude that recursion is not the primary driver of RLM performance [R9]. The λ-RLM authors report that a typed functional runtime outperformed standard RLM in most model-task comparisons [R86].

On the context side, the evidence shows that long inputs themselves hurt, and that compression can help. The Oolong authors report that frontier models struggle on Oolong, with GPT-5, Claude-Sonnet-4, and Gemini-2.5-Pro all achieving less than 50% accuracy on both splits at 128K [R126]. The Highlight-Then-Summarize authors report that a 0.46K-token Claude summary, about 3% of the 15.19K-token document, increased accuracy from 72.6 to 93.0 when used alone [R1]. The same authors name a limitation of that approach: H2S is less naturally suited to tasks requiring broadly distributed context coverage [R1].

For coding specifically, the evidence is thin: the context-rot paper only proposes a study, and the passages supplied say nothing about the Context Language Models paper's own results. The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition [R21].

## Cost efficiency: token reduction versus billed cost

The central finding on this theme comes from a study of token-reduction tools for coding agents, which separates tokens removed from money spent [R78]. In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill [R78]. The same work reports that aggressive compression reduced successful patch application on a SWE-bench Go subset [R78].

Work on compressing contexts reports efficiency in different units, namely latency and memory rather than billed spend. The In-context Autoencoder (ICAE) paper reports a 4× compression with gains in latency and GPU memory [R28]. Cartridges are reported to match in-context learning performance on long-context benchmarks at much lower serving cost [R94]. LongLLMLingua reports lower API costs and end-to-end latency together with higher performance than original prompts [R132].

For agent-level context assembly, ContextPipe reports fewer tokens and calls on a SWE-bench Pro subset, with a cost to caching [R81].

The supplied passages do not include the Context Language Models paper itself, so its cost behavior is not assessed here. None of the compression studies above reports provider-billed cost per successful coding task, and no passage covers recursive language models on cost, which leaves the comparison open.

## Production coding, trace reuse and evidence gaps

The sources supplied here say little about production coding as such, and none of them is the Context Language Models paper the reader named, so that work cannot be related to the evidence below. The Chained RLM paper describes its roots as modules that can inspect variables, run code, call sub-LLMs, and write artifacts [R5]. The Chained RLM authors save raw predecessor trajectories but do not inject them automatically into every prompt [R5].

On cost, the ContextPipe preliminary evaluation reports a 31% reduction in total token volume against append-only construction [R81]. A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories [R78]. The token-reduction cost study notes that its retained telemetry does not record, per token, the turn of entry and the number of later calls that reused it, so it presents its marginal-cost equation as a bounded conceptual model [R78].

On quality, the context-rot paper states that no published empirical study has tested whether codebase scale drives context growth and then tool-call degradation [R21]. ContextPipe's authors list comparisons of open-source and production coding harnesses under matched budgets as future work [R81]. Taken together, the passages supply no head-to-head comparison of RLMs and CLMs on production coding quality, cost, or trace reuse.

## Discussion

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

The RLM and context-compression literatures share a goal: working over inputs larger than a model can comfortably handle in one pass. RLMs treat the long prompt as an external environment, and the model programmatically examines, decomposes and recursively calls itself over snippets of it (C1, C26, C4). The compression approaches differ in mechanism. ICAE compresses context into memory slots the model conditions on, Cartridges train a small KV cache offline per corpus, and Highlight-Then-Summarize selects evidence and writes a question-conditioned summary. RLMs instead leave the prompt external and act on it with code (C29, C30, C32, C26). Chained RLM sits between the two. It passes a summary, blackboard and durable artifacts to a fresh root of the same model, because the working state otherwise stays inside one orchestration trajectory (C11, C28). The evidence on whether recursion is the useful ingredient pulls apart. The original paper reports inputs up to two orders of magnitude beyond context windows. Follow-up work finds recursion is not the primary driver of performance, finds that recursion often degrades performance within the model's window, and finds that depth-2 recursion degrades performance and inflates time and token costs (C5, C33, C37, C34). The reproduction study reports that depth-1 RLMs boost accuracy on complex reasoning tasks while deeper recursion degrades it. The benefit of an RLM therefore appears to depend on how it is configured (C36, C15). For coding, the quality evidence is thin. Context rot is defined as degradation of reasoning and tool-calling as the window fills, yet the authors state that no published study has directly tested the joint hypothesis linking codebase scale to context growth and then to tool attrition (C3, C43). The cost evidence cautions against equating fewer tokens with lower cost. One coding-agent study found that the largest compression setup cut delivered tool-output tokens yet raised the bill, and that aggressive compression reduced successful patch application on a SWE-bench Go subset (C45, C46, C54). On trace reuse, Chained RLM saves raw predecessor trajectories but does not inject them automatically into later prompts. The reviewed claims describe no evaluation of that reuse (C17, C52).

## Conclusions

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

The claims support that RLMs and context-compression methods both address long inputs but by different mechanisms: external programmatic decomposition versus compact representations or summaries (C26, C29, C30, C32). The claims do not support a general conclusion that recursion is what makes RLMs work, or that deeper recursion is beneficial. Evidence for depth beyond one is negative (C33, C36, C34). The claims do not establish suitability for production coding on quality, cost or trace reuse. The cost evidence is cautionary, and the context-rot authors report the quality hypothesis untested (C43, C45, C54).

## A research agenda

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Test directly whether codebase scale drives context growth and then tool-call degradation, since no published study has done so (C43, C56). Compare RLMs and compression methods on coding tasks by billed cost and patch success, not token counts alone, because token removal has raised bills and lowered patch success (C45, C46, C54). The cost study's retained telemetry does not record, per token, the turn of entry or the number of later calls that reused it, so it presents its marginal-cost equation only as a bounded conceptual model. This is a stated limitation of that study's evidence, not a recommendation drawn from the claims (C55). Evaluate injecting saved predecessor trajectories into later prompts, since they are saved but not automatically used (C17, C52). Compare coding harnesses under matched budgets, which is listed as future work (C57).

## Threats to validity

Coverage. The paper rests on what 12 queries found; the search was not repeated for the paper. A finding reported as missing means these searches did not find it, not that it does not exist.

Depth of reading. 11 of 26 kept papers were read at the abstract only, so their methods and caveats are known only as their abstracts state them.

What the checks cover. Each claim was checked against the passage it quotes, not against the whole source or the wider literature. A claim can be supported by its quote and still leave out a qualification stated elsewhere in the paper it cites. Interpretation sections were judged to follow from the claims they name; they were not checked against the sources.

Same-family grading. The writer is a Claude model; the judges are a different model family, and any independent scoring of this paper by a Claude model shares the writer's family.

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
[R81] Peng Xu, Zuyu Zhang, Yuze Sun et al.. ContextPipe: Database-Inspired Context Assembly for Long-Horizon Agents. 2026. arXiv:2609.00749. https://arxiv.org/abs/2609.00749
[R86] Amartya Roy, Rasul Tutunov, Xiao-Tong Ji et al.. The Y-Combinator for LLMs: Solving Long-Context Rot with λ-Calculus. 2026. arXiv:2603.20105. https://arxiv.org/abs/2603.20105
[R94] Sabri Eyuboglu, Ryan Ehrlich, Simran Arora et al.. Cartridges: Lightweight and general-purpose long context representations via self-study. 2025. arXiv:2506.06266. https://arxiv.org/abs/2506.06266
[R126] Bertsch, Amanda, Pratapa, Adithya, Mitamura, Teruko et al.. Oolong: Evaluating Long Context Reasoning and Aggregation Capabilities. 2025. doi:10.48550/arxiv.2511.02817. https://doi.org/10.48550/arxiv.2511.02817
[R132] Huiqiang Jiang, Qianhui Wu, Xufang Luo et al.. LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression. 2024. doi:10.18653/v1/2024.acl-long.91. https://doi.org/10.18653/v1/2024.acl-long.91
[R146] Charles Packer, Sarah Wooders, Kevin Lin et al.. MemGPT: Towards LLMs as Operating Systems. 2023. doi:10.48550/arxiv.2310.08560. https://doi.org/10.48550/arxiv.2310.08560
[R158] Yufeng Du, Minyang Tian, Srikanth Ronanki et al.. Context Length Alone Hurts LLM Performance Despite Perfect Retrieval. 2025. doi:10.18653/v1/2025.findings-emnlp.1264. https://doi.org/10.18653/v1/2025.findings-emnlp.1264
