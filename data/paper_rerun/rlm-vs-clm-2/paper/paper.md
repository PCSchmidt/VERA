# Recursive and Context Language Models for Coding Workloads: What Published Results Establish About Token, KV-Cache, Latency and Trace-Reuse Costs

## Abstract

This review paper asks: In a literature review of RLM (recursive language models that inspect and recursively call themselves over a prompt held in an external environment) and CLM (Shao et al., September 2026: models that treat their context as an updatable file, with suffix cache reuse), what do published results establish, and what do they leave unestablished, about each approach's cost efficiency (tokens, KV-cache reuse, latency) and trace reusability for production coding workloads, as distinct from long-context QA benchmarks? A small CPU-scale companion experiment would compare token and prefix-cache cost under an RLM-style recursive decomposition versus a CLM-style in-place context edit with suffix reuse, using a small open model on a public long-context or code-repository task. It rests on 51 claims from 14 sources, each checked against a quote from its source, drawn from 15 papers read in full and 16 read at the abstract. Its interpretation sections offer 11 statements judged to follow from those claims.

## Introduction

The question this review addresses starts from the cost of serving long contexts. R3 reports that serving is shifting from short conversations to long-context applications such as retrieval-augmented generation, long-document question answering, and agent reasoning [R3]. The same source says that prefill must process the entire context and that its computational cost grows rapidly with input length [R3]. R7 adds that a transformer's KV representation of a token is a function of its entire prefix, so exact reuse is confined to contexts that share a prefix verbatim [R7].

Beyond the serving cost of long contexts, agents that run over many steps raise a further question of how their context is managed. R18 describes repository-level software engineering as one of the long-running tasks for which LLM agents are increasingly used [R18]. R18 states that, as agent trajectories grow, session history accumulates continuously while each model invocation operates over a bounded context window, and identifies context management as a central challenge for the agent harness [R18].

Recent work approaches this context-management problem from two different directions, which the following paragraphs take in turn. The first, Recursive Language Models, is described by its authors as a general inference paradigm that treats long prompts as part of an external environment [R32]. The RLM authors report that it handles inputs up to two orders of magnitude beyond model context windows [R32].

The second approach is the Context Language Model, which this review treats explicitly. R17 reports that CLMs achieve 11.4% higher accuracy with 21.5% fewer prefix-reuse FLOPs than the strongest baseline on BrowseComp-Plus, and match its accuracy on TerminalBench 2.1 with 29.5% fewer FLOPs [R17]. R17 reports co-designing Suffix Cache Reuse for CLM serving, which it says further reduces server-side compute by 35% relative to standard SGLang at matched performance [R17]. R17 includes recursive language models among the baselines it compares against, on a shared Mini-SWE-Agent backbone [R17].

The sections that follow ask what these published results establish about token cost, KV-cache reuse, latency and trace reusability for production coding workloads, and a small CPU-scale experiment accompanies that analysis.

## Method

The question this paper answers was proposed by VERA from the user's topic and confirmed by the user: In a literature review of RLM (recursive language models that inspect and recursively call themselves over a prompt held in an external environment) and CLM (Shao et al., September 2026: models that treat their context as an updatable file, with suffix cache reuse), what do published results establish, and what do they leave unestablished, about each approach's cost efficiency (tokens, KV-cache reuse, latency) and trace reusability for production coding workloads, as distinct from long-context QA benchmarks? A small CPU-scale companion experiment would compare token and prefix-cache cost under an RLM-style recursive decomposition versus a CLM-style in-place context edit with suffix reuse, using a small open model on a public long-context or code-repository task.

Search. 12 queries were sent to the paper-search services: “recursive language models long prompt external environment”; “CLM context as updatable file suffix cache reuse”; “prefix caching KV cache reuse LLM serving”; “context editing KV cache reuse position-independent caching”; “agent context management long-horizon coding agents”; “recursive task decomposition LLM agents token cost”; “repository-level code benchmark long context evaluation”; “SWE-bench agent trajectories cost efficiency analysis”; “survey long context language models efficiency”; “survey LLM agent memory and context compression”; “failure modes of recursive LLM calls error propagation latency”; “agent trajectory reuse caching reproducibility”. They retrieved 120 candidate papers. A relevance screen, judged on titles and abstracts, kept 31 and set aside 89.

Reading. Every kept paper was read at its abstract; 15 were also read in full text, and 16 at the abstract only. This gave 180 evidence passages, the only text the paper may quote.

Writing and checking. The evidence sections were drafted sentence by sentence; every sentence that attributes something to a source carries a quote copied from one of those passages. Each quote was checked to be verbatim in its source, and a judge other than the writer checked that the passage supports the sentence and that the quote alone states it; sentences that failed were repaired once or removed. 51 claims from 14 sources survived, resting on 38 distinct quotes (a quote used by more than one sentence is one piece of evidence). Sentences without a claim were checked too: a synthesis names the claims it rests on and was judged to follow from them; any other sentence was judged to state no fact. Interpretation sections, where present, rest only on those claims and are labelled as such.

Models. Written by anthropic/claude-sonnet-5.5; judged by z-ai/glm-5.3-flash.

## Recursive Language Models: design, reproduction and reported costs on long-context tasks

The original RLM paper frames the approach as an inference paradigm over long prompts held outside the model [R32].

A reproduction study examined recursion depth, which the original work left at one [R112]. The reproduction reports that deeper recursion or use on simple retrieval hurts performance and inflates time and tokens [R112].

RLM-Extended addresses deployment gaps in the reference implementations, including local backends [R69].

Context Language Models (CLMs) are described by their authors as implemented by treating the context as a file and allowing the model to make unrestricted updates to that file [R17]. The CLM paper compares CLMs against MEM1, Self-Compact, ACM, and recursive language models (RLM) with a shared Mini-SWE-Agent backbone [R17]. The CLM authors report that their Suffix Cache Reuse for CLM serving reduces server-side compute by 35% relative to standard SGLang at matched performance [R17].

The next part turns from what each approach is and how it is built to how cost and reuse might be compared across them.

## Context Language Models (CLM): context as an updatable file and Suffix Cache Reuse

The CLM paper introduces Context Language Models as a way for models to manage their own context [R17]. The CLM authors implement this by treating the context as a file that the model may update without restriction [R17]. The coding comparison uses a shared Mini-SWE-Agent backbone and includes recursive language models among the baselines [R17].

On terminal coding, the CLM authors report that CLM matches the strongest baseline's accuracy on TerminalBench 2.1 with fewer FLOPs [R17].

In Suffix Cache Reuse, after an edit replaces a block, the cached states of all surviving tokens are reused and only the newly inserted or appended tokens are reprefilled [R17]. Standard prefix-cache reuse, by contrast, must re-prefill everything after the first mismatch [R17]. The CLM authors report that SCR cuts server-side compute by 35% against standard SGLang at matched performance [R17]. The CLM paper retains stale cache states for surviving suffix tokens, and its authors say this can even be beneficial in some cases [R17]. On terminal coding with a shared Mini-SWE-Agent backbone that includes recursive language models among the baselines, CLM is reported to match the strongest baseline's accuracy on TerminalBench 2.1 with fewer FLOPs, and its Suffix Cache Reuse is reported to cut server-side compute by 35% against standard SGLang at matched performance.

## Serving-side KV-cache reuse: prefix, non-prefix and in-place edit costs

This section turns to what serving-side work reports about reusing KV cache when context changes. The Context Language Models paper introduces Suffix Cache Reuse, in which an edit replacing B with B′ reuses the cached states of all surviving tokens and re-prefills only the newly inserted or appended tokens [R17]. The Context Language Models authors state that standard prefix-cache reuse must re-prefill all tokens after the first mismatch [R17]. Surviving suffix tokens under Suffix Cache Reuse keep stale states that encode the previous prefix, which the authors say can sometimes be beneficial [R17]. Leyline reports that production agentic harnesses fall back to re-prefill on every edit, paying full prefix-recomputation cost [R118]. Leyline's splice kernel lifts replay cache-hit by 11.2 points and cuts latency by up to 241 ms [R118]. The CacheTune authors note that directly reusing KV cache in non-prefix settings breaks cross-chunk attention and significantly degrades generation quality [R3]. SMem reports that deletion beats suffix recomputation by 8.5x at 512 blocks and 452x at 4096 blocks, which the authors describe as 32-256x the trained length and as probing the cost model rather than a served regime [R7].

## Context management for coding agents: token-level evidence and its limits

The sources on context management for coding agents are compared below with attention to token cost and accuracy. The Context Language Models paper reports that CLMs, applied zero-shot, achieve 11.4% higher accuracy with 21.5% fewer prefix-reuse FLOPs than the strongest baseline on BrowseComp-Plus [R17]. The same paper describes how CLMs can learn context-management strategies through reinforcement learning and internalize them in model weights [R17].

The CAT paper reports that SWE-Compressor reaches a 57.6% solved rate on SWE-Bench-Verified [R88]. The CAT authors also report that, under a 150-step budget, CAT maintains competitive performance and uses the fewest tokens across all methods [R88]. The ACM paper reports that its dual-constraint pipeline improves Qwen3.5-9B over the ReAct baseline by 8% on SWE-Bench Verified [R47].

The Focus study evaluated only N=5 SWE-bench Lite instances and reported a 22.7% token reduction with identical accuracy of 3/5 for both agents [R83]. The Scroll paper frames context management as a programming task, one that inherits the improving coding abilities of LLMs [R18]. The reported results come from different benchmarks, with different measures of cost: one paper reports 11.4% higher accuracy with 21.5% fewer prefix-reuse FLOPs on BrowseComp-Plus, another reports a 57.6% solved rate on SWE-Bench-Verified and the fewest tokens under a 150-step budget, another reports an 8% improvement over ReAct on SWE-Bench Verified, and another reports a 22.7% token reduction on only five SWE-bench Lite instances.

## Coding workloads versus long-context QA benchmarks and trace reusability

The following sections take up coding workloads, long-context benchmarks and trace reuse in turn. The CLM authors report that, on TerminalBench 2.1, CLM matches the strongest baseline's accuracy with 29.5% fewer FLOPs [R17]. The CLM authors also report that Suffix Cache Reuse reduces server-side compute by 35% with matched performance compared with standard SGLang serving [R17].

Long Code Arena provides six benchmarks for code processing tasks that require project-wide context [R62]. SWE-Bench-CL organizes GitHub issues into chronologically ordered sequences to evaluate whether an agent can accumulate experience and transfer knowledge across tasks [R36]. Long Code Arena's authors warn that reliance on open-source data can lead to contamination that skews evaluation results [R62].

## Unestablished questions and the scope of a CPU-scale companion experiment

The sections below turn to the cost and reuse evidence the retrieved passages offer for each approach. The Recursive Language Models paper proposes RLMs as an inference paradigm that treats long prompts as part of an external environment and lets the model examine, decompose and recursively call itself over snippets [R32]. The RLM authors report that it outperforms compaction, CodeAct with sub-calls and Claude Code across four long-context tasks while having comparable cost [R32].

The Context Language Models authors state that cache-reuse gains largely saturate by much shorter prefix [R17].

The next paragraph turns to work on serving costs for in-place edits. The Leyline authors state that production agentic harnesses fall back to re-prefill on every edit, paying full prefix-recomputation cost [R118]. The Leyline authors report that their splice kernel lifts replay cache-hit by 11.2 percentage points and cuts latency by up to 241 ms [R118].

The Scroll paper reports token counts rather than latency or dollar cost, because both depend on serving configuration [R18]. The Prompt Cache authors report TTFT reductions of 20× to 70× for CPU inference on LongBench [R125]. The cited passages report cost in different units: token counts without latency or dollar cost, time-to-first-token reductions on CPU inference, and cache-hit and latency changes under a splice kernel.

## Discussion

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Context Language Models (CLMs) are introduced by their authors as a way for models to manage their own context, implemented by treating the context as a file the model may update without restriction (C18, C15, C19). The motivation is consistent across sources: serving is shifting toward long-context applications, prefill cost grows rapidly with input length, and agents on repository-level software engineering face accumulating history against bounded context windows (C1, C2, C4, C5). Exact prefix reuse is confined to contexts sharing a prefix verbatim, and standard prefix-cache reuse must re-prefill everything after the first mismatch. Suffix Cache Reuse (SCR) reuses the cached states of surviving tokens after an edit and re-prefills only newly inserted or appended tokens (C3, C23, C27, C22). SCR reuses cached states of all surviving tokens after an edit and re-prefills only new or appended tokens. The price is stale states encoding the previous prefix, which the authors say can sometimes be beneficial; the claims give no general quality guarantee (C26, C28, C25). Reuse outside a shared prefix is not free in general: another source notes that non-prefix KV reuse breaks cross-chunk attention and significantly degrades generation quality. This pulls against treating CLM's stale-state reuse as unproblematic (C31, C28). The RLM evidence is of a different kind. Its authors report handling inputs two orders of magnitude beyond context windows and outperforming compaction, CodeAct with sub-calls and Claude Code across four long-context tasks at comparable cost. The claims do not say these tasks are coding workloads (C7, C46). A reproduction found that deeper recursion, or use on simple retrieval, hurts performance and inflates time and tokens. This qualifies the original cost claim, since the original left depth at one (C12, C13, C46).

## Conclusions

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

For CLM, the claims establish authors' reports of 11.4% higher accuracy with 21.5% fewer prefix-reuse FLOPs on BrowseComp-Plus, parity on TerminalBench 2.1 with 29.5% fewer FLOPs, and 35% less server-side compute than standard SGLang at matched performance (C8, C40, C41). For RLM, the claims establish reported capability and cost parity on long-context tasks, and a reproduction that finds token and time inflation under deeper recursion. They do not establish RLM cost on production coding workloads (C46, C13).

## A research agenda

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Test SCR's stale-state effect on output quality across edit sizes and positions, since the stale states are called sometimes beneficial while non-prefix reuse elsewhere degrades quality (C28, C25, C31). Check how far SCR gains persist at realistic prefix lengths, given the authors' statement that cache-reuse gains largely saturate at much shorter prefixes (C47, C41).

## Threats to validity

Coverage. The paper rests on what 12 queries found; the search was not repeated for the paper. A finding reported as missing means these searches did not find it, not that it does not exist. Works named in the question or the reader's emphasis: work by Shao was already among the review's sources (R17); “Context Language Models” was already among the review's sources (R17).

Depth of reading. 16 of 31 kept papers were read at the abstract only, so their methods and caveats are known only as their abstracts state them.

What the checks cover. Each claim was checked against the passage it quotes, not against the whole source or the wider literature. A claim can be supported by its quote and still leave out a qualification stated elsewhere in the paper it cites. Interpretation sections were judged to follow from the claims they name; they were not checked against the sources.

Same-family grading. The writer is a Claude model; the judges are a different model family, and any independent scoring of this paper by a Claude model shares the writer's family.

## References

[R3] Fei li, Song Liu, Yan Liu et al.. Adaptive KV Cache Reuse for Fast Long-Context LLM Serving. 2026. arXiv:2605.24022. https://arxiv.org/abs/2605.24022
[R7] Shengyao Wang, Jiang Liu. Memory as a cache: Exact context reuse and deletion by construction. 2026. arXiv:2609.32395. https://arxiv.org/abs/2609.32395
[R17] Rulin Shao, Shannon Zejiang Shen, Junjie Oscar Yin et al.. Context Language Models. 2026. arXiv:2609.37725. https://arxiv.org/abs/2609.37725
[R18] Yin Lin, Elaine Ang, Erkang Zhu et al.. Context as an Environment: Programmatic Context Management for Long-Horizon Agents. 2026. arXiv:2608.21690. https://arxiv.org/abs/2608.21690
[R32] Alex Zhang, Tim Kraska, Omar Khattab. Recursive Language Models. 2025. arXiv:2512.24601. https://arxiv.org/abs/2512.24601
[R36] Thomas T. Joshi, Shayan Chowdhury, Fatih Uysal. SWE-Bench-CL: Continual Learning for Coding Agents. 2025. arXiv:2507.00014. https://arxiv.org/abs/2507.00014
[R47] Xiaochuan Li, Ryan Ming, Meng Chu et al.. ACM: Agentic Context Management for Long Horizon Tasks. 2026. arXiv:2607.23809. https://arxiv.org/abs/2607.23809
[R62] Egor Bogomolov, Aleksandra Eliseeva, Galimzyanov, Timur et al.. Long Code Arena: a Set of Benchmarks for Long-Context Code Models. 2024. doi:10.48550/arxiv.2406.11612. https://doi.org/10.48550/arxiv.2406.11612
[R69] Devashish Komiya. RLM-Extended: Deterministic and Local-Model Inference for Recursive Language Models. 2026. doi:10.5281/zenodo.18317149. https://doi.org/10.5281/zenodo.18317149
[R83] Nikhil Verma. Active Context Compression: Autonomous Memory Management in LLM Agents. 2026. arXiv:2601.07190. https://arxiv.org/abs/2601.07190
[R88] Shukai Liu, Bo Jiang, Jian Yang et al.. Context as a Tool: Context Management for Long-Horizon SWE-Agents. 2026. arXiv:2512.22087. https://arxiv.org/abs/2512.22087
[R112] D. Wang. Think, But Don't Overthink: Reproducing Recursive Language Models. 2026. arXiv:2603.02615. https://arxiv.org/abs/2603.02615
[R118] Bole Ma, Jan Eitzinger, Harald Koestler. Leyline: KV Cache Directives for Agentic Inference. 2026. doi:10.48550/arxiv.2606.01065. https://doi.org/10.48550/arxiv.2606.01065
[R125] In Gim, Guojun Chen, Seung-seob Lee et al.. Prompt Cache: Modular Attention Reuse for Low-Latency Inference. 2023. doi:10.48550/arxiv.2311.04934. https://doi.org/10.48550/arxiv.2311.04934
