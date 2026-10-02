"""Measure retrieval for the three topics: key-paper recall, how the misses happened, and a relevance-check sheet.

For each topic in data/topics/manifest.json, reads its run (the run id in data/topics/scope_<id>.json): the retrieval
log runs/<run>/retrieved.jsonl and the screen's result artifacts/relevance.json. Writes

  data/retrieval/<id>/retrieved.jsonl   a committed copy of the log (its records carry their retrieval dates)
  docs/results/retrieval_recall.md      recall per topic before and after the screen and in the top 30, and each miss
                                        classified: screened out wrongly / indexed but the queries missed it / not
                                        found in the sources by direct lookup (T5 reverse-if (1))
  data/retrieval/relevance_check.csv    15 candidates per topic drawn by seed, for the user's blind relevance verdicts
  data/retrieval/relevance_key.json     the model's verdicts for those candidates (not shown on the sheet)

The key papers were fixed and hashed before the first retrieval (check_topics.py); nothing here feeds back into
retrieval. The direct lookups use the keyless Crossref and arXiv endpoints, paced and cached.

Usage: uv run python scripts/measure_retrieval.py [--seed 20261005]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

import httpx

from vera.audit.bibliography import USER_AGENT
from vera.bench.retest import wilson
from vera.literature.retrieval import HttpCache, Retriever, recall

ROOT = Path(__file__).resolve().parents[1]
TOPICS = ROOT / "data" / "topics"
OUT = ROOT / "data" / "retrieval"
SAMPLE_PER_TOPIC = 15
TOP_N = 30
THRESHOLD = 0.70  # T5 reverse-if (1) starting value, not a target: key-paper recall after retrieval below this opens T5


def indexed(client: httpx.Client, key_paper: dict) -> bool:
    """Does a direct lookup by identifier find the key paper in a source? (Then the queries missed it.)"""
    kid = key_paper["id"]
    try:
        if kid.lower().startswith("arxiv:"):
            r = client.get("https://export.arxiv.org/api/query", params={"id_list": kid.split(":", 1)[1]})
            return "<entry>" in r.text and "<title>Error</title>" not in r.text
        doi = kid.split(":", 1)[1]
        return client.get(f"https://api.crossref.org/works/{doi}").status_code == 200
    except httpx.HTTPError:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=20261005)
    ap.add_argument("--snapshot", metavar="LABEL", help="copy each run's retrieval files to data/retrieval/<id>/<LABEL>/")
    ap.add_argument("--label", help="measure a snapshot (see --snapshot) instead of the run: recall only, no sheet")
    args = ap.parse_args()
    manifest = json.loads((TOPICS / "manifest.json").read_text(encoding="utf-8"))["topics"]
    if args.snapshot:
        for tid in manifest:
            scope = json.loads((TOPICS / f"scope_{tid}.json").read_text(encoding="utf-8"))
            run, dest = ROOT / "runs" / scope["run_id"], OUT / tid / args.snapshot
            dest.mkdir(parents=True, exist_ok=True)
            for name in ("retrieved.jsonl", "screen.jsonl", "artifacts/relevance.json", "artifacts/queries.json"):
                shutil.copy(run / name, dest / Path(name).name)
            print(f"snapshot {tid} -> {dest.relative_to(ROOT)}")
        return
    client = Retriever(cache=HttpCache(ROOT / "data" / "cache" / "http")).client
    client.headers["User-Agent"] = USER_AGENT.replace("citation existence checks", "key-paper lookup")
    lines = ["# Retrieval: recall of the key papers\n",
             "Recall is measured against the key-paper lists fixed and hashed before the first retrieval "
             "(`data/topics/manifest.json`). T5 reverse-if (1): a recall after retrieval below "
             f"{THRESHOLD:.0%} opens T5. Starting value, not a target.\n"]  # fmt: skip
    sheet, key = [], {}
    rng = random.Random(args.seed)
    for tid, entry in manifest.items():
        scope = json.loads((TOPICS / f"scope_{tid}.json").read_text(encoding="utf-8"))
        run = (OUT / tid / args.label) if args.label else ROOT / "runs" / scope["run_id"]
        art = run if args.label else run / "artifacts"
        records = [json.loads(ln) for ln in (run / "retrieved.jsonl").read_text(encoding="utf-8").splitlines() if ln]
        relevance = json.loads((art / "relevance.json").read_text(encoding="utf-8"))
        kept = set(relevance["kept"])
        key_papers = json.loads((TOPICS / entry["file"]).read_text(encoding="utf-8"))["key_papers"]
        result = recall(key_papers, records, kept, TOP_N)
        if not args.label:
            (OUT / tid).mkdir(parents=True, exist_ok=True)
            shutil.copy(run / "retrieved.jsonl", OUT / tid / "retrieved.jsonl")
        lines += [f"\n## {tid}\n",
                  f"Run `{scope['run_id']}`: {len(records)} candidates retrieved, {len(kept)} kept by the relevance "
                  f"screen, {len(relevance['unsure'])} unsure.\n",
                  f"| | Key papers found | Share |\n|---|---|---|\n"
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
            elif not row["kept"]:
                why = "screened out"
            else:
                why = ""
            found, kept_ = ("yes" if row["found"] else "no"), ("yes" if row["kept"] else "no")
            lines.append(f"| {row['title'][:70]} | {found} | {kept_} | {row['position'] or ''} | {why} |\n")
        lines.append(f"\nVerdict on the starting threshold: recall after retrieval {result['found']:.0%} "
                     f"({'at or above' if result['found'] >= THRESHOLD else 'BELOW'} {THRESHOLD:.0%}).\n")  # fmt: skip
        if args.label:
            continue
        verdicts = {}
        for ln in (run / "screen.jsonl").read_text(encoding="utf-8").splitlines():
            v = json.loads(ln)
            verdicts[v["key"]] = {"answer": v["verdict"]["answer"], "confident": v["confident"]}
        for rec in rng.sample(records, min(SAMPLE_PER_TOPIC, len(records))):
            sheet.append({"topic": tid, "key": rec["key"], "title": rec["title"], "year": rec.get("year", ""),
                          "abstract": (rec.get("abstract") or "")[:1200], "your_verdict": ""})  # fmt: skip
            key[f"{tid}:{rec['key']}"] = verdicts.get(rec["key"])
    name = f"retrieval_recall_{args.label}.md" if args.label else "retrieval_recall.md"
    (ROOT / "docs" / "results" / name).write_text("".join(lines), encoding="utf-8")
    if args.label:
        print(f"wrote docs/results/{name}")
        return
    with (OUT / "relevance_check.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["topic", "key", "title", "year", "abstract", "your_verdict"])
        w.writeheader()
        w.writerows(sheet)
    (OUT / "relevance_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print("wrote docs/results/retrieval_recall.md, data/retrieval/relevance_check.csv (fill your_verdict: yes/no)")
    _ = wilson  # the agreement with its interval is computed by check_retrieval.py once the sheet is filled


if __name__ == "__main__":
    main()
