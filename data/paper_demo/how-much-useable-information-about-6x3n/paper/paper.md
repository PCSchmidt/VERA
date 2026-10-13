# Recovering Reusable Knowledge from Coding-Agent Traces: Design Rationale, Traceability, Failure and Repair History, and Test Intent

## Abstract

This review asks which categories of application knowledge (design rationale, requirements traceability, failure and repair history, and test intent) can be reliably recovered from coding-agent traces and reused for maintainability. The evidence supports only part of the question. Design rationale mined from Jira issue discussions can be reused: rationale-prompted LLMs produced 10×-18× more full-match patches, and developers often lack motivation to document rationale. This has not been shown for rationale recovered from agent traces. Agent provenance is weak, since decision trails are hard to reconstruct, though the supporting report relies on practitioner observation. Trajectories carry failure signal: failed runs are longer and more variable, and most still locate the right files. However, the length-failure link reverses once task difficulty is controlled, and automated attribution is limited (0.14-0.52 step-level judge accuracy) or costly (replay). Traceability results are promising but uneven, with concerns about datasets, scale and safety-critical use. Intent is the central difficulty, with 51.7% of 207 unresolved tasks involving ambiguous issues. Passing tests may hide overfitting, so test intent cannot be assumed to certify patches. Open work includes controlled provenance studies, larger validated failure categorization, cheaper attribution, and evaluating whether recovered specifications detect overfitting.

## Introduction

The review concerns what can be recovered from the traces of LLM-based coding agents and reused to make software easier to maintain and more robust. The survey of LLM-based agents for software engineering collects 124 papers and categorizes them from the software engineering and agent perspectives [R17]. OpenHands is described by its authors as a platform for agents that interact with the world in similar ways to those of a human developer [R22]. The OpenHands related-work section says that AutoCodeRover addresses GitHub issues via code search and abstract syntax tree manipulation [R22].

Maintenance tasks are the setting in which such agents are usually evaluated. The AutoCodeRover authors state that software engineering involves program improvement apart from coding, specifically software maintenance and software evolution [R10]. The agent survey describes SWE-bench as the first benchmark for end-to-end software maintenance, with 2,294 real-world GitHub issues across 12 popular Python repositories [R17]. The AutoCodeRover authors argue that the toughest challenge in program repair lies in inferring the intent of the developer or the specification [R10].

Work outside the agent literature addresses the kinds of information the question names. The DRMiner authors report that developers may lack motivation to document design rationales when they will not gain immediate benefit [R13]. The same authors report that advanced LLMs prompted with the mined rationales generate 10×-18× more full-match patches in automated program repair [R13]. The requirements traceability study states that understanding the relation between artifacts is crucial for understanding the system and for supporting tasks such as change impact analysis [R11]. The chapter on NLP for traceability notes that it is not yet clear how LLM-based approaches to trace link creation will scale [R20].

The passages supplied here stop short of the central question. They describe agents, benchmarks, rationale mining and traceability recovery, but none of them examines agent traces as a source of rationale, traceability, repair history or test intent, so that evidence gap frames the review that follows.

## Method

The question this paper answers was proposed by VERA from the user's topic and confirmed by the user: According to the existing literature on LLM-based coding agents (e.g., SWE-agent, OpenHands, AutoCodeRover) and on software provenance, design-rationale capture, and trace-based debugging, which categories of information about a software application (such as design rationale, requirements traceability, failure and repair history, and test intent) can be reliably recovered and reused from agent traces to improve software maintainability and robustness, and what limitations do published studies report?

Search. 12 queries were sent to the paper-search services: “SWE-agent agent-computer interface software engineering”; “OpenHands open platform AI software developers generalist agents”; “AutoCodeRover autonomous program improvement”; “agent trajectory analysis LLM coding agents failures”; “design rationale capture software engineering”; “requirements traceability recovery using large language models”; “software provenance tracking AI-generated code”; “trace-based debugging record and replay execution traces”; “SWE-bench benchmark resolving real-world GitHub issues”; “survey large language model agents for software engineering”; “automated program repair history mining bug fix patterns”; “limitations of LLM agents code maintainability hallucinated rationale negative results”. They retrieved 120 candidate papers. A relevance screen, judged on titles and abstracts, kept 48 and set aside 72.

Reading. Every kept paper was read at its abstract; 15 were also read in full text, and 33 at the abstract only. This gave 185 evidence passages, the only text the paper may quote.

Writing and checking. The evidence sections were drafted sentence by sentence; every sentence that attributes something to a source carries a quote copied from one of those passages. Each quote was checked to be verbatim in its source, and a judge other than the writer checked that the passage supports the sentence and that the quote alone states it; sentences that failed were repaired once or removed. 55 claims from 27 sources survived. Interpretation sections, where present, rest only on those claims and are labelled as such.

Models. Written by anthropic/claude-sonnet-5.5; judged by z-ai/glm-5.3-flash.

## Agent trajectories as a source of failure and repair history

Work on agent trajectories begins from the observation that outcome-only evaluation hides how agents behave. The authors of the comparative study of OpenHands, SWE-agent and Prometheus state that current evaluations treat agents as black boxes, focusing primarily on success rates while overlooking the rich information contained in their execution trajectories [R35]. The empirical study of OpenHands, SWE-agent and Prometheus trajectories reports that failed trajectories are consistently longer and exhibit higher variance than successful ones, with failure patterns differing significantly between agents [R35]. The two studies therefore disagree on whether length is a usable failure signal, and the evidence leaves that point unsettled.

On localization, the SWE-bench trajectory study finds that most trajectories identify the problematic files correctly, even in failures [R35]. SWE-agent's own appendix describes an automated categorization of 248 unresolved trajectories, validated against only 15 hand-labelled instances [R28].

Research on attributing failure to a particular step comes mostly from multi-agent settings rather than coding agents. DeFA, a dependency-guided attribution framework, is described as identifying the decisive error, responsible agent, and error category [R39]. A zero-replay debugging study reports that step-level attribution by an LLM judge reached only 0.14-0.52 accuracy on Who&When [R57]. The same work states that counterfactual replay is reliable but its cost grows linearly with candidate events [R57]. None of the supplied passages shows whether such attributions or replays yield reusable repair histories that improve later maintenance of a specific application, so that question stays open.

## Design rationale: evidence from issue logs rather than agent traces

The sources assembled here speak to design rationale mainly through issue logs and early hypertext tools, not through coding-agent traces. DRMiner's authors report that developers may lack motivation to document design rationales when they gain no immediate benefit, which leaves rationales without a standard capture [R13]. DRMiner is an approach that mines latent design rationales from developers' live discussion in open-source issue logs in Jira [R13]. In the DRMiner evaluation, advanced LLMs prompted with the extracted rationales generated 10×-18× more full-match patches in automated program repair and gained 10%-13% in CodeBLEU [R13].

The older gIBIS work shows that rationale capture is a long-standing aim. gIBIS is an application-specific hypertext system designed to facilitate the capture of early design deliberations [R121]. The authors of the gIBIS paper reported that early experiments suggested the IBIS method was still incomplete [R121].

Work on agent traces raises the same concern from the opposite direction. The LLMoxie report states that coding agents leave decision trails that are difficult to reconstruct after the fact [R59]. LLMoxie's authors describe current agentic practice as lacking mechanisms analogous to version control for tracking the provenance of AI-assisted contributions, which accumulates what they call intent debt [R59]. The LLMoxie report's operational lessons rest on practitioner observation and project artifacts rather than a controlled user study [R59].

The passages therefore show rationale being recovered from human issue discussions, and the absence of rationale being noted for agent work. None of them shows rationale reliably recovered from agent traces, which remains open.

## Requirements traceability link recovery with LLMs

The sources on requirements traceability link recovery (TLR) with LLMs describe a field that is active but constrained by data and reliability concerns. The Natural Language Processing for Requirements Traceability chapter states that TLR approaches often lack large enough and credible datasets [R20]. The same chapter reports that none of the automated trace recovery approaches are sufficiently good to be useful when dealing with real-world, safety-critical systems [R20].

Several studies report positive results for specific LLM-based designs. In the security-requirements study that linked requirements to goal models with GPT-3.5-turbo, the approach and tool yielded positive results, demonstrating a precision of 100%, a recall of 78.5%, and an F1-score of 87.9% [R46]. The evaluation behind that figure used one GRL model and 42 requirements, which is a small base. The bidirectional-convergence study reported that combining forward and backward recovery of use cases raised use-case recovery coverage from 65.5% to 75.1% [R67].

Work on ensembles and prompting shows trade-offs between recall, precision and cost. The inter-requirements ensemble study found that small LLMs reduce the candidate space with minimal loss of recall [R11]. In the study of LLM ensembles for candidate filtering in inter-requirements traceability, the authors report that while their LLM-based ensemble approach achieves comparable F2-scores to IR methods, it lags in precision [R11]. LightTraceLLM reported traceability performance comparable to a high-end baseline while cutting monetary inference cost by approximately 67-99% [R33]. TraceLLM concluded that traceability performance depends critically on the quality of prompt engineering [R109].

For requirements-to-code links, the evidence points to limits of textual similarity. The NL-PL study reports that relying solely on textual similarity is limited by the semantic gap between natural-language and programming-language artifacts [R101]. None of these passages tests recovery from coding-agent traces, and how well the results scale is left open.

## Test intent, code intent and specification inference

The sources describe intent inference mainly through specification-inference agents built on AutoCodeRover. The AutoCodeRover authors state that the toughest challenge in program repair lies in inferring the developer's intent or specification [R10]. AutoCodeRover gleans that intent from the project structure [R10]. The SpecRover authors describe their approach as more general, inferring specifications from program structure, program behavior, tests and other sources [R71].

SpecRover also adds a reviewer agent for validation. The SpecRover authors state that the reviewer agent can produce evidence of correctness for automatically generated fixes, such as an explanation of the patch, a reproducer test, and the accumulated specifications from different code elements [R71]. On SWE-bench Lite, SpecRover reports resolving 31% of issues [R71].

The sources also report limits on how reliably such intent can be recovered. In SpecRover's analysis of 207 unresolved SWE-bench Lite tasks, 107 (51.7%) had ambiguous issue descriptions, 61 (29.5%) had an incorrect fix location, and 39 (18.8%) had incorrect code modifications [R71]. The AutoCodeRover authors acknowledge that a patch passing the added tests may still be overfitting [R10]. The test-driven survey concludes that passing tests alone does not establish behavioral equivalence, effective feedback, or process adherence [R107]. The OSS-Fuzz study similarly finds that patches with high CodeBLEU scores still fail the given exploit input [R90].

The passages leave open whether inferred specifications can be reused after the original repair, since SpecRover's retention of evidence is proposed rather than evaluated for future regressions.

## Historical fix patterns and mined repair knowledge

The history-driven repair line of work starts from the observation that fixes recur. The authors of History Driven Program Repair state their main insight as follows: recurring bug fixes are common in real-world applications, and previously-appearing fix patterns can provide useful guidance to an automated repair technique [R127]. Getafix, which learns fix patterns from past human-written fixes for static-analysis bug categories, is reported to predict exactly the human-written fix as the top-most suggestion between 12% and 91% of the time, depending on the bug category [R91]. The wide range in that figure shows that how reliably mined fixes can be reused depends on the bug category.

FixMiner addresses how patterns are mined, and its authors argue that earlier approaches often do not yield fix patterns that are tractable and reusable as actionable input to APR systems [R55]. The FixMiner authors report that their mined patterns let the PARFixMiner prototype correctly fix 26 Defects4J bugs [R55].

Agent-based repair changes the setting. RepairAgent is described as treating the LLM as an agent that autonomously plans and executes actions to fix bugs by invoking suitable tools [R104]. DRMiner reports that advanced LLMs, when prompted with mined design rationales, generate 10×-18× more full-match patches [R13]. None of the supplied passages shows agent traces being mined for reusable fix patterns the way commit histories are, so that question remains open.

## Limitations: evidence gaps, benchmark scope, and maintainability claims

The sources agree that SWE-bench-style issue resolution is the standard testbed for coding agents, but they differ on how far results on it generalize. The SWE-bench-Live authors state that SWE-bench and its variants have become standard for evaluating LLMs on the issue resolution task [R29]. The SWE-bench-Live authors report that the same agent-LLM pair consistently performs worse on SWE-bench-Live than on SWE-bench [R29]. The same authors suggest that existing models may be overfitting to static benchmarks [R29].

Benchmark scope is a second limit. The SWE-bench-java authors note that SWE-bench is centered on Python and does not cover fields such as web applications, mobile applications, and system programming [R30].

Trace-based studies add limits on what resolution rates reveal. The large-scale trajectory study finds that the widely reported correlation between trajectory length and failure reverses direction once task difficulty is controlled [R81]. The debugging study of multi-agent traces cautions that its calibration may not transfer perfectly to production agent systems [R57].

On maintainability specifically, the evidence is thin. The LLMoxie authors report that current agentic AI practices lack mechanisms analogous to version control or commit history for tracking the provenance of AI-assisted contributions. The passages supplied here do not test whether information recovered from agent traces improves long-term maintainability or robustness, so that question remains open.

## Discussion

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

The claims agree that rationale is valuable but rarely captured: developers may lack motivation to document it without immediate benefit, and mining latent rationale from issue logs, when fed to LLMs, was reported to yield 10×-18× more full-match patches in program repair (C7, C18, C8, C20). Agent-side provenance is reported as weak: coding agents leave decision trails that are hard to reconstruct, and current practice lacks version-control-like provenance tracking, though the supporting report rests on practitioner observation and project artifacts, not a controlled study (C23, C24, C25). Failure history is partly recoverable from trajectories: failed ones are longer, more variable and differ by agent, and most trajectories find the right files even when failing. Yet the length–failure link is reported to reverse once task difficulty is controlled, so surface trace features are unreliable indicators (C12, C13, C54). Automated failure attribution is reported as limited: an LLM judge reached only 0.14-0.52 step-level accuracy on one benchmark, counterfactual replay is reliable but its cost grows linearly, and one categorization of unresolved trajectories was validated on only 15 hand-labelled instances (C16, C17, C14). Intent is the central difficulty. Inferring developer intent or specification is called the toughest repair challenge, and one analysis attributed 51.7% of 207 unresolved tasks to ambiguous issue descriptions (C6, C35, C40). Traceability results pull apart: individual LLM studies report strong figures such as 100% precision and 78.5% recall in one setting, while a survey chapter says no automated approach suffices for safety-critical systems and that scaling is unclear (C28, C27, C10). Passing tests is reported as insufficient evidence of correctness, so test intent recovered from agent traces cannot be assumed to certify patches (C41, C42, C43).

## Conclusions

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

The claims support that design rationale mined from issue discussion can be reused to help repair, and that past fix patterns are a reusable source of guidance. This is not shown for rationale recovered from agent traces themselves (C8, C44, C46). Failure information in trajectories carries signal, but attributing failures reliably is reported to be limited and costly (C12, C16, C17). Requirements traceability recovery shows promising but uneven results, with unresolved concerns about datasets, scale and safety-critical use (C26, C27, C31). Test intent is not shown to be reliably recoverable or sufficient, since passing tests may still hide overfitting. Whether any category improves maintainability from agent traces specifically remains unanswered by these claims (C41, C42).

## A research agenda

*Interpretation: VERA's reading of the claims named after each statement, judged to follow from them; not checked against quotes.*

Run controlled studies, beyond practitioner observation, of whether provenance and decision trails captured from agent runs can be reconstructed and reused for maintenance (C23, C24, C25). Validate trajectory failure categorization against larger hand-labelled sets, controlling for task difficulty (C14, C54). Develop cheaper failure attribution that improves on the low judge accuracy without the linear cost of replay (C16, C17). Test whether design-rationale mining, which DRMiner performs on Jira issue logs, transfers to agent traces. DRMiner reports that rationale-prompted LLMs generate 10×-18× more full-match patches, and that developers lack motivation to document rationales, so rationales have no standard capture. The evidence comes from issue logs, not agent traces (C8, C18, C19). Measure traceability recovery on real safety-critical data with larger credible datasets, and examine scaling (C26, C27, C10). Evaluate whether recovered test intent and specifications, such as the reproducer tests, patch explanations and accumulated specifications that SpecRover's reviewer produces as evidence of correctness, can detect overfitting patches beyond passing tests. AutoCodeRover's authors acknowledge that a patch passing the added tests may still overfit, and the test-driven survey concludes that passing tests alone does not establish behavioral equivalence (C38, C41, C42).

## Threats to validity

Coverage. The paper rests on what 12 queries found; the search was not repeated for the paper. A finding reported as missing means these searches did not find it, not that it does not exist.

Depth of reading. 33 of 48 kept papers were read at the abstract only, so their methods and caveats are known only as their abstracts state them.

What the checks cover. Each claim was checked against the passage it quotes, not against the whole source or the wider literature. A claim can be supported by its quote and still leave out a qualification stated elsewhere in the paper it cites. Interpretation sections were judged to follow from the claims they name; they were not checked against the sources.

Same-family grading. The writer is a Claude model; the judges are a different model family, and any independent scoring of this paper by a Claude model shares the writer's family.

## References

[R10] Yuntong Zhang, Haifeng Ruan, Zhiyu Fan et al.. AutoCodeRover: Autonomous Program Improvement. 2024. arXiv:2404.05427. https://arxiv.org/abs/2404.05427
[R11] Dominik Fuchß, Stefan Schwedt, Jan Keim et al.. Beyond Retrieval: A Study of Using LLM Ensembles for Candidate Filtering in Requirements Traceability. 2025. doi:10.1109/REW66121.2025.00006. https://doi.org/10.1109/REW66121.2025.00006
[R13] Jiuang Zhao, Zi-Tian Yang, Li Zhang et al.. DRMiner: Extracting Latent Design Rationale from Jira Issue Logs. 2024. doi:10.1145/3691620.3695019. https://doi.org/10.1145/3691620.3695019
[R17] Liu Jun-wei, Kaixin Wang, Yixuan Chen et al.. Large Language Model-Based Agents for Software Engineering: A Survey. 2026. arXiv:2409.02977. https://arxiv.org/abs/2409.02977
[R20] Jin L. C. Guo, Jan-Philipp Steghöfer, Andreas Vogelsang et al.. Natural Language Processing for Requirements Traceability. 2024. arXiv:2405.10845. https://arxiv.org/abs/2405.10845
[R22] Xingyao Wang, Boxuan Li, Yufan Song et al.. OpenHands: An Open Platform for AI Software Developers as Generalist Agents. 2024. arXiv:2407.16741. https://arxiv.org/abs/2407.16741
[R28] Yang, John, Jimenez, Carlos E., Alexander Wettig et al.. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. 2024. arXiv:2405.15793. https://arxiv.org/abs/2405.15793
[R29] Linghao Zhang, Shilin He, Chaoyun Zhang et al.. SWE-bench Goes Live!. 2025. arXiv:2505.23419. https://arxiv.org/abs/2505.23419
[R30] Daoguang Zan, Zhirong Huang, Ailun Yu et al.. SWE-bench-java: A GitHub Issue Resolving Benchmark for Java. 2024. arXiv:2408.14354. https://arxiv.org/abs/2408.14354
[R33] Nouf Alturayeif, Jameleddine Hassine, Irfan Ahmad. Toward Cost-Efficient Automated Requirements Traceability with Large Language Models. 2026. doi:10.1109/rew72749.2026.00019. https://doi.org/10.1109/rew72749.2026.00019
[R35] Oorja Majgaonkar, Zhiwei Fei, Xiang Li et al.. Understanding Code Agent Behaviour: An Empirical Study of Success and Failure Trajectories. 2025. doi:10.48550/arxiv.2511.00197. https://doi.org/10.48550/arxiv.2511.00197
[R39] Bo Deng, Xinlei Zheng, Yi Wei et al.. DeFA: Dependency-Guided Failure Attribution for LLM Agents. 2026. arXiv:2610.01256. https://arxiv.org/abs/2610.01256
[R46] Jameleddine Hassine. An LLM-based Approach to Recover Traceability Links between Security Requirements and Goal Models. 2024. doi:10.1145/3661167.3661261. https://doi.org/10.1145/3661167.3661261
[R55] Anil Koyuncu, Kui Liu, Tegawendé F. Bissyandé et al.. FixMiner: Mining relevant fix patterns for automated program repair. 2020. arXiv:1810.01791. https://arxiv.org/abs/1810.01791
[R57] Hyeonjeong Cha, Daein Weon, Dong Ho Kang. Knowledge-Based Zero-Replay Debugging of Multi-Agent LLM Traces. 2026. arXiv:2606.14805. https://arxiv.org/abs/2606.14805
[R59] Landung Setiawan, Anant Mittal, Cordero Core et al.. LLMoxie: Exploring Agentic AI for Scientific Software Development. 2026. arXiv:2607.02703. https://arxiv.org/abs/2607.02703
[R67] Jinhyup Lee, Janghwan Kim, Chaeyun Seo et al.. Requirement Traceability based on Bidirectional Convergence of Intermediate Artifact Recovery for AI Software Development. 2026. doi:10.30693/smj.2026.15.8.89. https://doi.org/10.30693/smj.2026.15.8.89
[R71] Haifeng Ruan, Yuntong Zhang, Abhik Roychoudhury. SpecRover: Code Intent Extraction via LLMs. 2024. arXiv:2408.02232. https://arxiv.org/abs/2408.02232
[R81] Tural Mehtiyev, Wesley K. G. Assunção. Beyond Resolution Rates: Behavioral Drivers of Coding Agent Success and Failure. 2026. doi:10.48550/arxiv.2604.02547. https://doi.org/10.48550/arxiv.2604.02547
[R90] Yuntong Zhang, Jiawei Wang, Dominic Berzin et al.. Fixing Security Vulnerabilities with AI in OSS-Fuzz. 2024. arXiv:2411.03346. https://arxiv.org/abs/2411.03346
[R91] Johannes Bader, Andrew Scott, Michael Pradel et al.. Getafix: learning to fix bugs automatically. 2019. doi:10.1145/3360585. https://doi.org/10.1145/3360585
[R101] Zhiyuan Zou, Bangchao Wang, Peng Liang et al.. Natural Language-Programming Language Software Traceability Link Recovery Needs More than Textual Similarity. 2025. arXiv:2509.05585. https://arxiv.org/abs/2509.05585
[R104] Islem Bouzenia, Prémkumar Dévanbu, Michael Pradel. RepairAgent: An Autonomous, LLM-Based Agent for Program Repair. 2024. doi:10.48550/arxiv.2403.17134. https://doi.org/10.48550/arxiv.2403.17134
[R107] Yunhao Liang, Chengguang Gan, Ruixuan Ying et al.. Test-Driven Approaches to Software Engineering with Large Language Models: A Survey of Phases, Tasks, and Agent Skills. 2026. https://openalex.org/W7213372607. https://openalex.org/W7213372607
[R109] Nouf Alturayeif, Irfan Ahmad, Jameleddine Hassine. TraceLLM: leveraging large language models with prompt engineering for enhanced requirements traceability. 2026. arXiv:2602.01253. https://arxiv.org/abs/2602.01253
[R121] Jeff Conklin, Michael L. Begeman. gIBIS: a hypertext tool for exploratory policy discussion. 1988. doi:10.1145/58566.59297. https://doi.org/10.1145/58566.59297
[R127] Xuan-Bach D. Le, David Lo, Claire Le Goues. History Driven Program Repair. 2016. doi:10.1109/saner.2016.76. https://doi.org/10.1109/saner.2016.76
