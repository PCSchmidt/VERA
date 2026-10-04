"""Key-paper recall for the fresh Increment 4 topics (lit2_ready), with retrieval v2 (12 queries, seven angles).

Reads each listed run (topic id : run id) and the topic's key papers (fixed and hashed before any retrieval:
data/topics/manifest.json). Reports key papers found before the screen, kept by it and in the top 30, each miss
classified as in scripts/measure_retrieval.py, the retrieval stats the review carries, and the number of claims.
Copies each run's retrieval log and scope into data/ for the record. Writes docs/results/retrieval_recall_v2.md.

Usage: uv run python scripts/measure_retrieval4.py <topic>:<run> [<topic>:<run> ...]
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from measure_retrieval import OUT, ROOT, THRESHOLD, TOP_N, TOPICS, indexed  # noqa: E402

from vera.audit.bibliography import USER_AGENT  # noqa: E402
from vera.literature.retrieval import HttpCache, Retriever, recall  # noqa: E402


def main() -> None:
    pairs = [a.split(":", 1) for a in sys.argv[1:]]
    manifest = json.loads((TOPICS / "manifest.json").read_text(encoding="utf-8"))["topics"]
    client = Retriever(cache=HttpCache(ROOT / "data" / "cache" / "http")).client
    client.headers["User-Agent"] = USER_AGENT.replace("citation existence checks", "key-paper lookup")
    lines = ["# Retrieval v2: recall of the key papers on the fresh topics\n",
             f"Key papers fixed and hashed before any retrieval for the topic. Starting threshold {THRESHOLD:.0%} "
             "(T5 reverse-if (1)), not a target. Retrieval v2: 12 queries, seven angles, up to 120 records.\n"]  # fmt: skip
    for tid, run_id in pairs:
        run = ROOT / "runs" / run_id
        records = [json.loads(ln) for ln in (run / "retrieved.jsonl").read_text(encoding="utf-8").splitlines() if ln]
        relevance = json.loads((run / "artifacts" / "relevance.json").read_text(encoding="utf-8"))
        kept = set(relevance["kept"])
        key_papers = json.loads((TOPICS / manifest[tid]["file"]).read_text(encoding="utf-8"))["key_papers"]
        result = recall(key_papers, records, kept, TOP_N)
        lit = json.loads((run / "artifacts" / "literature.json").read_text(encoding="utf-8"))
        queries = json.loads((run / "artifacts" / "queries.json").read_text(encoding="utf-8"))["queries"]
        (OUT / tid).mkdir(parents=True, exist_ok=True)
        shutil.copy(run / "retrieved.jsonl", OUT / tid / "retrieved.jsonl")
        shutil.copy(run / "scope.json", TOPICS / f"scope_{tid}.json")
        lines += [f"\n## {tid}\n",
                  f"Run `{run_id}`: {len(queries)} queries, {len(records)} candidates, {len(kept)} kept by the screen, "
                  f"{lit['stats']['drafted']} claims drafted, {lit['n_claims_kept']} kept "
                  f"(first-draft failures {lit['stats']['failed_first']}).\n",
                  "\n| | Key papers found | Share |\n|---|---|---|\n"
                  f"| Retrieved (before the screen) | {sum(r['found'] for r in result['rows'])} of "
                  f"{result['n_key_papers']} | {result['found']:.0%} |\n"
                  f"| Kept by the screen | {sum(r['kept'] for r in result['rows'])} | {result['kept']:.0%} |\n"
                  f"| In the top {TOP_N} by rank | {sum(r['in_top'] for r in result['rows'])} "
                  f"| {result['in_top']:.0%} |\n",
                  "\n| Key paper | Found | Kept | Position | Miss, classified |\n|---|---|---|---|---|\n"]  # fmt: skip
        for row in result["rows"]:
            if not row["found"]:
                kp = next(k for k in key_papers if k["title"] == row["title"])
                why = "indexed, queries missed it" if indexed(client, kp) else "not found in the sources by lookup"
            else:
                why = "" if row["kept"] else "screened out"
            lines.append(f"| {row['title'][:70]} | {'yes' if row['found'] else 'no'} | "
                         f"{'yes' if row['kept'] else 'no'} | {row['position'] or ''} | {why} |\n")  # fmt: skip
        lines.append(f"\nRecall after retrieval {result['found']:.0%} "
                     f"({'at or above' if result['found'] >= THRESHOLD else 'BELOW'} {THRESHOLD:.0%}).\n")  # fmt: skip
    (ROOT / "docs" / "results" / "retrieval_recall_v2.md").write_text("".join(lines), encoding="utf-8")
    print("".join(lines))


if __name__ == "__main__":
    main()
