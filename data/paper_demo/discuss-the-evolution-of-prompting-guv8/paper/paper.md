# From Prompts to Context to Harnesses: Definitions, Boundaries, and Attributed Components in Recent LLM Agent Literature

## Abstract

This review traces how prompt engineering, context engineering, and harnesses have been defined in recent LLM agent literature. Prompt engineering is consistently described as designing instructions to guide a model without altering its parameters, and as a form of programming. It is also described as poorly consolidated, with conflicting terminology, ad hoc practice, and no standardized theory. Several sources describe a movement beyond prompts: one survey frames it as a shift from input-level linguistic control to system-level contextual orchestration, and another places the harness at a stage extending into persistent infrastructure. Sources agree on the direction of the boundary but not its placement. Prompt engineering changes instructions, context engineering changes the evidence presented, and harness engineering takes the operating environment as its object, yet one review calls the harness a structured form of context engineering. Attributed components include context adaptation, memory accessed as a file system through tool calls, tool schemas that consume context budget, orchestration roles separating planning, generation, and evaluation, and verification. No single assignment of components to stages emerges. Evaluation evidence shows that changing the harness around a fixed model can alter performance and reverse rankings. Open questions include whether capability will move into weights or external harnesses, direct tests of context rot and tool attrition, broader context-management experiments, shared vocabulary, and evaluation beyond final task success.

## Introduction

The research question concerns how prompt engineering, context engineering, harnesses and agentic harnesses have been defined and bounded since 2025, and which technical components each stage is credited with. Prompt engineering is the natural starting point, and one survey describes it as a technique that involves strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters [R1]. Another paper describes prompts as a form of programming that can customize the outputs and interactions with an LLM [R11]. Both of these sources predate 2025, so they supply background for the earliest stage rather than evidence from the period in question.

A later survey treats prompt engineering as often lacking theory, noting that it is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework [R2]. The same survey frames the broader movement as a shift from input-level linguistic control to system-level contextual orchestration [R2]. Context management has also become an object of empirical study: one paper notes that LLM agents on long-running tasks inevitably exceed their usable context window, forcing a choice about what history to discard [R18].

Memory is another component, and one framework implements memory not as a vector database, but as a persistent file system accessible via tool calls [R24]. Tool use brings its own context costs, as tool schema definitions are reported to consume a disproportionate share of the available context budget [R20].

The harness concept moves the unit of analysis from the prompt or context to the execution system around the model. One survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings [R6]. A further survey takes the agent loop, not the model in isolation, as its unit of analysis [R8].

The passages supplied here do not offer a single agreed definition of each term or of the boundaries between them, and the review below must work from these partial and varied framings.

## Method

The question this paper answers was proposed by VERA from the user's topic and confirmed by the user: Between 2025 and the present, how have the definitions, scope, and claimed boundaries of prompt engineering, context engineering, harnesses, and agentic harnesses been articulated in the academic and practitioner literature, and which technical components (e.g., retrieval, memory, tool use, orchestration, evaluation loops) were attributed to each stage?

Search. 12 queries were sent to the paper-search services: “prompt engineering to context engineering definition”; “context engineering for large language model agents”; “agent harness design for LLM agents”; “agentic harness orchestration tool use memory”; “survey of context engineering techniques”; “retrieval-augmented generation and agent memory architectures”; “in-context learning and prompt design foundations”; “LLM agent scaffolding and tool-calling frameworks”; “benchmarks for evaluating LLM agent harnesses”; “long-context limitations context rot degradation”; “failure modes of autonomous LLM agents”; “survey of prompt engineering methods taxonomy”. They retrieved 120 candidate papers. A relevance screen, judged on titles and abstracts, kept 46 and set aside 74.

Reading. Every kept paper was read at its abstract; 15 were also read in full text, and 31 at the abstract only. This gave 195 evidence passages, the only text the paper may quote.

Writing and checking. The evidence sections were drafted sentence by sentence; every sentence that attributes something to a source carries a quote copied from one of those passages. Each quote was checked to be verbatim in its source, and a judge other than the writer checked that the passage supports the sentence and that the quote alone states it; sentences that failed were repaired once or removed. 59 claims from 18 sources survived. Interpretation sections, where present, rest only on those claims and are labelled as such.

Models. Written by anthropic/claude-sonnet-5.5; judged by z-ai/glm-5.3-flash.

## Prompt engineering: definitions, pattern catalogs, and terminological fragmentation

The supplied passages define prompt engineering mainly as instruction design for a fixed model. One survey describes it as strategically designing task-specific instructions, referred to as prompts, to guide model output without altering parameters [R1]. The pattern-catalog paper characterizes prompts as a form of programming that can customize the outputs and interactions with an LLM [R11]. The prompt pattern catalog paper justifies documenting prompts in pattern form by treating prompts as a form of programming: "Since prompts are a form of programming, it is natural to document them in pattern form." [R11].

Several sources report that the field's vocabulary and organization are unsettled. The Prompt Report states that prompt engineering suffers from conflicting terminology and a fragmented ontological understanding of what constitutes an effective prompt [R48]. A 2026 survey likewise says prompt engineering is frequently treated as an empirical, ad hoc practice lacking a standardized theoretical framework [R2]. A practitioner-focused study calls prompt engineering a critical yet loosely defined skill [R39].

The sources also differ in how they build taxonomies. The Prompt Report presents a taxonomy of 58 LLM prompting techniques [R48]. A practitioner-oriented study reports that its primary contribution is "a practice-based taxonomy of prompting strategies "in the wild," highlighting forms of interaction that extend beyond formal prompt engineering models." [R39]. The Prompt Report states that its stance is observational and that evaluation in the field is variable and unstandardized: "The field is new, and evaluation is variable and unstandardized-even the most meticulous experimentation may suffer from unanticipated shortcomings, and model outputs themselves are sensitive to meaning-preserving changes in inputs." [R48].

The passages say little about how prompt engineering is bounded against context engineering or harnesses. One review describes a shift from input-level linguistic control to system-level contextual orchestration [R2]. A review of externalization places the harness layer at the current stage, in which capability extends beyond prompt management into persistent infrastructure [R87].

## Context engineering: shifting from prompt text to system-level context

The surveyed sources describe context engineering as a move from crafting prompt text to managing the information that surrounds the model. One survey of prompt and context engineering analyzes the shift from input-level linguistic control to system-level contextual orchestration and names context dilution and computational overhead as persistent limitations [R2]. The ACE paper defines context adaptation as modifying inputs with instructions, strategies, or evidence rather than updating weights [R94]. The ACE authors report that their framework treats contexts as evolving playbooks built through generation, reflection, and curation [R94].

Harness-oriented sources place context engineering inside a wider boundary. The code-harness survey says prompt engineering changes instructions and context engineering changes what evidence is presented to the model, while harness engineering treats the operating environment itself as the object of analysis [R49]. The externalization review describes a harness that separates the prompt into layers instead of treating it as an undifferentiated text buffer, and calls this a structured form of context engineering [R87]. The scaling-the-harness paper lists a context constructor as one of six components of an agent [R26].

Context rot is the main failure mode the sources attach to this stage. One empirical proposal describes context rot as progressive, nonlinear degradation of reasoning quality and tool-calling reliability as the context window fills [R20]. The same paper states that no published empirical study has directly tested its joint hypothesis linking codebase scale, context growth and tool attrition [R20]. The passages leave open how the boundaries among these terms should be settled and how far the reported benchmark gains hold outside simulation.

## Harness engineering: the structure around a fixed model

The surveys in this set generally treat the harness as the structure wrapped around a fixed model, but they enumerate its parts differently. The externalization review describes memory as externalizing state across time, skills as externalizing procedural expertise, protocols as externalizing interaction structure, and harness engineering as the unification layer that coordinates them into governed execution [R87].

The sources place the harness relative to prompt and context engineering in a consistent way. The code-as-harness survey states that prompt engineering changes instructions and context engineering changes what evidence is presented to the model, whereas agentic harness engineering treats the operating environment itself as the object of analysis [R49]. The externalization review describes the harness as a structured form of context engineering that separates the prompt into layers with distinct update rates, governance requirements, and failure modes [R87].

Evidence that the harness matters for measured results comes from evaluation work. The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings [R6]. The UniACE study reports large bidirectional score changes and model-ranking reversals when compared with source implementations [R84].

The sources differ on where the harness boundary lies and leave several questions open. The harness survey proposes that routine capability-bearing support migrates inward into model weights while constraint-bearing governance functions remain external [R29]. The code-as-harness survey lists open challenges including evaluation beyond final task success, verification under incomplete feedback, and regression-free harness improvement [R49]. The passages supplied here do not settle a single agreed definition of the harness or a standard component list.

## Agentic harnesses: loops, multi-agent orchestration, and agentic RAG

The survey "The Agent Loop" states that every LLM agent, beneath its framework and its prompts, runs a loop: it observes, decides, acts, and observes again until it stops [R8]. The same survey states that cost, reliability and safety are decided by the loop rather than by the model alone [R8]. Another survey defines the agent harness as the external execution support structure built around the model [R29].

The scaling-the-harness paper lists the components of a harness, including orchestration and verification [R26]. The externalization review places the harness as the stage at which engineering attention moved from prompts to the operating environment [R87]. The code-harness survey describes production systems as wrapping the model in a managed development loop [R49].

On multi-agent orchestration, the code-harness survey reports that long-running harnesses separate planning, generation and evaluation into distinct roles [R49]. The Agentic RAG survey frames retrieval as part of this agentic design space, since agents use reflection, planning, tool use and multi-agent collaboration to manage retrieval [R17]. The survey on Agentic RAG concludes that "no single architecture is universally optimal; effectiveness depends on aligning complexity with task requirements." [R17].

The sources differ on where the loop's competence should sit. The agent-loop survey argues that the loop is being internalized into weights and externalized into skills and harnesses [R8]. Open problems named across the sources include evaluation beyond final task success and consistent shared state across multiple agents [R49].

## Evaluation as a harness-stage component and performance dependence on the harness

The sources place evaluation at the center of how harnesses are understood, and they converge on the claim that a benchmark score depends on more than the model. The harness-aware evaluation survey reports that changing the execution system around a fixed model can alter performance and even reverse model rankings [R6]. The UniACE authors state that a reported score reflects a complete model–harness–environment configuration rather than the model alone [R84]. In UniACE's comparisons with source implementations, the authors found large bidirectional score changes and model-ranking reversals [R84].

The sources differ in the remedies they propose for this dependence. The harness-aware evaluation survey introduces a four-factor framework comprising the model, harness, environment, and evaluator, alongside the protocol under which they are tested [R6]. The harness engineering survey proposes a two-stage evaluation logic separating native capability-gap diagnosis from assessment of compensation effectiveness and net benefit [R29].

Several sources also tie evaluation to safety and failure analysis. The code-as-harness survey warns that a new verifier may improve pass rate by accepting underspecified solutions [R49]. The scaling-the-harness paper argues that agent quality should be evaluated as a longitudinal systems property rather than a one-shot completion score [R26]. The externalization review suggests treating evaluation as externalized quality infrastructure rather than as a post-hoc measurement [R87].

The passages leave open how far these harness effects generalize, a gap that the harness-aware evaluation survey itself names among its research directions, and none of them settles whether evaluation belongs to a distinct harness stage.

## Limits of the evidence: unsettled boundaries and weak generalizability

The sources do not offer a single settled map of where prompt engineering ends and harness engineering begins. Another paper, by contrast, places test-driven governance, orchestrator-controlled phase order and bounded repair loops inside a prompt-engineering framing. That placement shows stages overlapping in practice, since orchestration and validation appear under the prompt label.

Much of the evidence is also narrow in scope. The context-compression experiment used a synthetic recall task and acknowledges the limits of its single-model, single-budget setup [R18]. The context-rot paper states that no published empirical study has directly tested its joint hypothesis that codebase scale drives context window growth, which in turn triggers measurable MCP tool attrition [R20]. The drilling system draws its conclusion from case studies and a qualitative ablation analysis, which it says suggest that domain-specialized tool design, rather than model scale alone, is the primary driver of analytical quality [R41].

Evaluation work shows why attributing effects to a single stage is hard. The UniACE study reports that comparisons with source implementations produced bidirectional score shifts and model-ranking reversals [R84]. The harness-aware survey distinguishes what existing comparisons establish from effects that remain entangled [R6]. The passages do not settle whether these definitions hold beyond the domains studied.

## Discussion

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Prompt engineering is described consistently as designing instructions to guide a model without altering its parameters, and as a form of programming that customizes outputs and interactions (C1, C2, C11). Prompt engineering is also described as poorly consolidated: it is said to have conflicting terminology, to be treated as empirical and ad hoc without a standardized theoretical framework, and to be a critical yet loosely defined skill (C3, C13, C14, C15). Several sources describe a movement beyond prompts: one survey frames it as a shift from input-level linguistic control to system-level contextual orchestration, and the externalization review places the harness at a stage extending into persistent infrastructure (C4, C19, C20). The sources agree on the direction of the boundary but phrase it differently. Prompt engineering changes instructions, context engineering changes the evidence presented, and harness engineering takes the operating environment as its object of analysis. The externalization review separately calls the harness a structured form of context engineering, so the boundary between context engineering and harness is not drawn identically (C24, C30, C25, C31). Components are attributed across the stages: context adaptation and evolving playbooks, memory as a file system accessed through tool calls, tool schemas that consume context budget, orchestration roles separating planning, generation and evaluation, and verification as a harness component (C22, C23, C6, C7, C42, C39). Evaluation evidence converges on the claim that the harness matters: changing the execution system around a fixed model can alter performance and reverse rankings, and a reported score reflects a model–harness–environment configuration (C8, C32, C48, C49). Sources diverge on where capability ends up. One survey proposes that routine support moves into model weights while governance stays external, and another says the loop is both internalized into weights and externalized into skills and harnesses (C34, C45).

## Conclusions

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

The literature articulates a progression from prompt-level instruction design, to context-level management of what the model sees, to harness-level treatment of the surrounding execution environment, though the exact boundaries are phrased differently across sources (C4, C24, C30, C20, C31). Memory, tool use, orchestration and verification are attributed mainly to the system-level and harness stages, but these claims do not show a single agreed assignment of components to stages (C6, C7, C39, C42, C25). Some of the empirical support is limited: one context-compression experiment used a synthetic task with a single model and budget, and the context-rot hypothesis is stated as untested by prior published studies (C55, C28, C56). The claims do not settle whether capability will mainly move into weights or into external harnesses (C34, C45).

## A research agenda

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Test the context-rot and tool-attrition hypothesis directly, since it is described as untested (C28, C56, C27). Repeat context-management comparisons with multiple models and budgets on non-synthetic tasks, because the existing experiment is limited to a single model and budget (C55, C5). Develop shared definitions and a common vocabulary for the three stages, given the terminological fragmentation and the differing placement of the harness relative to context engineering (C13, C3, C25, C24). Report evaluations as full model–harness–environment configurations and separate the entangled effects, since rankings can reverse (C48, C49, C59, C50). Study evaluation beyond final task success, including verification under incomplete feedback and the risk that a new verifier accepts underspecified solutions (C35, C46, C52). The sources describe a split in where agent functions reside: one harness survey proposes that routine capability-bearing support migrates into model weights while constraint-bearing governance functions remain external, and the agent-loop survey likewise argues that the loop is being internalized into weights and externalized into skills and harnesses. Both are proposals or arguments, and the sources do not report an empirical test of which functions migrate (C34, C45).

## Threats to validity

Coverage. The paper rests on what 12 queries found; the search was not repeated for the paper. A finding reported as missing means these searches did not find it, not that it does not exist.

Depth of reading. 31 of 46 kept papers were read at the abstract only, so their methods and caveats are known only as their abstracts state them.

What the checks cover. Each claim was checked against the passage it quotes, not against the whole source or the wider literature. A claim can be supported by its quote and still leave out a qualification stated elsewhere in the paper it cites. Interpretation sections were judged to follow from the claims they name; they were not checked against the sources.

Same-family grading. The writer is a Claude model; the judges are a different model family, and any independent scoring of this paper by a Claude model shares the writer's family.

## References

[R1] Pranab Sahoo, Ayush Singh, Sriparna Saha et al.. A Systematic Survey of Prompt Engineering in Large Language Models: Techniques and Applications. 2024. arXiv:2402.07927. https://arxiv.org/abs/2402.07927
[R2] Tonmoy Debnath, Md Nurul Absar Siddiky, Muhammad Enayetur Rahman et al.. A comprehensive survey of prompt engineering and context engineering techniques in large language models. 2026. doi:10.1016/j.cosrev.2026.100979. https://doi.org/10.1016/j.cosrev.2026.100979
[R6] Ahmed Y. Radwan, Athanasios V. Vasilakos, Shaina Raza. Harness-Aware Evaluation of LLM Agents: Systems, Benchmarks, and Protocols. 2026. doi:10.20944/preprints202609.2140.v1. https://doi.org/10.20944/preprints202609.2140.v1
[R8] Jungseob Lee, Chanjun Park. The Agent Loop: A Survey of Control Strategies, Skills, and Harnesses for LLM Agents. 2026. doi:10.2139/ssrn.7186738. https://doi.org/10.2139/ssrn.7186738
[R11] Jules White, Quchen Fu, Sam Hays et al.. A Prompt Pattern Catalog to Enhance Prompt Engineering with ChatGPT. 2023. doi:10.48550/arxiv.2302.11382. https://doi.org/10.48550/arxiv.2302.11382
[R17] Aditi Singh, Abul Ehtesham, Saket Kumar et al.. Agentic Retrieval-Augmented Generation: A Survey on Agentic RAG. 2025. doi:10.48550/arxiv.2501.09136. https://doi.org/10.48550/arxiv.2501.09136
[R18] Yash Zode. An Empirical Evaluation of Context-Management Strategies for Large Language Model Agents Under Forced Context Compression. 2026. doi:10.2139/ssrn.6961019. https://doi.org/10.2139/ssrn.6961019
[R20] Abrar Shahriar, Qurat-ul-ain Mastoi. Context Rot and MCP Tool Attrition in Production-Scale Codebases: An Empirical Investigation of Context-Driven Tool Calling Degradation in Agentic AI Coding Systems. 2026. doi:10.2139/ssrn.7344299. https://doi.org/10.2139/ssrn.7344299
[R24] Víctor Gallego. Distilling Feedback into Memory-as-a-Tool. 2026. arXiv:2601.05960. https://arxiv.org/abs/2601.05960
[R26] Shangding Gu. From Model Scaling to System Scaling: Scaling the Harness in Agentic AI. 2026. arXiv:2605.26112. https://arxiv.org/abs/2605.26112
[R29] Jieni Li, Yuan Wu, Yi Chang. Harness Engineering for LLM Agents: A Survey of Harness Component Taxonomy, Evaluation, and Model–Harness Coevolution. 2026. doi:10.20944/preprints202606.2203.v1. https://doi.org/10.20944/preprints202606.2203.v1
[R39] Dominic Vincent Ligot. Prompting in the Wild: A Qualitative Taxonomy of Practitioner-Driven Prompt Engineering Methods. 2026. doi:10.2139/ssrn.6129946. https://doi.org/10.2139/ssrn.6129946
[R41] Rong Lu. TADI: Tool-Augmented Drilling Intelligence via Agentic LLM Orchestration over Heterogeneous Wellsite Data. 2026. doi:10.20944/preprints202604.1820.v1. https://doi.org/10.20944/preprints202604.1820.v1
[R48] Sander Schulhoff, Michael Ilie, Nishant Balepur et al.. The Prompt Report: A Systematic Survey of Prompt Engineering Techniques. 2024. doi:10.48550/arxiv.2406.06608. https://doi.org/10.48550/arxiv.2406.06608
[R49] Xuying Ning, Katherine Tieu, Dongqi Fu et al.. Code as Agent Harness. 2026. arXiv:2605.18747. https://arxiv.org/abs/2605.18747
[R84] Pengyu Zhu, Lijun Li, Yaxing Lyu et al.. UniACE: A Unified Framework for Evaluating LLM Agentic Capabilities. 2026. doi:10.48550/arxiv.2605.27898. https://doi.org/10.48550/arxiv.2605.27898
[R87] Chenyu Zhou, Huacan Chai, Wenteng Chen et al.. Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering. 2026. arXiv:2604.08224. https://arxiv.org/abs/2604.08224
[R94] Qizheng Zhang, Changran Hu, Shubhangi Upasani et al.. Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models. 2025. arXiv:2510.04618. https://arxiv.org/abs/2510.04618
