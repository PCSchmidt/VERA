# Real-case labelling sheet (Increment 7, test split)

Label each item with one letter after `Label:`. Judge only from what is shown. Do not open
`data/realcase/items.jsonl` (it records which items others flagged) until the set is frozen.

- **claim**: `W` says no more than its quote; `M` says more than its quote; `X` needs context outside the quote
- **sentence**: `N` states no fact (a transition); `F` follows from the claims listed; `D` does not follow from them, or contradicts them
- **inference**: `F` follows from its premises; `O` overreaches or does not follow

## T01 · claim

Source: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering

Claim: The externalization review places the harness as the stage at which engineering attention moved from prompts to the operating environment.

Quote: “As context windows became saturated and prompt templates more unwieldy, engineering attention increasingly shifted from "what should we tell the model?" to "what environment should the model operate in?"”

Label (W/M/X): M

## T02 · claim

Source: ContextPipe: Database-Inspired Context Assembly for Long-Horizon Agents

Claim: On cost, the ContextPipe preliminary evaluation reports a 31% reduction in total token volume against append-only construction.

Quote: “A preliminary evaluation using the SWE-bench Pro Qutebrowser subset shows that, compared with the append-only context construction policy, ContextPipe reduces total token volume by 31%, LLM calls by 23%, and response time by 9%, at the cost of a lower KV cache-hit ratio.”

Label (W/M/X): W

## T03 · sentence

Section: Harness engineering: the structure around a fixed model

Sentence: The passages supplied here do not settle a single agreed definition of the harness or a standard component list.

Claims of its section:
- The externalization review describes memory as externalizing state across time, skills as externalizing procedural expertise, protocols as externalizing interaction structure, and harness engineering as the unification layer that coordinates them into governed execution.
- The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis.
- The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes.
- The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- The UniACE study reports large bidirectional score changes and model-ranking reversals when compared with source implementations.
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The code-as-harness survey lists open challenges including evaluation beyond final task success, verification under incomplete feedback, and regression-free harness improvement.

Label (N/F/D): F

## T04 · sentence

Section: Introduction

Sentence: That same paper states that no published empirical study has tested how codebase scale drives context growth and tool-call degradation, so the evidence on production coding is thin.

Claims of its section:
- Long-context reasoning is described as a central direction in building agentic systems that work over large documents, codebases, transcripts, and multi-step data.
- The straightforward approach of placing everything in the context has a stated limitation: the entire problem-solving process has to occur inside one interaction trace.
- For coding in particular, one paper reports that context rot is the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions.
- Recursive Language Models are presented as a general inference paradigm that treats long prompts as part of an external environment.
- The RLM authors report that RLMs process inputs up to two orders of magnitude beyond model context windows.
- Follow-up work qualifies this picture: the SRLM study finds that recursion itself is not the primary driver of performance in RLM.
- Chained RLM addresses the limitation of RLMs by passing a plain-text summary, blackboard, and durable artifacts to a fresh root of the same model.
- The In-context Autoencoder compresses a long context into short compact memory slots that the LLM can condition on directly.
- Highlight-Then-Summarize is a compress-then-reason paradigm that first identifies question-relevant evidence and then integrates it into a compact summary.

Label (N/F/D): D

## T05 · sentence

Section: Limits of the evidence: unsettled boundaries and weak generalizability

Sentence: Another paper, by contrast, places test-driven governance, orchestrator-controlled phase order and bounded repair loops inside a prompt-engineering framing.

Claims of its section:
- The context-compression experiment used a synthetic recall task and acknowledges the limits of its single-model, single-budget setup.
- The context-rot paper states that no published empirical study has directly tested its joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.
- The drilling system draws its conclusion from case studies and a qualitative ablation analysis, which it says suggest that domain-specialized tool design, rather than model scale alone, is the primary driver of analytical quality.
- The UniACE study reports that comparisons with source implementations produced bidirectional score shifts and model-ranking reversals.
- The harness-aware survey distinguishes what existing comparisons establish from effects that remain entangled.

Label (N/F/D): D

## T06 · sentence

Section: Introduction

Sentence: The context-centric side of the question covers methods that compress or condition on large contexts.

Claims of its section:
- Long-context reasoning is described as a central direction in building agentic systems that work over large documents, codebases, transcripts, and multi-step data.
- The straightforward approach of placing everything in the context has a stated limitation: the entire problem-solving process has to occur inside one interaction trace.
- For coding in particular, one paper reports that context rot is the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions.
- Recursive Language Models are presented as a general inference paradigm that treats long prompts as part of an external environment.
- The RLM authors report that RLMs process inputs up to two orders of magnitude beyond model context windows.
- Follow-up work qualifies this picture: the SRLM study finds that recursion itself is not the primary driver of performance in RLM.
- Chained RLM addresses the limitation of RLMs by passing a plain-text summary, blackboard, and durable artifacts to a fresh root of the same model.
- The In-context Autoencoder compresses a long context into short compact memory slots that the LLM can condition on directly.
- Highlight-Then-Summarize is a compress-then-reason paradigm that first identifies question-relevant evidence and then integrates it into a compact summary.

Label (N/F/D): F

## T07 · claim

Source: Chained Recursive Language Models for Multi-Iteration Reasoning

Claim: On reuse of traces, Chained RLM saves predecessor trajectories but does not inject them automatically into later prompts.

Quote: “Raw predecessor trajectories are also saved, but they are not automatically injected into every prompt.”

Label (W/M/X): W

## T08 · claim

Source: Highlight-Then-Summarize: Learning to Compress Evidence for Long-Context Understanding

Claim: The Highlight-Then-Summarize authors report that a 0.46K-token Claude summary, about 3% of the 15.19K-token document, increased accuracy from 72.6 to 93.0 when used alone.

Quote: “A 0.46K-token Claude summary, approximately 3% of the 15.19K-token document, increases accuracy from 72.6 to 93.0 when used alone”

Label (W/M/X): W

## T09 · sentence

Section: Introduction

Sentence: The harness concept moves the unit of analysis from the prompt or context to the execution system around the model.

Claims of its section:
- Prompt engineering is the natural starting point, and one survey describes it as a technique that involves strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters.
- Another paper describes prompts as a form of programming that can customize the outputs and interactions with an LLM.
- A later survey treats prompt engineering as often lacking theory, noting that it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.
- The same survey frames the broader movement as a shift from input-level linguistic control to system-level contextual orchestration.
- Context management has also become an object of empirical study: one paper notes that LLM agents on long-running tasks inevitably exceed their usable context window, forcing a choice about what history to discard.
- Memory is another component, and one framework implements memory not as a vector database, but as a persistent file system accessible via tool calls.
- Tool use brings its own context costs, as tool schema definitions are reported to consume a disproportionate share of the available context budget.
- One survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- A further survey takes the agent loop, not the model in isolation, as its unit of analysis.

Label (N/F/D): F

## T10 · claim

Source: Chained Recursive Language Models for Multi-Iteration Reasoning

Claim: Chained RLM states that RLMs improve long-context inference without changing model weights.

Quote: “This improves long-context inference without changing model weights, but the global working state still largely lives inside one orchestration trajectory.”

Label (W/M/X): W

## T11 · sentence

Section: Mechanistic overlap and differences between RLMs and CLMs

Sentence: Evidence on RLM quality and cost is mixed.

Claims of its section:
- The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt.
- Chained RLM states that RLMs improve long-context inference without changing model weights.
- Chained RLM responds by passing a summary, blackboard, and durable artifacts to a fresh root of the same model.
- The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes.
- The Cartridges work trains a smaller KV cache offline for each corpus.
- The Cartridges authors report that self-study Cartridges match ICL performance while using 38.6x less memory and enabling 26.4x higher throughput.
- H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary.
- SRLM's authors conclude that recursion itself is not the primary driver of performance in RLM.
- A reproduction study reports that depth-2 recursion degrades performance and inflates execution time and token costs.
- A billing study of coding agents finds that user-side context layers account for only about 6% of cost.

Label (N/F/D): F

## T12 · inference

Section: Discussion

Statement: For coding, the quality evidence is thin. Context rot is defined as degradation of reasoning and tool-calling as the window fills, yet the authors state that no published study has directly tested the joint hypothesis linking codebase scale to context growth and then to tool attrition.

Its premises:
- For coding in particular, one paper reports that context rot is the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions.
- The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.

Label (F/O): F

## T13 · claim

Source: UniACE: A Unified Framework for Evaluating LLM Agentic Capabilities

Claim: The UniACE study reports large bidirectional score changes and model-ranking reversals when compared with source implementations.

Quote: “Comparisons with source implementations show large bidirectional score changes and model-ranking reversals, while matched online and offline runs reveal substantial sensitivity to accessible evidence and its representation.”

Label (W/M/X): W

## T14 · inference

Section: Conclusions

Statement: Some of the empirical support is limited: one context-compression experiment used a synthetic task with a single model and budget, and the context-rot hypothesis is stated as untested by prior published studies.

Its premises:
- The context-compression experiment used a synthetic recall task and acknowledges the limits of its single-model, single-budget setup.
- The same paper states that no published empirical study has directly tested its joint hypothesis linking codebase scale, context growth and tool attrition.
- The context-rot paper states that no published empirical study has directly tested its joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.

Label (F/O): F

## T15 · claim

Source: In-context Autoencoder for Context Compression in a Large Language Model

Claim: The In-context Autoencoder compresses a long context into short compact memory slots that the LLM can condition on directly.

Quote: “We propose the In-context Autoencoder (ICAE), leveraging the power of a large language model (LLM) to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes.”

Label (W/M/X): W

## T16 · inference

Section: A research agenda

Statement: Test directly whether codebase scale drives context growth and then tool-call degradation, since no published study has done so.

Its premises:
- The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.
- On quality, the context-rot paper states that no published empirical study has tested whether codebase scale drives context growth and then tool-call degradation.

Label (F/O): F

## T17 · sentence

Section: Introduction

Sentence: The supplied passages also do not directly compare RLMs and CLMs on production coding cost or on the reuse of execution traces.

Claims of its section:
- Long-context reasoning is described as a central direction in building agentic systems that work over large documents, codebases, transcripts, and multi-step data.
- The straightforward approach of placing everything in the context has a stated limitation: the entire problem-solving process has to occur inside one interaction trace.
- For coding in particular, one paper reports that context rot is the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions.
- Recursive Language Models are presented as a general inference paradigm that treats long prompts as part of an external environment.
- The RLM authors report that RLMs process inputs up to two orders of magnitude beyond model context windows.
- Follow-up work qualifies this picture: the SRLM study finds that recursion itself is not the primary driver of performance in RLM.
- Chained RLM addresses the limitation of RLMs by passing a plain-text summary, blackboard, and durable artifacts to a fresh root of the same model.
- The In-context Autoencoder compresses a long context into short compact memory slots that the LLM can condition on directly.
- Highlight-Then-Summarize is a compress-then-reason paradigm that first identifies question-relevant evidence and then integrates it into a compact summary.

Label (N/F/D): D

## T18 · sentence

Section: Output quality: gains, caveats and degradation with long context

Sentence: The sources describe output quality under long context as a mix of gains and degradation, and they do not settle how far these results carry over to production coding.

Claims of its section:
- The reproduction study of recursive language models reports that depth-1 RLMs effectively boost accuracy on complex reasoning tasks, while deeper recursion degrades performance.
- The SRLM authors report that for context lengths within the model's window, RLMs with recursion often degrade performance relative to the base model.
- The SRLM authors also conclude that recursion is not the primary driver of RLM performance.
- The λ-RLM authors report that a typed functional runtime outperformed standard RLM in most model-task comparisons.
- The Oolong authors report that frontier models struggle on Oolong, with GPT-5, Claude-Sonnet-4, and Gemini-2.5-Pro all achieving less than 50% accuracy on both splits at 128K.
- The Highlight-Then-Summarize authors report that a 0.46K-token Claude summary, about 3% of the 15.19K-token document, increased accuracy from 72.6 to 93.0 when used alone.
- The same authors name a limitation of that approach: H2S is less naturally suited to tasks requiring broadly distributed context coverage.
- The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.

Label (N/F/D): D

## T19 · claim

Source: Code as Agent Harness

Claim: On multi-agent orchestration, the code-harness survey reports that long-running harnesses separate planning, generation and evaluation into distinct roles.

Quote: “Anthropic's long-running harnesses separate planning, generation, and evaluation into distinct roles, using structured artifacts and independent evaluation to maintain progress across long sessions [15,171].”

Label (W/M/X): W

## T20 · inference

Section: Conclusions

Statement: The claims do not settle whether capability will mainly move into weights or into external harnesses.

Its premises:
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The agent-loop survey argues that the loop is being internalized into weights and externalized into skills and harnesses.

Label (F/O): F

## T21 · claim

Source: A Comprehensive Survey on Long Context Language Modeling

Claim: A survey notes that gist-token methods carry a cost in model modification.

Quote: “However, such methods typically require modifying the parameters of the LLM.”

Label (W/M/X): W

## T22 · sentence

Section: Prompt engineering: definitions, pattern catalogs, and terminological fragmentation

Sentence: The supplied passages define prompt engineering mainly as instruction design for a fixed model.

Claims of its section:
- One survey describes it as strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters.
- The pattern-catalog paper characterizes prompts as a form of programming that can customize the outputs and interactions with an LLM.
- The prompt pattern catalog paper justifies documenting prompts in pattern form by treating prompts as a form of programming: "Since prompts are a form of programming, it is natural to document them in pattern form."
- The Prompt Report states that prompt engineering suffers from conflicting terminology and a fragmented ontological understanding of what constitutes an effective prompt.
- A 2026 survey likewise says prompt engineering is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.
- A practitioner-focused study calls prompt engineering a critical yet loosely defined skill.
- The Prompt Report presents a taxonomy of 58 LLM prompting techniques.
- A practitioner-oriented study reports that its primary contribution is "a practice-based taxonomy of prompting strategies "in the wild," highlighting forms of interaction that extend beyond formal prompt engineering models."
- The Prompt Report states that its stance is observational and that evaluation in the field is variable and unstandardized: "The field is new, and evaluation is variable and unstandardized-even the most meticulous experimentation may suffer from unanticipated shortcomings, and model outputs themselves are sensitive to meaning-preserving changes in inputs."
- One review describes a shift from input-level linguistic control to system-level contextual orchestration.
- A review of externalization places the harness layer at the current stage, in which capability extends beyond prompt management into persistent infrastructure.

Label (N/F/D): F

## T23 · inference

Section: A research agenda

Statement: The sources describe a split in where agent functions reside: one harness survey proposes that routine capability-bearing support migrates into model weights while constraint-bearing governance functions remain external, and the agent-loop survey likewise argues that the loop is being internalized into weights and externalized into skills and harnesses. Both are proposals or arguments, and the sources do not report an empirical test of which functions migrate.

Its premises:
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The agent-loop survey argues that the loop is being internalized into weights and externalized into skills and harnesses.

Label (F/O): O

## T24 · claim

Source: A comprehensive survey of prompt engineering and context engineering techniques in large language models

Claim: One review describes a shift from input-level linguistic control to system-level contextual orchestration.

Quote: “By analyzing the shift from input-level linguistic control to system-level contextual orchestration, we identify persistent limitations, such as context dilution and computational overhead.”

Label (W/M/X): W

## T25 · inference

Section: A research agenda

Statement: Repeat context-management comparisons with multiple models and budgets on non-synthetic tasks, because the existing experiment is limited to a single model and budget.

Its premises:
- The context-compression experiment used a synthetic recall task and acknowledges the limits of its single-model, single-budget setup.
- Context management has also become an object of empirical study: one paper notes that LLM agents on long-running tasks inevitably exceed their usable context window, forcing a choice about what history to discard.

Label (F/O): F

## T26 · sentence

Section: Production coding, trace reuse and evidence gaps

Sentence: The sources supplied here say little about production coding as such, and none of them is the Context Language Models paper the reader named, so that work cannot be related to the evidence below.

Claims of its section:
- The Chained RLM paper describes its roots as modules that can inspect variables, run code, call sub-LLMs, and write artifacts.
- The Chained RLM authors save raw predecessor trajectories but do not inject them automatically into every prompt.
- On cost, the ContextPipe preliminary evaluation reports a 31% reduction in total token volume against append-only construction.
- A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories.
- The token-reduction cost study notes that its retained telemetry does not record, per token, the turn of entry and the number of later calls that reused it, so it presents its marginal-cost equation as a bounded conceptual model.
- On quality, the context-rot paper states that no published empirical study has tested whether codebase scale drives context growth and then tool-call degradation.
- ContextPipe's authors list comparisons of open-source and production coding harnesses under matched budgets as future work.

Label (N/F/D): D

## T27 · claim

Source: From Model Scaling to System Scaling: Scaling the Harness in Agentic AI

Claim: The scaling-the-harness paper lists the components of a harness, including orchestration and verification.

Quote: “This framing is increasingly inadequate because agent performance emerges from the interaction among the foundation model, memory substrate, context constructor, skill-routing layer, orchestration loop, and verification-and-governance layer.”

Label (W/M/X): W

## T28 · sentence

Section: Harness engineering: the structure around a fixed model

Sentence: The surveys in this set generally treat the harness as the structure wrapped around a fixed model, but they enumerate its parts differently.

Claims of its section:
- The externalization review describes memory as externalizing state across time, skills as externalizing procedural expertise, protocols as externalizing interaction structure, and harness engineering as the unification layer that coordinates them into governed execution.
- The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis.
- The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes.
- The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- The UniACE study reports large bidirectional score changes and model-ranking reversals when compared with source implementations.
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The code-as-harness survey lists open challenges including evaluation beyond final task success, verification under incomplete feedback, and regression-free harness improvement.

Label (N/F/D): F

## T29 · inference

Section: Conclusions

Statement: The literature articulates a progression from prompt-level instruction design, to context-level management of what the model sees, to harness-level treatment of the surrounding execution environment, though the exact boundaries are phrased differently across sources.

Its premises:
- The same survey frames the broader movement as a shift from input-level linguistic control to system-level contextual orchestration.
- The code-harness survey says prompt engineering changes instructions and context engineering changes what evidence is presented to the model, while harness engineering treats the operating environment itself as the object of analysis.
- The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis.
- A review of externalization places the harness layer at the current stage, in which capability extends beyond prompt management into persistent infrastructure.
- The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes.

Label (F/O): F

## T30 · claim

Source: UniACE: A Unified Framework for Evaluating LLM Agentic Capabilities

Claim: The UniACE authors state that a reported score reflects a complete model–harness–environment configuration rather than the model alone.

Quote: “a reported score reflects a complete model--harness--environment configuration rather than the model alone.”

Label (W/M/X): W

## T31 · claim

Source: Harness-Aware Evaluation of LLM Agents: Systems, Benchmarks, and Protocols

Claim: The harness-aware evaluation survey introduces a four-factor framework comprising the model, harness, environment, and evaluator, alongside the protocol under which they are tested.

Quote: “introduces a four-factor evaluation framework comprising the model, harness, environment, and evaluator, alongside the protocol under which they are tested.”

Label (W/M/X): W

## T32 · sentence

Section: Cost efficiency: token reduction versus billed cost

Sentence: Work on compressing contexts reports efficiency in different units, namely latency and memory rather than billed spend.

Claims of its section:
- The central finding on this theme comes from a study of token-reduction tools for coding agents, which separates tokens removed from money spent.
- In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.
- The same work reports that aggressive compression reduced successful patch application on a SWE-bench Go subset.
- The In-context Autoencoder (ICAE) paper reports a 4× compression with gains in latency and GPU memory.
- Cartridges are reported to match in-context learning performance on long-context benchmarks at much lower serving cost.
- LongLLMLingua reports lower API costs and end-to-end latency together with higher performance than original prompts.
- For agent-level context assembly, ContextPipe reports fewer tokens and calls on a SWE-bench Pro subset, with a cost to caching.

Label (N/F/D): D

## T33 · sentence

Section: Limits of the evidence: unsettled boundaries and weak generalizability

Sentence: That placement shows stages overlapping in practice, since orchestration and validation appear under the prompt label.

Claims of its section:
- The context-compression experiment used a synthetic recall task and acknowledges the limits of its single-model, single-budget setup.
- The context-rot paper states that no published empirical study has directly tested its joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.
- The drilling system draws its conclusion from case studies and a qualitative ablation analysis, which it says suggest that domain-specialized tool design, rather than model scale alone, is the primary driver of analytical quality.
- The UniACE study reports that comparisons with source implementations produced bidirectional score shifts and model-ranking reversals.
- The harness-aware survey distinguishes what existing comparisons establish from effects that remain entangled.

Label (N/F/D): D

## T34 · inference

Section: Conclusions

Statement: The claims support that RLMs and context-compression methods both address long inputs but by different mechanisms: external programmatic decomposition versus compact representations or summaries.

Its premises:
- The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt.
- The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes.
- The Cartridges work trains a smaller KV cache offline for each corpus.
- H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary.

Label (F/O): F

## T35 · claim

Source: The Agent Loop: A Survey of Control Strategies, Skills, and Harnesses for LLM Agents

Claim: A further survey takes the agent loop, not the model in isolation, as its unit of analysis.

Quote: “This survey takes that agent loop, not the model in isolation, as its unit of analysis, on the argument that the properties practitioners actually care about, cost, reliability, and safety, are decided by the loop rather than by the model alone.”

Label (W/M/X): W

## T36 · claim

Source: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering

Claim: The externalization review describes a harness that separates the prompt into layers instead of treating it as an undifferentiated text buffer, and calls this a structured form of context engineering.

Quote: “Rather than treating the prompt as an undifferentiated text buffer, the harness separates it into layers with distinct update rates, governance requirements, and failure modes.”

Label (W/M/X): X

## T37 · claim

Source: Token Reduction Is Not Cost Reduction

Claim: A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories.

Quote: “Recall is not task success; marker preservation is not task success; candidate precision is not task success; synthetic critical-drop tests are not task success; bytes removed are not billed savings; and shorter context can cause longer trajectories.”

Label (W/M/X): W

## T38 · inference

Section: Discussion

Statement: Chained RLM sits between the two. It passes a summary, blackboard and durable artifacts to a fresh root of the same model, because the working state otherwise stays inside one orchestration trajectory.

Its premises:
- Chained RLM's authors note that Recursive Language Models improve long-context inference without changing model weights, but the global working state still largely lives inside one orchestration trajectory.
- Chained RLM responds by passing a summary, blackboard, and durable artifacts to a fresh root of the same model.

Label (F/O): F

## T39 · sentence

Section: Context-centric models: compression, memory and context management

Sentence: The passages supplied do not include the paper on Context Language Models that treats the context as an editable file, so no comparison with it can be drawn here.

Claims of its section:
- The ICAE authors describe compressing a long context into memory slots that the model can condition on directly.
- The ICAE authors report about 1% added parameters and 4x compression on Llama, with latency and GPU memory gains.
- A survey notes that gist-token methods carry a cost in model modification.
- The Cartridges authors train a small KV cache per corpus from synthetic conversations with a context-distillation objective.
- The Cartridges authors report matching in-context learning on long-context benchmarks with far less memory and higher throughput.
- The MemGPT authors describe a system in which the model edits and searches its own memory.
- MemGPT also keeps a recursive summary of evicted messages at the head of its queue.
- The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed perfect.

Label (N/F/D): D

## T40 · claim

Source: Cartridges: Lightweight and general-purpose long context representations via self-study

Claim: Cartridges are reported to match in-context learning performance on long-context benchmarks at much lower serving cost.

Quote: “On challenging long-context benchmarks, Cartridges trained with self-study match ICL performance while using 38.6x less memory and enabling 26.4x higher throughput.”

Label (W/M/X): M

## T41 · claim

Source: Highlight-Then-Summarize: Learning to Compress Evidence for Long-Context Understanding

Claim: The same authors name a limitation of that approach: H2S is less naturally suited to tasks requiring broadly distributed context coverage.

Quote: “A current limitation is that H2S is less naturally suited to tasks requiring broadly distributed context coverage”

Label (W/M/X): W

## T42 · sentence

Section: Cost efficiency: token reduction versus billed cost

Sentence: None of the compression studies above reports provider-billed cost per successful coding task, and no passage covers recursive language models on cost, which leaves the comparison open.

Claims of its section:
- The central finding on this theme comes from a study of token-reduction tools for coding agents, which separates tokens removed from money spent.
- In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.
- The same work reports that aggressive compression reduced successful patch application on a SWE-bench Go subset.
- The In-context Autoencoder (ICAE) paper reports a 4× compression with gains in latency and GPU memory.
- Cartridges are reported to match in-context learning performance on long-context benchmarks at much lower serving cost.
- LongLLMLingua reports lower API costs and end-to-end latency together with higher performance than original prompts.
- For agent-level context assembly, ContextPipe reports fewer tokens and calls on a SWE-bench Pro subset, with a cost to caching.

Label (N/F/D): D

## T43 · claim

Source: Chained Recursive Language Models for Multi-Iteration Reasoning

Claim: The Chained RLM authors save raw predecessor trajectories but do not inject them automatically into every prompt.

Quote: “Raw predecessor trajectories are also saved, but they are not automatically injected into every prompt.”

Label (W/M/X): W

## T44 · inference

Section: Discussion

Statement: The compression approaches differ in mechanism. ICAE compresses context into memory slots the model conditions on, Cartridges train a small KV cache offline per corpus, and Highlight-Then-Summarize selects evidence and writes a question-conditioned summary. RLMs instead leave the prompt external and act on it with code.

Its premises:
- The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes.
- The Cartridges work trains a smaller KV cache offline for each corpus.
- H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary.
- The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt.

Label (F/O): F

## T45 · claim

Source: Token Reduction Is Not Cost Reduction

Claim: In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.

Quote: “The largest compression setup reduced delivered tool-output tokens by 38.4% but increased billed cost by 6.8%, while lighter compression produced only small and statistically uncertain savings.”

Label (W/M/X): W

## T46 · inference

Section: A research agenda

Statement: The cost study's retained telemetry does not record, per token, the turn of entry or the number of later calls that reused it, so it presents its marginal-cost equation only as a bounded conceptual model. This is a stated limitation of that study's evidence, not a recommendation drawn from the claims.

Its premises:
- The token-reduction cost study notes that its retained telemetry does not record, per token, the turn of entry and the number of later calls that reused it, so it presents its marginal-cost equation as a bounded conceptual model.

Label (F/O): F

## T47 · inference

Section: Discussion

Statement: Sources diverge on where capability ends up. One survey proposes that routine support moves into model weights while governance stays external, and another says the loop is both internalized into weights and externalized into skills and harnesses.

Its premises:
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The agent-loop survey argues that the loop is being internalized into weights and externalized into skills and harnesses.

Label (F/O): F

## T48 · claim

Source: LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression

Claim: LongLLMLingua reports lower API costs and end-to-end latency together with higher performance than original prompts.

Quote: “Experiments on the multidocument QA, multi-hop QA, and long context benchmarks demonstrate that LongLLMLingua compressed prompt can derive higher performance than original prompts while both API costs for inference and the end-to-end system latency are largely reduced.”

Label (W/M/X): W

## T49 · claim

Source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems

Claim: For coding in particular, one paper reports that context rot is the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions.

Quote: “As agentic coding systems including Claude Code, OpenAI Codex, and GitHub Copilot are increasingly deployed on production-scale repositories, a phenomenon now termed context rot has emerged: the progressive and nonlinear degradation of agent reasoning quality and tool calling reliability as the context window fills during extended coding sessions.”

Label (W/M/X): W

## T50 · inference

Section: Conclusions

Statement: The claims do not establish suitability for production coding on quality, cost or trace reuse. The cost evidence is cautionary, and the context-rot authors report the quality hypothesis untested.

Its premises:
- The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.
- In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.
- A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories.

Label (F/O): O

## T51 · claim

Source: Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems

Claim: The context-rot authors state that no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.

Quote: “no published empirical study has directly tested the joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition”

Label (W/M/X): W

## T52 · inference

Section: Discussion

Statement: Several sources describe a movement beyond prompts: one survey frames it as a shift from input-level linguistic control to system-level contextual orchestration, and the externalization review places the harness at a stage extending into persistent infrastructure.

Its premises:
- The same survey frames the broader movement as a shift from input-level linguistic control to system-level contextual orchestration.
- One review describes a shift from input-level linguistic control to system-level contextual orchestration.
- A review of externalization places the harness layer at the current stage, in which capability extends beyond prompt management into persistent infrastructure.

Label (F/O): F

## T53 · inference

Section: Discussion

Statement: The evidence on whether recursion is the useful ingredient pulls apart. The original paper reports inputs up to two orders of magnitude beyond context windows. Follow-up work finds recursion is not the primary driver of performance, finds that recursion often degrades performance within the model's window, and finds that depth-2 recursion degrades performance and inflates time and token costs.

Its premises:
- The RLM authors report that RLMs process inputs up to two orders of magnitude beyond model context windows.
- SRLM's authors conclude that recursion itself is not the primary driver of performance in RLM.
- The SRLM authors report that for context lengths within the model's window, RLMs with recursion often degrade performance relative to the base model.
- A reproduction study reports that depth-2 recursion degrades performance and inflates execution time and token costs.

Label (F/O): F

## T54 · claim

Source: MemGPT: Towards LLMs as Operating Systems

Claim: MemGPT also keeps a recursive summary of evicted messages at the head of its queue.

Quote: “The first index in the FIFO queue stores a system message containing a recursive summary of messages that have been evicted from the queue.”

Label (W/M/X): W

## T55 · claim

Source: Context Length Alone Hurts LLM Performance Despite Perfect Retrieval

Claim: The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed perfect.

Quote: “However, despite this robustness in retrieval, its accuracy drops by 24.2% compared to the short-context case.”

Label (W/M/X): X

## T56 · claim

Source: Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering

Claim: The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes.

Quote: “Rather than treating the prompt as an undifferentiated text buffer, the harness separates it into layers with distinct update rates, governance requirements, and failure modes.”

Label (W/M/X): X

## T57 · sentence

Section: Harness engineering: the structure around a fixed model

Sentence: The sources place the harness relative to prompt and context engineering in a consistent way.

Claims of its section:
- The externalization review describes memory as externalizing state across time, skills as externalizing procedural expertise, protocols as externalizing interaction structure, and harness engineering as the unification layer that coordinates them into governed execution.
- The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis.
- The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes.
- The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- The UniACE study reports large bidirectional score changes and model-ranking reversals when compared with source implementations.
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The code-as-harness survey lists open challenges including evaluation beyond final task success, verification under incomplete feedback, and regression-free harness improvement.

Label (N/F/D): D

## T58 · inference

Section: A research agenda

Statement: Compare RLMs and compression methods on coding tasks by billed cost and patch success, not token counts alone, because token removal has raised bills and lowered patch success.

Its premises:
- In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.
- The same work reports that aggressive compression reduced successful patch application on a SWE-bench Go subset.
- A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories.

Label (F/O): F

## T59 · sentence

Section: Harness engineering: the structure around a fixed model

Sentence: Evidence that the harness matters for measured results comes from evaluation work.

Claims of its section:
- The externalization review describes memory as externalizing state across time, skills as externalizing procedural expertise, protocols as externalizing interaction structure, and harness engineering as the unification layer that coordinates them into governed execution.
- The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis.
- The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes.
- The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- The UniACE study reports large bidirectional score changes and model-ranking reversals when compared with source implementations.
- The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.
- The code-as-harness survey lists open challenges including evaluation beyond final task success, verification under incomplete feedback, and regression-free harness improvement.

Label (N/F/D): F

## T60 · claim

Source: Token Reduction Is Not Cost Reduction

Claim: The same work reports that aggressive compression reduced successful patch application on a SWE-bench Go subset.

Quote: “On a SWE-bench Go subset, aggressive compression also reduced successful patch application.”

Label (W/M/X): W

## T61 · claim

Source: Chained Recursive Language Models for Multi-Iteration Reasoning

Claim: Long-context reasoning is described as a central direction in building agentic systems that work over large documents, codebases, transcripts, and multi-step data.

Quote: “Recently, long context reasoning in large language models (LLMs) have become a central direction in building agentic systems which can work over large documents, codebases, transcripts, and multi-step data (Plaat et al., 2025).”

Label (W/M/X): W

## T62 · claim

Source: TADI: Tool-Augmented Drilling Intelligence via Agentic LLM Orchestration over Heterogeneous Wellsite Data

Claim: The drilling system draws its conclusion from case studies and a qualitative ablation analysis, which it says suggest that domain-specialized tool design, rather than model scale alone, is the primary driver of analytical quality.

Quote: “the case studies and qualitative ablation analysis suggest that domain-specialized tool design, rather than model scale alone, is the primary driver of analytical quality in technical operations.”

Label (W/M/X): W

## T63 · inference

Section: Discussion

Statement: Prompt engineering is described consistently as designing instructions to guide a model without altering its parameters, and as a form of programming that customizes outputs and interactions.

Its premises:
- Prompt engineering is the natural starting point, and one survey describes it as a technique that involves strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters.
- Another paper describes prompts as a form of programming that can customize the outputs and interactions with an LLM.
- The pattern-catalog paper characterizes prompts as a form of programming that can customize the outputs and interactions with an LLM.

Label (F/O): F

## T64 · inference

Section: Discussion

Statement: Prompt engineering is also described as poorly consolidated: it is said to have conflicting terminology, to be treated as empirical and ad hoc without a standardized theoretical framework, and to be a critical yet loosely defined skill.

Its premises:
- A later survey treats prompt engineering as often lacking theory, noting that it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.
- The Prompt Report states that prompt engineering suffers from conflicting terminology and a fragmented ontological understanding of what constitutes an effective prompt.
- A 2026 survey likewise says prompt engineering is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.
- A practitioner-focused study calls prompt engineering a critical yet loosely defined skill.

Label (F/O): F

## T65 · claim

Source: A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT

Claim: Another paper describes prompts as a form of programming that can customize the outputs and interactions with an LLM.

Quote: “Prompts are also a form of programming that can customize the outputs and interactions with an LLM.”

Label (W/M/X): W

## T66 · claim

Source: Recursive Language Models Meet Uncertainty: The Surprising Effectiveness of Self-Reflective Program Search for Long Context

Claim: Follow-up work qualifies this picture: the SRLM study finds that recursion itself is not the primary driver of performance in RLM.

Quote: “Our findings show that recursion itself is not the primary driver of performance in RLM, and a simple self-reflective program search can match or surpass RLM without requiring self-query or explicit recursion mechanisms.”

Label (W/M/X): W

## T67 · claim

Source: ContextPipe: Database-Inspired Context Assembly for Long-Horizon Agents

Claim: ContextPipe's authors list comparisons of open-source and production coding harnesses under matched budgets as future work.

Quote: “to compare open-source and production coding harnesses under matched budgets with the same model, retry, and caching policies;”

Label (W/M/X): W

## T68 · sentence

Section: Context-centric models: compression, memory and context management

Sentence: The sources show several mechanisms for compressing or managing context, and they differ in where the compression is stored.

Claims of its section:
- The ICAE authors describe compressing a long context into memory slots that the model can condition on directly.
- The ICAE authors report about 1% added parameters and 4x compression on Llama, with latency and GPU memory gains.
- A survey notes that gist-token methods carry a cost in model modification.
- The Cartridges authors train a small KV cache per corpus from synthetic conversations with a context-distillation objective.
- The Cartridges authors report matching in-context learning on long-context benchmarks with far less memory and higher throughput.
- The MemGPT authors describe a system in which the model edits and searches its own memory.
- MemGPT also keeps a recursive summary of evicted messages at the head of its queue.
- The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed perfect.

Label (N/F/D): F

## T69 · claim

Source: In-context Autoencoder for Context Compression in a Large Language Model

Claim: The ICAE authors report about 1% added parameters and 4x compression on Llama, with latency and GPU memory gains.

Quote: “Experiments demonstrate that our lightweight ICAE, introducing about 1% additional parameters, effectively achieves $4\times$ context compression based on Llama, offering advantages in both improved latency and GPU memory cost during inference, and showing an interesting insight in memorization as well as potential for scalability.”

Label (W/M/X): W

## T70 · claim

Source: A comprehensive survey of prompt engineering and context engineering techniques in large language models

Claim: A 2026 survey likewise says prompt engineering is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.

Quote: “Despite the critical role of prompt engineering, it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework, leading to challenges such as output inconsistency, prompt sensitivity, and hallucinations.”

Label (W/M/X): W

## T71 · inference

Section: Discussion

Statement: Components are attributed across the stages: context adaptation and evolving playbooks, memory as a file system accessed through tool calls, tool schemas that consume context budget, orchestration roles separating planning, generation and evaluation, and verification as a harness component.

Its premises:
- The ACE paper defines context adaptation as modifying inputs with instructions, strategies, or evidence rather than updating weights.
- The ACE authors report that their framework treats contexts as evolving playbooks built through generation, reflection, and curation.
- Memory is another component, and one framework implements memory not as a vector database, but as a persistent file system accessible via tool calls.
- Tool use brings its own context costs, as tool schema definitions are reported to consume a disproportionate share of the available context budget.
- On multi-agent orchestration, the code-harness survey reports that long-running harnesses separate planning, generation and evaluation into distinct roles.
- The scaling-the-harness paper lists the components of a harness, including orchestration and verification.

Label (F/O): F

## T72 · inference

Section: Discussion

Statement: The cost evidence cautions against equating fewer tokens with lower cost. One coding-agent study found that the largest compression setup cut delivered tool-output tokens yet raised the bill, and that aggressive compression reduced successful patch application on a SWE-bench Go subset.

Its premises:
- In that study, the largest compression setup cut delivered tool-output tokens yet raised the bill.
- The same work reports that aggressive compression reduced successful patch application on a SWE-bench Go subset.
- A separate study of token reduction cautions that bytes removed are not billed savings and that shorter context can lengthen trajectories.

Label (F/O): F

## T73 · inference

Section: A research agenda

Statement: Evaluate injecting saved predecessor trajectories into later prompts, since they are saved but not automatically used.

Its premises:
- On reuse of traces, Chained RLM saves predecessor trajectories but does not inject them automatically into later prompts.
- The Chained RLM authors save raw predecessor trajectories but do not inject them automatically into every prompt.

Label (F/O): F

## T74 · sentence

Section: Introduction

Sentence: Both of these sources predate 2025, so they supply background for the earliest stage rather than evidence from the period in question.

Claims of its section:
- Prompt engineering is the natural starting point, and one survey describes it as a technique that involves strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters.
- Another paper describes prompts as a form of programming that can customize the outputs and interactions with an LLM.
- A later survey treats prompt engineering as often lacking theory, noting that it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.
- The same survey frames the broader movement as a shift from input-level linguistic control to system-level contextual orchestration.
- Context management has also become an object of empirical study: one paper notes that LLM agents on long-running tasks inevitably exceed their usable context window, forcing a choice about what history to discard.
- Memory is another component, and one framework implements memory not as a vector database, but as a persistent file system accessible via tool calls.
- Tool use brings its own context costs, as tool schema definitions are reported to consume a disproportionate share of the available context budget.
- One survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- A further survey takes the agent loop, not the model in isolation, as its unit of analysis.

Label (N/F/D): D

## T75 · claim

Source: The Agent Loop: A Survey of Control Strategies, Skills, and Harnesses for LLM Agents

Claim: The agent-loop survey argues that the loop is being internalized into weights and externalized into skills and harnesses.

Quote: “One thesis runs throughout: the loop is being pulled in two directions at once, internalized into weights and externalized into skills and harnesses.”

Label (W/M/X): W

## T76 · claim

Source: Harness Engineering for LLM Agents: A Survey of Harness Component Taxonomy, Evaluation, and Model–Harness Coevolution

Claim: The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.

Quote: “explaining the shifting functional boundary where routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external.”

Label (W/M/X): W

## T77 · claim

Source: Distilling Feedback into Memory-as-a-Tool

Claim: Memory is another component, and one framework implements memory not as a vector database, but as a persistent file system accessible via tool calls.

Quote: “we implement M not as a vector database, but as a persistent file system accessible via tool calls.”

Label (W/M/X): W

## T78 · claim

Source: Code as Agent Harness

Claim: Open problems named across the sources include evaluation beyond final task success and consistent shared state across multiple agents.

Quote: “We further outline open challenges for harness engineering, including evaluation beyond final task success, verification under incomplete feedback, regression-free harness improvement, consistent shared state across multiple agents, human oversight for safety-critical actions, and extensions to multimodal environments.”

Label (W/M/X): W

## T79 · sentence

Section: Limits of the evidence: unsettled boundaries and weak generalizability

Sentence: The passages do not settle whether these definitions hold beyond the domains studied.

Claims of its section:
- The context-compression experiment used a synthetic recall task and acknowledges the limits of its single-model, single-budget setup.
- The context-rot paper states that no published empirical study has directly tested its joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition.
- The drilling system draws its conclusion from case studies and a qualitative ablation analysis, which it says suggest that domain-specialized tool design, rather than model scale alone, is the primary driver of analytical quality.
- The UniACE study reports that comparisons with source implementations produced bidirectional score shifts and model-ranking reversals.
- The harness-aware survey distinguishes what existing comparisons establish from effects that remain entangled.

Label (N/F/D): F

## T80 · sentence

Section: Context-centric models: compression, memory and context management

Sentence: Other work moves compression offline or hands it to the model itself.

Claims of its section:
- The ICAE authors describe compressing a long context into memory slots that the model can condition on directly.
- The ICAE authors report about 1% added parameters and 4x compression on Llama, with latency and GPU memory gains.
- A survey notes that gist-token methods carry a cost in model modification.
- The Cartridges authors train a small KV cache per corpus from synthetic conversations with a context-distillation objective.
- The Cartridges authors report matching in-context learning on long-context benchmarks with far less memory and higher throughput.
- The MemGPT authors describe a system in which the model edits and searches its own memory.
- MemGPT also keeps a recursive summary of evicted messages at the head of its queue.
- The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed perfect.

Label (N/F/D): F

## T81 · sentence

Section: Mechanistic overlap and differences between RLMs and CLMs

Sentence: None of the supplied passages evaluates RLMs or CLMs on production coding, and none examines reuse of execution traces across tasks, so those questions remain open here.

Claims of its section:
- The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt.
- Chained RLM states that RLMs improve long-context inference without changing model weights.
- Chained RLM responds by passing a summary, blackboard, and durable artifacts to a fresh root of the same model.
- The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes.
- The Cartridges work trains a smaller KV cache offline for each corpus.
- The Cartridges authors report that self-study Cartridges match ICL performance while using 38.6x less memory and enabling 26.4x higher throughput.
- H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary.
- SRLM's authors conclude that recursion itself is not the primary driver of performance in RLM.
- A reproduction study reports that depth-2 recursion degrades performance and inflates execution time and token costs.
- A billing study of coding agents finds that user-side context layers account for only about 6% of cost.

Label (N/F/D): D

## T82 · sentence

Section: Context engineering: shifting from prompt text to system-level context

Sentence: Harness-oriented sources place context engineering inside a wider boundary.

Claims of its section:
- One survey of prompt and context engineering analyzes the shift from input-level linguistic control to system-level contextual orchestration and names context dilution and computational overhead as persistent limitations.
- The ACE paper defines context adaptation as modifying inputs with instructions, strategies, or evidence rather than updating weights.
- The ACE authors report that their framework treats contexts as evolving playbooks built through generation, reflection, and curation.
- The code-harness survey says prompt engineering changes instructions and context engineering changes what evidence is presented to the model, while harness engineering treats the operating environment itself as the object of analysis.
- The externalization review describes a harness that separates the prompt into layers instead of treating it as an undifferentiated text buffer, and calls this a structured form of context engineering.
- The scaling-the-harness paper lists a context constructor as one of six components of an agent.
- One empirical proposal describes context rot as progressive, nonlinear degradation of reasoning quality and tool-calling reliability as the context window fills.
- The same paper states that no published empirical study has directly tested its joint hypothesis linking codebase scale, context growth and tool attrition.

Label (N/F/D): F

## T83 · inference

Section: A research agenda

Statement: Develop shared definitions and a common vocabulary for the three stages, given the terminological fragmentation and the differing placement of the harness relative to context engineering.

Its premises:
- The Prompt Report states that prompt engineering suffers from conflicting terminology and a fragmented ontological understanding of what constitutes an effective prompt.
- A later survey treats prompt engineering as often lacking theory, noting that it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework.
- The externalization review describes a harness that separates the prompt into layers instead of treating it as an undifferentiated text buffer, and calls this a structured form of context engineering.
- The code-harness survey says prompt engineering changes instructions and context engineering changes what evidence is presented to the model, while harness engineering treats the operating environment itself as the object of analysis.

Label (F/O): F

## T84 · sentence

Section: Context-centric models: compression, memory and context management

Sentence: They also give no direct measurement of coding quality, cost or trace reuse for these compression methods.

Claims of its section:
- The ICAE authors describe compressing a long context into memory slots that the model can condition on directly.
- The ICAE authors report about 1% added parameters and 4x compression on Llama, with latency and GPU memory gains.
- A survey notes that gist-token methods carry a cost in model modification.
- The Cartridges authors train a small KV cache per corpus from synthetic conversations with a context-distillation objective.
- The Cartridges authors report matching in-context learning on long-context benchmarks with far less memory and higher throughput.
- The MemGPT authors describe a system in which the model edits and searches its own memory.
- MemGPT also keeps a recursive summary of evicted messages at the head of its queue.
- The authors of a controlled study report that accuracy fell by 24.2% for Llama-3.1-8B Instruct on long inputs even though retrieval stayed perfect.

Label (N/F/D): D

## T85 · claim

Source: Recursive Language Models

Claim: The RLM authors report that RLMs process inputs up to two orders of magnitude beyond model context windows.

Quote: “We find that RLMs can successfully process inputs up to two orders of magnitude beyond model context windows and, even for shorter prompts, dramatically outperform the quality of vanilla frontier LLMs and common long-context and coding scaffolds (e.g., on GPT-5 by a median across the evaluated benchmarks of $26\%$ against compaction, $130\%$ against CodeAct with sub-calls, and $13\%$ against Claude Code) across four diverse long-context tasks while having comparable cost.”

Label (W/M/X): W

## T86 · sentence

Section: Mechanistic overlap and differences between RLMs and CLMs

Sentence: The compression line instead modifies or trains parameters to shrink context.

Claims of its section:
- The original RLM paper describes a paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt.
- Chained RLM states that RLMs improve long-context inference without changing model weights.
- Chained RLM responds by passing a summary, blackboard, and durable artifacts to a fresh root of the same model.
- The ICAE work proposes leveraging an LLM to compress a long context into short compact memory slots that can be directly conditioned on by the LLM for various purposes.
- The Cartridges work trains a smaller KV cache offline for each corpus.
- The Cartridges authors report that self-study Cartridges match ICL performance while using 38.6x less memory and enabling 26.4x higher throughput.
- H2S describes a compress-then-reason paradigm that selects evidence and then writes a question-conditioned summary.
- SRLM's authors conclude that recursion itself is not the primary driver of performance in RLM.
- A reproduction study reports that depth-2 recursion degrades performance and inflates execution time and token costs.
- A billing study of coding agents finds that user-side context layers account for only about 6% of cost.

Label (N/F/D): D

## T87 · inference

Section: A research agenda

Statement: Compare coding harnesses under matched budgets, which is listed as future work.

Its premises:
- ContextPipe's authors list comparisons of open-source and production coding harnesses under matched budgets as future work.

Label (F/O): F

## T88 · inference

Section: A research agenda

Statement: Study evaluation beyond final task success, including verification under incomplete feedback and the risk that a new verifier accepts underspecified solutions.

Its premises:
- The code-as-harness survey lists open challenges including evaluation beyond final task success, verification under incomplete feedback, and regression-free harness improvement.
- Open problems named across the sources include evaluation beyond final task success and consistent shared state across multiple agents.
- The code-as-harness survey warns that a new verifier may improve pass rate by accepting underspecified solutions.

Label (F/O): F

## T89 · sentence

Section: Evaluation as a harness-stage component and performance dependence on the harness

Sentence: The sources place evaluation at the center of how harnesses are understood, and they converge on the claim that a benchmark score depends on more than the model.

Claims of its section:
- The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings.
- The UniACE authors state that a reported score reflects a complete model–harness–environment configuration rather than the model alone.
- In UniACE's comparisons with source implementations, the authors found large bidirectional score changes and model-ranking reversals.
- The harness-aware evaluation survey introduces a four-factor framework comprising the model, harness, environment, and evaluator, alongside the protocol under which they are tested.
- The harness engineering survey proposes a two-stage evaluation logic separating native capability-gap diagnosis from assessment of compensation effectiveness and net benefit.
- The code-as-harness survey warns that a new verifier may improve pass rate by accepting underspecified solutions.
- The scaling-the-harness paper argues that agent quality should be evaluated as a longitudinal systems property rather than a one-shot completion score.
- The externalization review suggests treating evaluation as externalized quality infrastructure rather than as a post-hoc measurement.

Label (N/F/D): F

## T90 · claim

Source: Think, But Don't Overthink: Reproducing Recursive Language Models

Claim: The reproduction study of recursive language models reports that depth-1 RLMs effectively boost accuracy on complex reasoning tasks, while deeper recursion degrades performance.

Quote: “While depth-1 RLMs effectively boost accuracy on complex reasoning tasks, applying deeper recursion (depth=2) or using RLMs on simple retrieval tasks paradoxically degrades performance and exponentially inflates execution time (e.g., from 3.6s to 344.5s) and token costs.”

Label (W/M/X): W
