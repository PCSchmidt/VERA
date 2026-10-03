## Literature review

The evidence on judge reliability for numeric and table-grounded claims is thin and mixed, and few of the supplied sources test the conditions named in the question directly. A financial-document study reports that even a strict LLM judge with access to ground truth disagrees with graph-verified truth in 5.9% of cases [R15]. The same study reports that a grounded judge, given the full source document but no ground truth, achieves only 54.3% agreement, with a 33.1% false acceptance rate [R15]. It adds that false acceptances concentrate in exact recall, multi-hop and threshold questions [R15].

A study of extractive QA gives a more favourable picture for numbers. It finds that LLM judges perform particularly well on number-related answers but struggle with more complex types such as job titles [R46]. The same work reports that zero-shot, context-free judging often yields the best evaluation performance [R46]. The two studies are not directly comparable, since the extractive QA work compares predicted answers to a gold answer, while the financial study concerns structured retrieval over documents. The sources do not say whether the difference arises from task type, answer format or judge setup. The QA study also notes that its human evaluation was small, with only 161 samples, each response assessed by a single annotator [R46].

On mitigation, evidence is partial. That study concerns legal correctness rather than numeric or table claims, so its transfer to them is not established. A survey reports that combining rating with explanation leads to higher correlations with human ratings [R37]. None of the supplied passages tests a judge equipped with a calculator, code execution or a recomputation step.

The table-verification sources concern models as verifiers rather than judges, but they bear on difficulty. FEVEROUS reports that for about 10% of claims numerical reasoning was selected as the main verification challenge, ranging from counting cells to arithmetic [R6]. A few-shot study found that with chain-of-thought prompting LLMs can reach strong performance on table QA and fact verification [R23]. That study also found that around 90% of sampled reasoning chains from correct predictions were faithful to the table [R23]. These results measure LLMs as table reasoners, not as judges of others' claims, so they do not establish judge agreement.

Methodological work cautions about how reliability is measured. One study argues that statements about a judge need gold labels or a varied scorer facet [R43]. Overall, what is not established is a controlled comparison of table-visible versus text-only judging, of arithmetic depth, or of tool-augmented judges against programmatic labels. Only the financial study offers programmatically verified labels, and it suggests that source access alone does not make judging reliable.

## Retrieval and its limits

This review rests on 5 search queries, which retrieved 60 candidate papers. A relevance screen kept 11 and set aside 49; 6 were read in full text and 5 at the abstract only. Where this review says that something is missing or not established, it means that these searches did not find it: it is not a measure of the literature, and no figure for how much of the field the searches missed is available for a topic given without a list of its key papers.

## References

[R6] Rami Aly, Zhijiang Guo, Michael Schlichtkrull et al.. FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information. 2021. doi:10.48550/arxiv.2106.05707. https://doi.org/10.48550/arxiv.2106.05707
[R15] Agus Sudjianto, Wingyan Lau. When the Judge is Wrong: Measuring LLM-as-Judge Reliability Against Graph-Verified Ground Truth in Financial Documents. 2026. doi:10.2139/ssrn.6482162. https://doi.org/10.2139/ssrn.6482162
[R23] Wenhu Chen. Large Language Models are few(1)-shot Table Reasoners. 2022. doi:10.48550/arxiv.2210.06710. https://doi.org/10.48550/arxiv.2210.06710
[R37] Haitao Li, Qian Dong, Junjie Chen et al.. LLMs-as-Judges: A Comprehensive Survey on LLM-based Evaluation Methods. 2024. doi:10.48550/arxiv.2412.05579. https://doi.org/10.48550/arxiv.2412.05579
[R43] Louis Yiven Zhu. Three Ways Classical Test Theory Can Mislead About LLM Judges. 2026. arXiv:2609.29709. https://arxiv.org/abs/2609.29709
[R46] Xanh Ho, Jiahao Huang, Florian Boudin et al.. Reassessing Extractive QA Datasets at Scale: LLM-as-a-Judge and In-Depth Analyses. 2025. arXiv:2504.11972. https://arxiv.org/abs/2504.11972
