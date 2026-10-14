# Judge set labels (Increment 8, test sample)

Answer each item Y or N after `Label (Y/N):`, judging only from what is shown. Do not open data/judge8/raw/ or
data/results/judge8_*.json. Change nothing but the letters.

## L01 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Evaluation as a harness-stage component and performance dependence on the harness"
Sentence: The sources place evaluation at the center of how harnesses are understood, and they converge on the claim that a benchmark score depends on more than the model.

Label (Y/N): N

## L02 · within_quote

**Does the claim say only what the quote says?**

Source: "Adaptive KV Cache Reuse for Fast Long-Context LLM Serving"
Claim: R3 reports that serving is shifting from short conversations to long-context applications such as retrieval-augmented generation, long-document question answering, and agent reasoning.

Quote from that source: Large language model (LLM) serving is gradually shifting from short conversations to long-context applications such as retrieval-augmented generation (RAG) (Lewis et al., 2020), long-document question answering (Bai et al., 2024), and agent reasoning (Yao et al., 2023).

Label (Y/N): Y

## L03 · within_quote

**Does the claim say only what the quote says?**

Source: "Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems"
Claim: Tool use brings its own context costs, as tool schema definitions are reported to consume a disproportionate share of the available context budget.

Quote from that source: Context rot manifests well before nominal token limits are reached, as tool schema definitions consume a disproportionate share of the available context budget and model attention weakens for information positioned deep within growing prompts.

Label (Y/N): N

## L04 · within_quote

**Does the claim say only what the quote says?**

Source: "Context Language Models"
Claim: The CLM paper retains stale cache states for surviving suffix tokens, and its authors say this can even be beneficial in some cases.

Quote from that source: Surviving suffix tokens 𝐶 thus retain stale cache states that encode the previous prefix, which can even be beneficial in some cases, as it retains richer information from the past.

Label (Y/N): Y

## L05 · within_quote

**Does the claim say only what the quote says?**

Source: "Harness-Aware Evaluation of LLM Agents: Systems, Benchmarks, and Protocols"
Claim: The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.

Quote from that source: recent results highlight the importance of the agent harness: changing the execution system around a fixed model can alter performance and even reverse model rankings.

Label (Y/N): Y

## L06 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C12: A reproduction study examined recursion depth, which the original work left at one. (source: Think, But Don't Overthink: Reproducing Recursive Language Models)
C13: The reproduction reports that deeper recursion or use on simple retrieval hurts performance and inflates time and tokens. (source: Think, But Don't Overthink: Reproducing Recursive Language Models)
C46: The RLM authors report that it outperforms compaction, CodeAct with sub-calls and Claude Code across four long-context tasks while having comparable cost. (source: Recursive Language Models)

Statement: A reproduction found that deeper recursion, or use on simple retrieval, hurts performance and inflates time and tokens. This qualifies the original cost claim, since the original left depth at one.

Label (Y/N): Y

## L07 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C43: The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition. (source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems)
C45: In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill. (source: Token Reduction Is Not Cost Reduction)
C54: A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories. (source: Token Reduction Is Not Cost Reduction)

Statement: The claims do not establish suitability for production coding on quality, cost or trace reuse. The cost evidence is cautionary, and the context-rot authors report the quality hypothesis untested.

Label (Y/N): Y

## L08 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C34: The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external. (source: Harness Engineering for LLM Agents: A Survey of Harness Component Taxonomy, Evaluation, and Model–Harness Coevolution)
C45: The agent-loop survey argues that the loop is being internalized into weights and externalized into skills and harnesses. (source: The Agent Loop: A Survey of Control Strategies, Skills, and Harnesses for LLM Agents)

Statement: The claims do not settle whether capability will mainly move into weights or into external harnesses.

Label (Y/N): Y

## L09 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Recursive Language Models: design, reproduction and reported costs on long-context tasks"
Sentence: The next part turns from what each approach is and how it is built to how cost and reuse might be compared across them.

Label (Y/N): Y

## L10 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Unestablished questions and the scope of a CPU-scale companion experiment"
Sentence: The sections below turn to the cost and reuse evidence the retrieved passages offer for each approach.

Label (Y/N): Y

## L11 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C26: The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt. (source: Recursive Language Models)
C29: The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes. (source: In-context Autoencoder for Context Compression in a Large Language Model)
C30: The Cartridges work trains a smaller KV cache offline for each corpus. (source: Cartridges: Lightweight and general-purpose long context representations via self-study)
C32: H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary. (source: Highlight-Then-Summarize: Learning to Compress Evidence for Long-Context Understanding)

Statement: The claims support that RLMs and context-compression methods both address long inputs but by different mechanisms: external programmatic decomposition versus compact representations or summaries.

Label (Y/N): Y

## L12 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Output quality: gains, caveats and degradation with long context"
Sentence: For coding specifically, the evidence is thin: the context-rot paper only proposes a study, and the passages supplied say nothing about the Context Language Models paper's own results.

Label (Y/N): N

## L13 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Serving-side KV-cache reuse: prefix, non-prefix and in-place edit costs"
Sentence: This section turns to what serving-side work reports about reusing KV cache when context changes.

Label (Y/N): Y

## L14 · within_quote

**Does the claim say only what the quote says?**

Source: "Token Reduction Is Not Cost Reduction"
Claim: In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.

Quote from that source: The largest compression setup reduced delivered tool-output tokens by 38.4% but increased billed cost by 6.8%, while lighter compression produced only small and statistically uncertain savings.

Label (Y/N): Y

## L15 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Context-centric models: compression, memory and context management"
Sentence: They also give no direct measurement of coding quality, cost or trace reuse for these compression methods.

Label (Y/N): N

## L16 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Introduction"
Sentence: The research question concerns how prompt engineering, context engineering, harnesses and agentic harnesses have been defined and bounded since 2025, and which technical components each stage is credited with.

Label (Y/N): Y

## L17 · within_quote

**Does the claim say only what the quote says?**

Source: "SWE-Bench-CL: Continual Learning for Coding Agents"
Claim: SWE-Bench-CL organizes GitHub issues into chronologically ordered sequences to evaluate whether an agent can accumulate experience and transfer knowledge across tasks.

Quote from that source: By organizing GitHub issues into chronologically ordered sequences that reflect natural repository evolution, SWE-Bench-CL enables direct evaluation of an agent's ability to accumulate experience, transfer knowledge across tasks, and resist catastrophic forgetting.

Label (Y/N): Y

## L18 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C1: R3 reports that serving is shifting from short conversations to long-context applications such as retrieval-augmented generation, long-document question answering, and agent reasoning. (source: Adaptive KV Cache Reuse for Fast Long-Context LLM Serving)
C2: The same source says that prefill must process the entire context and that its computational cost grows rapidly with input length. (source: Adaptive KV Cache Reuse for Fast Long-Context LLM Serving)
C4: R18 describes repository-level software engineering as one of the long-running tasks for which LLM agents are increasingly used. (source: Context as an Environment: Programmatic Context Management for Long-Horizon Agents)
C5: R18 states that, as agent trajectories grow, session history accumulates continuously while each model invocation operates over a bounded context window, and identifies context management as a central challenge for the agent harness. (source: Context as an Environment: Programmatic Context Management for Long-Horizon Agents)

Statement: The motivation is consistent across sources: serving is shifting toward long-context applications, prefill cost grows rapidly with input length, and agents on repository-level software engineering face accumulating history against bounded context windows.

Label (Y/N): Y

## L19 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C24: The code-harness survey says prompt engineering changes instructions and context engineering changes what evidence is presented to the model, while harness engineering treats the operating environment itself as the object of analysis. (source: Code as Agent Harness)
C30: The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis. (source: Code as Agent Harness)
C25: The externalization review describes a harness that separates the prompt into layers instead of treating it as an undifferentiated text buffer, and calls this a structured form of context engineering. (source: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering)
C31: The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes. (source: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering)

Statement: The sources agree on the direction of the boundary but phrase it differently. Prompt engineering changes instructions, context engineering changes the evidence presented, and harness engineering takes the operating environment as its object of analysis. The externalization review separately calls the harness a structured form of context engineering, so the boundary between context engineering and harness is not drawn identically.

Label (Y/N): Y

## L20 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C28: The same paper states that no published empirical study has directly tested its joint hypothesis linking codebase scale, context growth and tool attrition. (source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems)
C56: The context-rot paper states that no published empirical study has directly tested its joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition. (source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems)
C27: One empirical proposal describes context rot as progressive, nonlinear degradation of reasoning quality and tool-calling reliability as the context window fills. (source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems)

Statement: Test the context-rot and tool-attrition hypothesis directly, since it is described as untested.

Label (Y/N): N

## L21 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Introduction"
Sentence: The question this review addresses starts from the cost of serving long contexts.

Label (Y/N): Y

## L22 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C1: Prompt engineering is the natural starting point, and one survey describes it as a technique that involves strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters. (source: A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications)
C2: Another paper describes prompts as a form of programming that can customize the outputs and interactions with an LLM. (source: A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT)
C11: The pattern-catalog paper characterizes prompts as a form of programming that can customize the outputs and interactions with an LLM. (source: A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT)

Statement: Prompt engineering is described consistently as designing instructions to guide a model without altering its parameters, and as a form of programming that customizes outputs and interactions.

Label (Y/N): Y

## L23 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Evaluation as a harness-stage component and performance dependence on the harness"
Sentence: Several sources also tie evaluation to safety and failure analysis.

Label (Y/N): N

## L24 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C43: The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition. (source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems)
C56: On quality, the context-rot paper states that no published empirical study has tested whether codebase scale drives context growth and then tool-call degradation. (source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems)

Statement: Test directly whether codebase scale drives context growth and then tool-call degradation, since no published study has done so.

Label (Y/N): N

## L25 · within_quote

**Does the claim say only what the quote says?**

Source: "Adaptive KV Cache Reuse for Fast Long-Context LLM Serving"
Claim: The same source says that prefill must process the entire context and that its computational cost grows rapidly with input length.

Quote from that source: Prefill must process the entire context, and its computational cost grows rapidly with input length.

Label (Y/N): Y

## L26 · within_quote

**Does the claim say only what the quote says?**

Source: "Context Language Models"
Claim: The CLM paper compares CLMs against MEM1, Self-Compact, ACM, and recursive language models (RLM) with a shared Mini-SWE-Agent backbone.

Quote from that source: We compare CLMs against MEM1 (Zhou et al., 2026), Self-Compact (Li et al., 2026b), ACM (Li et al., 2026c), and recursive language models (RLM) (Zhang et al., 2025a) with a shared Mini-SWE-Agent backbone (Merrill et al., 2026).

Label (Y/N): Y

## L27 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C8: R17 reports that CLMs achieve 11.4% higher accuracy with 21.5% fewer prefix-reuse FLOPs than the strongest baseline on BrowseComp-Plus, and match its accuracy on TerminalBench 2.1 with 29.5% fewer FLOPs. (source: Context Language Models)
C40: The CLM authors report that, on TerminalBench 2.1, CLM matches the strongest baseline's accuracy with 29.5% fewer FLOPs. (source: Context Language Models)
C41: The CLM authors also report that Suffix Cache Reuse reduces server-side compute by 35% with matched performance compared with standard SGLang serving. (source: Context Language Models)

Statement: For CLM, the claims establish authors' reports of 11.4% higher accuracy with 21.5% fewer prefix-reuse FLOPs on BrowseComp-Plus, parity on TerminalBench 2.1 with 29.5% fewer FLOPs, and 35% less server-side compute than standard SGLang at matched performance.

Label (Y/N): Y

## L28 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Limits of the evidence: unsettled boundaries and weak generalizability"
Sentence: That placement shows stages overlapping in practice, since orchestration and validation appear under the prompt label.

Label (Y/N): N

## L29 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Introduction"
Sentence: The sections that follow ask what these published results establish about token cost, KV-cache reuse, latency and trace reusability for production coding workloads, and a small CPU-scale experiment accompanies that analysis.

Label (Y/N): Y

## L30 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C17: On reuse of traces, Chained RLM saves predecessor trajectories but does not inject them automatically into later prompts. (source: Chained Recursive Language Models for Multi-Iteration Reasoning)
C52: The Chained RLM authors save raw predecessor trajectories but do not inject them automatically into every prompt. (source: Chained Recursive Language Models for Multi-Iteration Reasoning)

Statement: Evaluate injecting saved predecessor trajectories into later prompts, since they are saved but not automatically used.

Label (Y/N): N

## L31 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C7: The RLM authors report that it handles inputs up to two orders of magnitude beyond model context windows. (source: Recursive Language Models)
C46: The RLM authors report that it outperforms compaction, CodeAct with sub-calls and Claude Code across four long-context tasks while having comparable cost. (source: Recursive Language Models)

Statement: The RLM evidence is of a different kind. Its authors report handling inputs two orders of magnitude beyond context windows and outperforming compaction, CodeAct with sub-calls and Claude Code across four long-context tasks at comparable cost. The claims do not say these tasks are coding workloads.

Label (Y/N): N

## L32 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Context management for coding agents: token-level evidence and its limits"
Sentence: The sources on context management for coding agents are compared below with attention to token cost and accuracy.

Label (Y/N): Y

## L33 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Context-centric models: compression, memory and context management"
Sentence: Other work moves compression offline or hands it to the model itself.

Label (Y/N): N

## L34 · within_quote

**Does the claim say only what the quote says?**

Source: "Token Reduction Is Not Cost Reduction"
Claim: A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories.

Quote from that source: Recall is not task success; marker preservation is not task success; candidate precision is not task success; synthetic critical-drop tests are not task success; bytes removed are not billed savings; and shorter context can cause longer trajectories.

Label (Y/N): Y

## L35 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Context engineering: shifting from prompt text to system-level context"
Sentence: The passages leave open how the boundaries among these terms should be settled and how far the reported benchmark gains hold outside simulation.

Label (Y/N): N

## L36 · within_quote

**Does the claim say only what the quote says?**

Source: "Recursive Language Models Meet Uncertainty: The Surprising Effectiveness of Self-Reflective Program Search for Long Context"
Claim: The SRLM authors report that for context lengths within the model's window, RLMs with recursion often degrade performance relative to the base model.

Quote from that source: We find that for context lengths within the model's window, RLMs with recursion often degrade performance relative to the base model, whereas SRLM yields consistent gains across both short and long contexts.

Label (Y/N): Y

## L37 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C1: Long-context reasoning is described as a central direction in building agentic systems that work over large documents, codebases, transcripts, and multi-step data. (source: Chained Recursive Language Models for Multi-Iteration Reasoning)
C26: The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt. (source: Recursive Language Models)
C4: Recursive Language Models are presented as a general inference paradigm that treats long prompts as part of an external environment. (source: Recursive Language Models)

Statement: The RLM and context-compression literatures share a goal: working over inputs larger than a model can comfortably handle in one pass. RLMs treat the long prompt as an external environment, and the model programmatically examines, decomposes and recursively calls itself over snippets of it.

Label (Y/N): N

## L38 · within_quote

**Does the claim say only what the quote says?**

Source: "Oolong: Evaluating Long Context Reasoning and Aggregation Capabilities"
Claim: The Oolong authors report that frontier models struggle on Oolong, with GPT-5, Claude-Sonnet-4, and Gemini-2.5-Pro all achieving less than 50% accuracy on both splits at 128K.

Quote from that source: Even frontier models struggle on Oolong, with GPT-5, Claude-Sonnet-4, and Gemini-2.5-Pro all achieving less than 50% accuracy on both splits at 128K.

Label (Y/N): Y

## L39 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C4: The same survey frames the broader movement as a shift from input-level linguistic control to system-level contextual orchestration. (source: A comprehensive survey of prompt engineering and context engineering techniques in large language models)
C19: One review describes a shift from input-level linguistic control to system-level contextual orchestration. (source: A comprehensive survey of prompt engineering and context engineering techniques in large language models)
C20: A review of externalization places the harness layer at the current stage, in which capability extends beyond prompt management into persistent infrastructure. (source: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering)

Statement: Several sources describe a movement beyond prompts: one survey frames it as a shift from input-level linguistic control to system-level contextual orchestration, and the externalization review places the harness at a stage extending into persistent infrastructure.

Label (Y/N): Y

## L40 · no_fact

**Does the sentence state no fact about the literature (only introduce, order or signpost)?**

Section: "Context-centric models: compression, memory and context management"
Sentence: The sources show several mechanisms for compressing or managing context, and they differ in where the compression is stored.

Label (Y/N): N

## L41 · within_quote

**Does the claim say only what the quote says?**

Source: "Context Language Models"
Claim: R17 includes recursive language models among the baselines it compares against, on a shared Mini-SWE-Agent backbone.

Quote from that source: We compare CLMs against MEM1 (Zhou et al., 2026), Self-Compact (Li et al., 2026b), ACM (Li et al., 2026c), and recursive language models (RLM) (Zhang et al., 2025a) with a shared Mini-SWE-Agent backbone (Merrill et al., 2026).

Label (Y/N): Y

## L42 · inference

**Does the statement follow from these claims alone, clause by clause, without overstating them?**

Claims (each verified against a quote from its source):
C3: A later survey treats prompt engineering as often lacking theory, noting that it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework. (source: A comprehensive survey of prompt engineering and context engineering techniques in large language models)
C13: The Prompt Report states that prompt engineering suffers from conflicting terminology and a fragmented ontological understanding of what constitutes an effective prompt. (source: The Prompt Report: A Systematic Survey of Prompt Engineering Techniques)
C14: A 2026 survey likewise says prompt engineering is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework. (source: A comprehensive survey of prompt engineering and context engineering techniques in large language models)
C15: A practitioner-focused study calls prompt engineering a critical yet loosely defined skill. (source: Prompting in the Wild: A Qualitative Taxonomy of Practitioner-Driven Prompt Engineering Methods)

Statement: Prompt engineering is also described as poorly consolidated: it is said to have conflicting terminology, to be treated as empirical and ad hoc without a standardized theoretical framework, and to be a critical yet loosely defined skill.

Label (Y/N): Y

## L43 · within_quote

**Does the claim say only what the quote says?**

Source: "ContextPipe: Database-Inspired Context Assembly for Long-Horizon Agents"
Claim: For agent-level context assembly, ContextPipe reports fewer tokens and calls on a SWE-bench Pro subset, with a cost to caching.

Quote from that source: A preliminary evaluation using the SWE-bench Pro Qutebrowser subset shows that, compared with the append-only context construction policy, ContextPipe reduces total token volume by 31%, LLM calls by 23%, and response time by 9%, at the cost of a lower KV cache-hit ratio.

Label (Y/N): Y

## L44 · within_quote

**Does the claim say only what the quote says?**

Source: "Harness-Aware Evaluation of LLM Agents: Systems, Benchmarks, and Protocols"
Claim: One survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.

Quote from that source: recent results highlight the importance of the agent harness: changing the execution system around a fixed model can alter performance and even reverse model rankings.

Label (Y/N): Y

## L45 · within_quote

**Does the claim say only what the quote says?**

Source: "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression"
Claim: LongLLMLingua reports lower API costs and end-to-end latency together with higher performance than original prompts.

Quote from that source: Experiments on the multidocument QA, multi-hop QA, and long context benchmarks demonstrate that LongLLMLingua compressed prompt can derive higher performance than original prompts while both API costs for inference and the end-to-end system latency are largely reduced.

Label (Y/N): Y
