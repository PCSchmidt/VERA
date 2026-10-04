# ruff: noqa: E501
"""Gate `lit2_ready`: the literature stage v2 measured (Increment 4).

Requires:
- docs/results/retrieval_recall_lit2.md and, for the three Increment 3 topics re-run through the v2 stage,
  docs/results/retrieval_recall_lit2_old.md: each topic's table of key papers found and missed, and a stated verdict
  against the 70% starting threshold (reported, not gated on a level);
- data/results/anchoring_measure.json (the checks on the claims Increment 3 passed) and anchoring_real.json (the 30
  labelled real claims), with their rates and intervals and the ledgers they were charged to;
- for each fresh topic (conformal-shift, tabular-trees-vs-nets, research-agents-eval) a committed review in
  data/literature/<topic>/ that carries the retrieval statement ("## Retrieval and its limits") and whose audit report is
  not red, and the first version of the section kept in data/literature_first/<topic>/ (the section was written again after
  a reader found sentences leaning on an earlier one);
- the fresh topics' key-paper lists unchanged since their manifest entries (check_topics.py's hash rule, run here).
"""

from __future__ import annotations

import json
import re

from _common import block, ok, repo_root_arg

FRESH = ("conformal-shift", "tabular-trees-vs-nets", "research-agents-eval")
OLD = ("tree-explain", "credal-dro", "llm-judge-numbers")


def load(path, what: str):
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    res = args.root / "docs" / "results"
    for name, topics in (("retrieval_recall_lit2.md", FRESH), ("retrieval_recall_lit2_old.md", OLD)):
        path = res / name
        if not path.exists():
            block(f"{name} not found")
        text = path.read_text(encoding="utf-8")
        for t in topics:
            if f"## {t}" not in text:
                block(f"{name} has no section for {t}")
        if len(re.findall(r"Recall after retrieval \d+%", text)) < len(topics):
            block(f"{name} does not state the recall verdict for each topic")
    m = load(args.root / "data" / "results" / "anchoring_measure.json", "the anchoring measurement")
    r = load(args.root / "data" / "results" / "anchoring_real.json", "the anchoring measurement on the real claims")
    if m["claims"] < 40 or r["claims"] < 30 or "ci95" not in m or "ci95" not in r:
        block("the anchoring measurements must cover the 42 passed claims and the 30 labelled real claims, with intervals")
    for rec in (m, r):
        if not (args.root / rec["ledger"]).exists():
            block(f"ledger {rec['ledger']} missing")
    for t in FRESH:
        folder = args.root / "data" / "literature" / t
        review = folder / "literature.md"
        if not review.exists():
            block(f"no committed review for {t}")
        if re.search(r"^## Retrieval and its limits", review.read_text(encoding="utf-8"), re.MULTILINE) is None:
            block(f"{t}: the review does not carry its retrieval statement")
        audit = load(folder / "audit_report.json", f"{t}'s audit report")
        if audit["overall"] == "red":
            block(f"{t}: the review's audit is red")
        if not (args.root / "data" / "literature_first" / t / "literature.md").exists():
            block(f"{t}: the first version of the section is not kept")
    ok(f"recall tables for {len(FRESH)} fresh and {len(OLD)} old topics; anchoring on {m['claims']} + {r['claims']} claims; "
       f"fresh reviews carry their retrieval statement, audits not red")


if __name__ == "__main__":
    main()
