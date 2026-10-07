# ruff: noqa: E501
"""Second keyed source (Increment 5, T5 reverse-if (5)): what Semantic Scholar adds to the key-paper recall.

For each of the six topics, takes the queries the Increment 4 retrieval used (the run's `queries.json`) and the candidates
it retrieved (`retrieved.jsonl`), runs the same queries through Semantic Scholar with the user's own key
(`SEMANTIC_SCHOLAR_API_KEY`, read from the environment or the git-ignored .env, sent as a header, never stored), and
reports key-paper recall before the screen with and without the new records. The key lists are the topics' hashed
lists, unchanged. The screen is not re-run (that costs model calls): "kept" figures are from the old run and the new
records are reported as candidates only.

Usage: uv run python scripts/measure_retrieval5.py
Writes docs/results/retrieval_recall_s2.md and data/retrieval_s2/<topic>/s2_hits.jsonl.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from measure_retrieval import ROOT, TOPICS  # noqa: E402

from vera.literature.retrieval import HttpCache, Retriever, merge_records, recall  # noqa: E402

RUNS = {"research-agents-eval": "topic4-agents-1", "conformal-shift": "topic4-conformal-2",
        "tabular-trees-vs-nets": "topic4-tabular-3", "tree-explain": "lit2-tree-explain",
        "credal-dro": "lit2-credal-dro-b", "llm-judge-numbers": "lit2-llm-judge-numbers-b"}  # fmt: skip
OUT = ROOT / "data" / "retrieval_s2"


def main() -> None:
    manifest = json.loads((TOPICS / "manifest.json").read_text(encoding="utf-8"))["topics"]
    retriever = Retriever(cache=HttpCache(ROOT / "data" / "cache" / "http"), sources=["semanticscholar"])
    lines = ["# Second keyed source: Semantic Scholar's addition to key-paper recall (Increment 5)\n",
             "Same queries and same hashed key lists as the Increment 4 retrieval; Semantic Scholar searched with the user's own "
             "key. Recall is before the screen; the screen was not re-run, so no kept-by-screen figure is given for the new records.\n",
             "\n| Topic | Key papers | Found before (Increment 4) | Found with Semantic Scholar | Added by it | Records it returned |\n|---|---|---|---|---|---|\n"]  # fmt: skip
    tot = [0, 0, 0]
    detail = []
    for tid, run_id in RUNS.items():
        run = ROOT / "runs" / run_id
        old = [json.loads(ln) for ln in (run / "retrieved.jsonl").read_text(encoding="utf-8").splitlines() if ln]
        queries = json.loads((run / "artifacts" / "queries.json").read_text(encoding="utf-8"))["queries"]
        key_papers = json.loads((TOPICS / manifest[tid]["file"]).read_text(encoding="utf-8"))["key_papers"]
        hits = []
        for q in queries:
            text = q["query"] if isinstance(q, dict) else q
            hits += retriever(text)
        (OUT / tid).mkdir(parents=True, exist_ok=True)
        (OUT / tid / "s2_hits.jsonl").write_text("\n".join(json.dumps(h) for h in hits) + "\n", encoding="utf-8")
        new_only = merge_records(hits)
        before = recall(key_papers, old, set(), 30)
        after = recall(key_papers, old + new_only, set(), 30)
        nb, na = sum(r["found"] for r in before["rows"]), sum(r["found"] for r in after["rows"])
        added = [r["title"] for r, b in zip(after["rows"], before["rows"], strict=True) if r["found"] and not b["found"]]
        tot = [tot[0] + len(key_papers), tot[1] + nb, tot[2] + na]
        lines.append(f"| {tid} | {len(key_papers)} | {nb} | {na} | {na - nb} | {len(new_only)} |\n")
        detail.append((tid, added, [k["title"] for k, r in zip(key_papers, after["rows"], strict=True) if not r["found"]]))
    lines.append(f"| **Pooled** | {tot[0]} | {tot[1]} ({tot[1] / tot[0]:.0%}) | {tot[2]} ({tot[2] / tot[0]:.0%}) | {tot[2] - tot[1]} | |\n")
    lines.append("\n## Key papers it added, and those still missed\n")
    for tid, added, missed in detail:
        lines.append(f"\n**{tid}** added: {'; '.join(a[:70] for a in added) or 'none'}. Still missed: {len(missed)}.\n")
    (ROOT / "docs" / "results" / "retrieval_recall_s2.md").write_text("".join(lines), encoding="utf-8")
    print("".join(lines))


if __name__ == "__main__":
    main()
