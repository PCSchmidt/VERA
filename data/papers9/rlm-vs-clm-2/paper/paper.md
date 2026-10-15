# Cost Efficiency and Trace Reusability of Recursive Language Models and Context Language Models for Production Coding Workloads: What Is Established and What Is Not

## Abstract

This review paper asks: In a literature review of RLM (recursive language models that inspect and recursively call themselves over a prompt held in an external environment) and CLM (Shao et al., September 2026: models that treat their context as an updatable file, with suffix cache reuse), what do published results establish, and what do they leave unestablished, about each approach's cost efficiency (tokens, KV-cache reuse, latency) and trace reusability for production coding workloads, as distinct from long-context QA benchmarks? A small CPU-scale companion experiment would compare token and prefix-cache cost under an RLM-style recursive decomposition versus a CLM-style in-place context edit with suffix reuse, using a small open model on a public long-context or code-repository task. It rests on 47 claims from 12 sources, each checked against a quote from its source, drawn from 15 papers read in full and 16 read at the abstract. Its interpretation sections offer 12 statements judged to follow from those claims.

## Introduction

Long-context serving is moving from short conversations toward applications such as retrieval-augmented generation, long-document question answering and agent reasoning [R3]. In these settings prefill must process the entire context, and its computational cost grows rapidly with input length [R3]. A study of serving cost reports that prefill takes tens of percent of GPU time in production workloads, and more in agentic ones dominated by long, repeated tool and document context [R7]. A transformer's KV representation of a token is a function of its entire prefix, so exact reuse is confined to contexts that share a prefix verbatim [R7]. Long-context serving is moving toward applications such as agent reasoning, and in these settings prefill must process the entire context, with a computational cost that grows rapidly with input length. The agent harness must then manage context, since session history accumulates while each model call sees only a bounded window [R18]. Two approaches to this problem are the focus of the review. Recursive Language Models treat long prompts as part of an external environment and let the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt [R32]. The RLM authors report that it has comparable cost across four long-context tasks [R32]. Context Language Models (CLMs) are language models that natively manage their own context, implemented by treating the context as a file and allowing the model to make unrestricted updates to it [R17]. The CLM authors also co-design Suffix Cache Reuse for serving, reporting a 35% reduction in server-side compute relative to standard SGLang at matched performance [R17]. The CLM evaluation compares against MEM1, Self-Compact, ACM, and recursive language models (RLM) with a shared Mini-SWE-Agent backbone [R17]. With that motivation in view, the review turns to what these results show about token, cache and latency costs and about trace reuse in coding workloads.

## Method

The question this paper answers was proposed by VERA from the user's topic and confirmed by the user: In a literature review of RLM (recursive language models that inspect and recursively call themselves over a prompt held in an external environment) and CLM (Shao et al., September 2026: models that treat their context as an updatable file, with suffix cache reuse), what do published results establish, and what do they leave unestablished, about each approach's cost efficiency (tokens, KV-cache reuse, latency) and trace reusability for production coding workloads, as distinct from long-context QA benchmarks? A small CPU-scale companion experiment would compare token and prefix-cache cost under an RLM-style recursive decomposition versus a CLM-style in-place context edit with suffix reuse, using a small open model on a public long-context or code-repository task.

Search. 12 queries were sent to the paper-search services: “recursive language models long prompt external environment”; “CLM context as updatable file suffix cache reuse”; “prefix caching KV cache reuse LLM serving”; “context editing KV cache reuse position-independent caching”; “agent context management long-horizon coding agents”; “recursive task decomposition LLM agents token cost”; “repository-level code benchmark long context evaluation”; “SWE-bench agent trajectories cost efficiency analysis”; “survey long context language models efficiency”; “survey LLM agent memory and context compression”; “failure modes of recursive LLM calls error propagation latency”; “agent trajectory reuse caching reproducibility”. They retrieved 120 candidate papers. A relevance screen, judged on titles and abstracts, kept 31 and set aside 89.

Reading. Every kept paper was read at its abstract; 15 were also read in full text, and 16 at the abstract only. This gave 180 evidence passages, the only text the paper may quote.

Writing and checking. The evidence sections were drafted sentence by sentence; every sentence that attributes something to a source carries a quote copied from one of those passages. Each quote was checked to be verbatim in its source, and a judge other than the writer checked that the passage supports the sentence and that the quote alone states it; sentences that failed were repaired once or removed. 47 claims from 12 sources survived, resting on 37 distinct quotes (a quote used by more than one sentence is one piece of evidence). Sentences without a claim were checked too: a synthesis names the claims it rests on and was judged to follow from them; any other sentence was judged to state no fact. Interpretation sections, where present, rest only on those claims and are labelled as such.

Models. Written by anthropic/claude-sonnet-5.5; judged by anthropic/claude-sonnet-5.5, z-ai/glm-5.3-flash.

## Recursive Language Models: paradigm, reproductions, and reported cost on long-context tasks

The original RLM paper proposes Recursive Language Models as a general inference paradigm that treats long prompts as part of an external environment and lets the LLM programmatically examine, decompose, and recursively call itself over snippets of the prompt [R32].

A reproduction study extends the framework by varying recursion depth, which the original paper left as future work [R112]. The reproduction reports that depth-1 RLMs help on complex reasoning, while deeper recursion or use on simple retrieval degrades performance and inflates time and tokens [R112]. A separate systems extension, RLM-Extended, states that existing reference implementations of RLM have practical limitations in termination, reproducibility, and deployment [R69].

Taken together, the sources can be read side by side on how recursion depth relates to time and token use. Context Language Models are implemented by treating the context as a file and allowing the model to make unrestricted updates to this file [R17]. The CLM study compares CLMs against baselines including recursive language models (RLM) with a shared Mini-SWE-Agent backbone [R17].

## Context Language Models: context as an updatable file, Suffix Cache Reuse, and reported FLOP savings

The CLM paper introduces Context Language Models as models that natively manage their own context [R17]. Context Language Models implement their approach by treating the context as a file and allowing the model to make unrestricted updates to this file [R17]. The CLM paper compares CLMs against MEM1, Self-Compact, ACM, and recursive language models (RLM) with a shared Mini-SWE-Agent backbone [R17].

On cost, the CLM authors report matching the strongest baseline's accuracy on TerminalBench 2.1 with fewer FLOPs [R17]. On EdgeBench-10 with Qwen3.6-27B, the paper reports that CLM reached a higher score than summarization at far lower prefix-reuse compute [R17].

Suffix Cache Reuse is the serving co-design that reuses cached states of surviving tokens after an edit [R17]. The authors note that the surviving suffix tokens keep stale cache states encoding the previous prefix [R17]. The reported serving gain is a 35% reduction in server-side compute relative to standard SGLang at matched performance [R17].

The CLM paper reports prefix-reuse FLOPs under standard serving throughout, with additional SCR savings reported separately [R17].

## Serving-side KV-cache reuse for in-place edits and non-prefix contexts

The next step is to turn from the cost of recomputation in general to how cache reuse is handled once contexts are edited rather than only appended. The Leyline authors state that agentic conversations evolve through policy-driven editing, with failed tool calls retried and stale outputs dropped [R118]. Leyline reports that production agentic harnesses fall back to re-prefill on every edit [R118].

The discussion now moves to approaches that tackle this cost where the reused context is not a prefix. The EPIC authors report up to 8x TTFT improvement and 7x throughput gain over existing systems, with negligible or no accuracy loss [R123]. The CacheTune authors warn that directly reusing KV cache in non-prefix settings causes significant degradation in generation quality [R3]. The SemPIC authors state that, under a standard causal decoder, naively stitched caches are position aligned but contextually incomplete, and their quality can collapse [R109]. The Leyline authors report that their splice kernel lifts replay cache-hit by 11.2 points and cuts latency by up to 241 ms [R118]. The SMem authors report that deletion beats suffix recomputation by 8.5x at 512 blocks, while describing the setting as probing the cost model rather than a served regime [R7]. Taken together, these results show reuse beyond exact prefixes being pursued for latency, with reported gains in time to first token, throughput, cache-hit rate and latency, while the risk of degraded quality from reusing non-prefix or naively stitched caches is acknowledged across sources.

## Context management in coding agents: token-level evidence and its limits

The passages on coding-agent context management are considered next, with attention to what they measure. The CAT authors report that SWE-Compressor reaches a 57.6% solved rate on SWE-Bench-Verified under a 32B agent post-training setting [R88]. The CAT authors also report that under a 150-step interaction budget, CAT maintains competitive performance and uses the fewest tokens of all methods [R88]. The ACM authors state that their analysis shows effective context management reduces peak token pressure and yields more consistent solutions across independent trials [R47].

Work on Context Language Models is considered next. The Context Language Models paper describes reinforcement learning in which, because context edits change the input across turns, stepwise GRPO is used [R17]. The Scroll authors describe a setup in which model-written code searches, materializes, and transforms session state through exec, and only explicitly printed projections enter the model's working view for the next call [R18].

## Unestablished questions: head-to-head RLM versus CLM comparison, latency, and trace reuse

The CLM paper compares CLMs against MEM1, Self-Compact, ACM, and recursive language models with a shared Mini-SWE-Agent backbone [R17]. The CLM authors report that, on TerminalBench 2.1, CLM matched the strongest baseline's accuracy with 29.5% fewer FLOPs [R17]. The CLM paper reports prefix-reuse FLOPs under standard serving, with additional SCR savings reported separately [R17].

In the CLM paper, Suffix Cache Reuse (SCR) reuses the cached states of all surviving tokens after an edit and only re-prefills the newly inserted or appended tokens [R17]. The CLM authors report that, when Suffix Cache Reuse is further applied, it reduces server-side compute by 35% with matched performance compared with standard SGLang serving [R17].

The Leyline authors state that production agentic harnesses fall back to re-prefill on every edit, paying full prefix-recomputation cost [R118].

## Implications for a CPU-scale companion experiment and its transfer limits

The comparison turns on two distinct ways of changing a long context, and each is introduced in turn below. The RLM authors propose a general inference paradigm that treats long prompts as part of an external environment and lets the model programmatically examine, decompose, and recursively call itself over snippets of the prompt [R32].

The Context Language Models paper introduces Suffix Cache Reuse (SCR), under which an edit that replaces B with B′ reuses the cached states of all surviving tokens and re-prefills only the newly inserted or appended tokens [R17].

The Leyline paper asserts that production agentic harnesses fall back to re-prefill on every edit [R118]. The CacheTune authors report that, in their experiments, the optimized CPU-cache path preserves the benefits of reuse despite the additional data movement [R3]. One proposal has the model examine, decompose, and recursively call itself over snippets of a prompt held in an external environment (s2), while another has an edit replacing B with B′ reuse the cached states of surviving tokens and re-prefill only the newly inserted or appended tokens (s4). A further source asserts that production agentic harnesses fall back to re-prefill on every edit (s7), and another reports that an optimized CPU-cache path preserves the benefits of reuse despite additional data movement (s8).

## Discussion

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Prefill cost grows rapidly with input length as long-context serving moves toward applications such as retrieval-augmented generation, long-document question answering and agent reasoning, and production agentic workloads are reported to spend a larger share of GPU time on prefill. Token and cache cost are therefore plausible central dimensions for comparing RLM and CLM, although these sources do not themselves compare the two (C1, C2, C3). Exact KV reuse is confined to contexts sharing a verbatim prefix, and production agentic harnesses are reported to fall back to re-prefill on every edit. This is the cost problem that Context Language Models' Suffix Cache Reuse targets, since it reuses cached states of surviving tokens after an edit (C4, C43, C22, C41). The CLM authors acknowledge that surviving suffix tokens keep stale cache states encoding the previous prefix. Reuse after an in-place edit therefore departs from exact prefix reuse, and the claims do not say what this costs in quality beyond the matched-performance serving result (C23, C4, C24). Reported RLM cost evidence is thin and mixed: the original authors report comparable cost across four long-context tasks, while a reproduction finds that depth-1 helps on complex reasoning but deeper recursion or simple retrieval degrades performance and inflates time and tokens (C7, C13). The CLM paper reports compute figures for coding-agent settings, including 29.5% fewer FLOPs than the strongest baseline at matched accuracy on TerminalBench 2.1. These are FLOPs under standard prefix reuse, with SCR savings reported separately, so they are not latency or token measurements (C39, C40, C25).

## Conclusions

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Published results establish that CLM, which treats context as an editable file, reports lower FLOPs than baselines including RLM on a shared Mini-SWE-Agent backbone, and that SCR adds a 35% server-side compute reduction versus standard SGLang at matched performance (C8, C10, C39, C42). For RLM, the claims establish a recursive-decomposition paradigm with comparable cost on four long-context tasks and a reproduction showing that extra depth can inflate time and tokens. They do not establish its cost on production coding workloads (C6, C7, C13). The claims leave open a direct, controlled comparison of tokens, cache reuse and latency between RLM and CLM, and the trace reusability of either approach. They also leave open whether the 35% figure holds beyond the reported setting (C10, C24, C40).

## A research agenda

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Report wall-clock latency alongside FLOPs for CLM with and without SCR, because the reported gains are in compute (C25, C42). Vary RLM recursion depth on code tasks, because a reproduction study that varied depth (left as future work in the original paper) reported that depth-1 RLMs help on complex reasoning while deeper recursion degrades performance and inflates time and tokens. That study did not establish the effect on code workloads, which remains to be tested (C12, C13). Test the quality effect of stale suffix cache states after edits, as the CLM authors note them and non-prefix reuse is warned to degrade generation quality (C23, C29). Examine whether traces from each approach can be replayed or reused under harnesses that re-prefill on every edit (C43, C26).

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
[R47] Xiaochuan Li, Ryan Ming, Meng Chu et al.. ACM: Agentic Context Management for Long Horizon Tasks. 2026. arXiv:2607.23809. https://arxiv.org/abs/2607.23809
[R69] Devashish Komiya. RLM-Extended: Deterministic and Local-Model Inference for Recursive Language Models. 2026. doi:10.5281/zenodo.18317149. https://doi.org/10.5281/zenodo.18317149
[R88] Shukai Liu, Bo Jiang, Jian Yang et al.. Context as a Tool: Context Management for Long-Horizon SWE-Agents. 2026. arXiv:2512.22087. https://arxiv.org/abs/2512.22087
[R109] Hui Xie, Peng Xiao, Yutong Deng et al.. SemPIC: Learning Semantic Position-Independent KV Caches. 2026. arXiv:2607.28069. https://arxiv.org/abs/2607.28069
[R112] D. Wang. Think, But Don't Overthink: Reproducing Recursive Language Models. 2026. arXiv:2603.02615. https://arxiv.org/abs/2603.02615
[R118] Bole Ma, Jan Eitzinger, Harald Koestler. Leyline: KV Cache Directives for Agentic Inference. 2026. doi:10.48550/arxiv.2606.01065. https://doi.org/10.48550/arxiv.2606.01065
[R123] Junhao Hu, Wenrui Huang, Wang, Weidong et al.. EPIC: Efficient Position-Independent Caching for Serving Large Language Models. 2024. doi:10.48550/arxiv.2410.15332. https://doi.org/10.48550/arxiv.2410.15332
