# ruff: noqa: E501
"""Build the seeded test set for the inference check (AUD-F-11, Increment 6): `data/seeded_inference/`.

Each item is an interpretation statement with its premises and the premise claims' text, labelled by construction:

- **control** (label `follows`): a cautious reading of two or three real claims from a committed review, written by hand.
- **reversed**, **overstated**, **new_fact** (label `fault`): hand-written variants of a control that reverse its
  direction, overstate its strength, or add a fact the claims do not hold. These test the judge layer.
- **irrelevant_premise** (`fault`): a control's text, with premises from another review of the same split. Judge layer
  (and the name rule, when the text names something only its own review mentions).
- **named_source**, **unsupported_number** (`fault`): a control with a system name or a figure its premises lack. These
  test the deterministic layer and are reported apart from the judge's figures.

Claims come from nine committed reviews (`data/literature/*/claims.jsonl`, `data/app/live/*/claims.jsonl`), referred to
by their line number. The split is by review: dev reviews may be used to check the question's wording; the test split
and the check's source are hashed (`split.json`) before the one test run (`scripts/measure_inference.py`).

Provenance: controls and variants were written by Claude Code (the agent that also wrote the check) on 2026-10-11, and
are disclosed as such; Chris may relabel any item before the freeze. Usage: uv run python scripts/build_inference_set.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "seeded_inference"
REVIEWS = {
    "conformal-shift": "data/literature/conformal-shift", "credal-dro": "data/literature/credal-dro",
    "llm-judge-numbers": "data/literature/llm-judge-numbers", "research-agents-eval": "data/literature/research-agents-eval",
    "tabular-trees-vs-nets": "data/literature/tabular-trees-vs-nets", "tree-explain": "data/literature/tree-explain",
    "agent-traces": "data/app/live/how-well-do-agent-traces-record-soft-0kdg", "rlm-vs-clm": "data/app/live/rlm-vs-clm-2",
    "rehearsal-1": "data/app/live/rehearsal-1",
}  # fmt: skip
DEV = ["conformal-shift", "research-agents-eval", "rlm-vs-clm"]
# review -> controls: (premise line numbers, control, reversed, overstated, new_fact)
CONTROLS: dict[str, list[tuple[list[int], str, str, str, str]]] = {
    "conformal-shift": [
        ([1, 2], "The coverage guarantee of weighted conformal prediction depends on knowing the likelihood ratio, so it is not assured when the ratio has to be estimated.",
         "The coverage guarantee of weighted conformal prediction holds whether or not the likelihood ratio is known.",
         "Weighted conformal prediction always fails to cover whenever the likelihood ratio has to be estimated.",
         "The coverage guarantee of weighted conformal prediction depends on knowing the likelihood ratio, and in practice the ratio is estimated with kernel density methods."),
        ([4, 6], "When the weights must be learned, the sources suggest coverage can fall short, by an amount tied to how well the weights are estimated.",
         "When the weights must be learned, the sources suggest coverage improves, regardless of how well the weights are estimated.",
         "Learned weights make weighted conformal prediction useless, as coverage collapses in every case.",
         "When the weights must be learned, coverage can fall short, which is why practitioners have abandoned the method in deployed systems."),
    ],
    "credal-dro": [
        ([2, 4], "Two studies agree that out-of-sample performance is not monotone in the Wasserstein radius, which suggests the radius has to be tuned rather than simply made large.",
         "Two studies agree that out-of-sample performance improves steadily as the Wasserstein radius grows, so a larger radius is always better.",
         "The studies prove that a single universal optimal radius exists for every problem.",
         "Two studies agree that out-of-sample performance is not monotone in the Wasserstein radius, and cross-validation is known to find the optimal radius reliably."),
        ([0, 3], "A larger radius buys reliability of the guarantee, according to the portfolio experiments, though the guarantee itself rests on choosing the radius suitably.",
         "A larger radius reduces the reliability of the guarantee, according to the portfolio experiments.",
         "Any radius, however chosen, guarantees that the true distribution lies in the ball.",
         "A larger radius buys reliability of the guarantee, and it also lowers the computational cost of the robust problem."),
    ],
    "llm-judge-numbers": [
        ([0, 1, 2], "In the financial-document study, an LLM judge was unreliable on numbers even when it could see the source, and access to ground truth reduced but did not remove its errors.",
         "In the financial-document study, an LLM judge that could see the source checked numbers reliably without ground truth.",
         "LLM judges can never be trusted to check any number, in any domain.",
         "In the financial-document study, an LLM judge was unreliable on numbers even when it could see the source, and fine-tuning the judge fixed the problem."),
        ([4, 6], "For extractive QA with context, judging numbers looks promising, though the supporting human evaluation was small.",
         "For extractive QA with context, judge scores were unrelated to human evaluations of number answers.",
         "For extractive QA, LLM judges are proven to be as accurate as humans on every kind of answer.",
         "For extractive QA with context, judging numbers looks promising, and the result has since been replicated on medical records."),
    ],
    "research-agents-eval": [
        ([3, 4, 5], "PaperBench relies on an LLM judge whose accuracy its own authors consider not yet sufficient, so its scores carry judge error.",
         "PaperBench's authors consider their LLM judge's accuracy fully settled.",
         "PaperBench scores are meaningless because its judge is wrong most of the time.",
         "PaperBench relies on an LLM judge whose accuracy its own authors consider not yet sufficient, and the judge was later replaced by human graders."),
        ([2, 7], "Benchmark results for research agents should be read with caution, since one benchmark was found to have construct-validity problems and repeated evaluations can disagree.",
         "Benchmark results for research agents are stable and valid, since repeated evaluations agree and the benchmarks measure what they claim.",
         "Every research-agent benchmark is invalid.",
         "Benchmark results for research agents should be read with caution, and most leaderboards have now been withdrawn for that reason."),
    ],
    "tabular-trees-vs-nets": [
        ([1, 2], "One study suggests that the advantage of gradient-boosted trees appears only as datasets grow, with little to separate the models at small sizes.",
         "One study suggests that gradient-boosted trees lead clearly at small sizes and lose their advantage as datasets grow.",
         "Gradient-boosted trees beat neural networks on every dataset larger than a few rows.",
         "One study suggests that the advantage of gradient-boosted trees appears only as datasets grow, because neural networks overfit large tables."),
        ([3, 5, 6], "The sources disagree on whether trees or tuned neural networks win on mid-sized tables, and part of the disagreement may come from different dataset choices.",
         "The sources agree that tuned neural networks never beat trees on mid-sized tables.",
         "Dataset choice fully explains every disagreement between the tree and neural-network studies.",
         "The sources disagree on whether trees or tuned neural networks win on mid-sized tables, and a later meta-analysis settled the question in favour of trees."),
    ],
    "tree-explain": [
        ([0, 1], "Explaining tree models with a functional decomposition is harder under correlated features, since the classical decomposition relies on independence that realistic data generally lacks.",
         "Correlated features make functional decompositions of tree models easier, since the classical decomposition does not depend on independence.",
         "Functional decompositions of tree models are impossible whenever any two features are correlated.",
         "Explaining tree models with a functional decomposition is harder under correlated features, and this is the main reason regulators reject such explanations."),
        ([4, 5], "On the evidence of its own paper, TreeHFD may separate effects more cleanly than TreeSHAP, though this rests on the authors' experiments.",
         "On the evidence of its own paper, TreeSHAP separates effects more cleanly than TreeHFD.",
         "TreeHFD has been shown to dominate TreeSHAP on every dataset and every model.",
         "On the evidence of its own paper, TreeHFD may separate effects more cleanly than TreeSHAP, and it runs ten times faster."),
    ],
    "agent-traces": [
        ([0, 1, 2], "Agent tooling appears to record execution traces as a matter of course, with tasks carrying a status, which suggests traces are widely available to study.",
         "Agent tooling rarely records execution traces, so traces are seldom available to study.",
         "Every agent run ever executed has a complete trace that captures all of its reasoning.",
         "Agent tooling appears to record execution traces as a matter of course, and these traces are usually retained for years by default."),
        ([3, 5], "Trace formats are not yet standard: one study had to unify agents' logs into a common format, and the main conventions leave some orchestration phases unrepresented.",
         "Trace formats are already standard, so agents' logs can be compared without conversion.",
         "No two agent trace formats can ever be reconciled.",
         "Trace formats are not yet standard, and a standards body is expected to publish one next year."),
    ],
    "rlm-vs-clm": [
        ([0, 1], "Recursive querying of long prompts may not pay off everywhere, since an independent reproduction found deeper recursion and simple retrieval tasks hurt performance and cost.",
         "Deeper recursion improved performance and reduced cost in the independent reproduction.",
         "Recursive language models are worse than standard models on every task.",
         "Recursive querying of long prompts may not pay off everywhere, and the original authors have withdrawn their paper."),
        ([4, 6], "On the one benchmark reported, CLM reaches the strongest baseline's accuracy at lower compute, in a comparison that included RLM under a shared backbone.",
         "On the one benchmark reported, CLM needed more compute than the strongest baseline to reach its accuracy.",
         "CLM is more efficient than RLM on every benchmark and every backbone.",
         "On the one benchmark reported, CLM reaches the strongest baseline's accuracy at lower compute, and it also uses less memory."),
    ],
    "rehearsal-1": [
        ([2, 3], "Under covariate shift with known density ratios validity can be restored, but without restrictions on how the conditional distribution shifts, target coverage cannot be pinned down at all.",
         "Even under unrestricted conditional shift, target coverage can be pinned down precisely.",
         "Conformal prediction is worthless under any distribution shift.",
         "Under covariate shift with known density ratios validity can be restored, and density ratios are easy to know in most applications."),
        ([6, 8], "Guarantees exist for some kinds of shift, such as label shift and temporal drift, though the evidence for label shift is thin.",
         "No guarantee exists for label shift or for temporal drift.",
         "Conformal methods are guaranteed to cover under every kind of distribution shift.",
         "Guarantees exist for some kinds of shift, such as label shift and temporal drift, and both have been validated in clinical trials."),
    ],
}
NAMED = ", as the SciGraph study also shows."
NUMBER = " This held in 37 of the 50 cases studied."


def claims_of(review: str) -> list[str]:
    path = ROOT / REVIEWS[review] / "claims.jsonl"
    return [json.loads(ln)["claim"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def premise_map(review: str, lines: list[int]) -> tuple[list[str], dict[str, str]]:
    claims = claims_of(review)
    ids = [f"C{n + 1}" for n in lines]
    return ids, {f"C{n + 1}": claims[n] for n in lines}


def build() -> list[dict]:
    items: list[dict] = []
    reviews = list(CONTROLS)
    for r_i, review in enumerate(reviews):
        split = "dev" if review in DEV else "test"
        same_split = [r for r in reviews if (r in DEV) == (review in DEV) and r != review]
        other = same_split[r_i % len(same_split)]
        for c_i, (lines, control, reversed_, overstated, new_fact) in enumerate(CONTROLS[review]):
            premises, claims = premise_map(review, lines)
            base = {"review": review, "split": split, "premises": premises, "claims": claims}

            def add(kind: str, text: str, label: str, layer: str, base: dict = base, stem: str = f"{review}-{c_i + 1}",
                    **over: object) -> None:  # fmt: skip
                items.append(base | {"id": f"{stem}-{kind}", "type": kind, "text": text, "label": label, "layer": layer} | over)

            add("control", control, "follows", "both")
            add("reversed", reversed_, "fault", "judge")
            add("overstated", overstated, "fault", "judge")
            add("new_fact", new_fact, "fault", "judge")
            o_lines = CONTROLS[other][c_i][0]
            o_premises, o_claims = premise_map(other, o_lines)
            add("irrelevant_premise", control, "fault", "judge", premises=o_premises, claims=o_claims, premise_review=other)
            if c_i == 0:
                add("named_source", control.rstrip(".") + NAMED, "fault", "rules")
                add("unsupported_number", control.rstrip(".") + NUMBER, "fault", "rules")
    return items


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    items = build()
    OUT.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items)
    (OUT / "items.jsonl").write_text(body, encoding="utf-8")
    test = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items if i["split"] == "test")
    counts = {s: {t: sum(1 for i in items if i["split"] == s and i["type"] == t) for t in dict.fromkeys(i["type"] for i in items)}
              for s in ("dev", "test")}  # fmt: skip
    meta = {"built_at": datetime.now(UTC).isoformat(timespec="seconds"), "dev_reviews": DEV,
            "test_reviews": [r for r in CONTROLS if r not in DEV], "counts": counts, "items_sha256": sha(body),
            "test_sha256": sha(test), "author": "Claude Code (controls and variants written by hand, 2026-10-11)"}  # fmt: skip
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
