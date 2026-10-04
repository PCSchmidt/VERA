# ruff: noqa: E501
"""Build the novelty gold set (Increment 4, audit4_ready): pairs of an idea and a known prior method, labelled by construction.

Documents: the retrieval records of the six topics (title and abstract of published papers). Two kinds of pair, split dev and
test **by source paper**, the test hash fixed here before the audit runs on any test pair:

- `not_distinct`: a published paper's method written back as a proposal "as if it were new, in different words" by a model
  (Sonnet 5.5): the idea is that paper's method relabelled, paired with that paper;
- `distinct`: such a proposal paired with a paper from *another* topic (an unrelated method), and the loop's own real ideas
  (from the earlier runs) paired with the closest record, which are for Chris to label on a drawn sample
  (`data/novelty_gold/chris_sheet.csv`; his labels go to `chris_labels.csv`).

Writes data/novelty_gold/pairs.jsonl, split.json (counts, test hash, `frozen_audit_sha256` null until the freeze) and
chris_sheet.csv, and a never-overwritten ledger. Refuses to run if split.json exists.

Usage: uv run python scripts/build_novelty_gold.py [--n-papers 24] [--max-usd 0.5]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

from vera.audit.novelty import closest
from vera.backends.generator import OpenRouterGenerator
from vera.ledger import Ledger
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "novelty_gold"
SEED = 20261010
TOPICS = ["tree-explain", "credal-dro", "llm-judge-numbers", "conformal-shift", "tabular-trees-vs-nets", "research-agents-eval"]
SYSTEM = "You write research proposals. Reply with the proposal only."
PROMPT = (
    "Below are the title and abstract of a published paper. Write a proposal of about 50 words for a method, as if it were your own "
    "new idea, describing the SAME core method as the paper but in different words, with a different name and no mention of the "
    "paper, its authors or its datasets. Describe exactly what is computed. Reply with the proposal text only.\n\n"
    "Title: {title}\n\nAbstract: {abstract}"
)


def records(topic: str) -> list[dict]:
    rows = [json.loads(ln) for ln in (ROOT / "data" / "retrieval" / topic / "retrieved.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if len(r.get("abstract") or "") > 400 and r.get("title")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-papers", type=int, default=24)
    ap.add_argument("--max-usd", type=float, default=0.5)
    args = ap.parse_args()
    if (OUT / "split.json").exists():
        raise SystemExit("data/novelty_gold/split.json exists: the split is fixed once")
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    pool = {t: records(t) for t in TOPICS}
    chosen = []
    per_topic = args.n_papers // len(TOPICS)
    for t in TOPICS:
        for r in rng.sample(pool[t], min(per_topic, len(pool[t]))):
            chosen.append((t, r))
    n = 1
    while (ROOT / "data" / "ledger" / f"run_noveltygold-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"noveltygold-{n}", root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=args.max_usd, max_wall_seconds=3600)
    gen = OpenRouterGenerator("sonnet", "anthropic/claude-sonnet-5.5", ledger=ledger, budget=budget, max_tokens=600, reasoning={"effort": "minimal"})
    pairs = []
    for i, (topic, rec) in enumerate(chosen):
        idea = gen.generate(SYSTEM, PROMPT.format(title=rec["title"], abstract=rec["abstract"][:1800]), component="novelty.gold").strip()
        split = "test" if i % 2 == 1 else "dev"  # by source paper: a paper's two pairs share its split
        pairs.append({"id": f"nd-{i:02d}", "label": "not_distinct", "kind": "relabelled", "split": split, "topic": topic,
                      "idea": idea, "prior_title": rec["title"], "prior_text": rec["abstract"], "prior_id": rec.get("id")})  # fmt: skip
        other_topic = rng.choice([t for t in TOPICS if t != topic])
        other = rng.choice(pool[other_topic])
        pairs.append({"id": f"d-{i:02d}", "label": "distinct", "kind": "unrelated", "split": split, "topic": topic,
                      "idea": idea, "prior_title": other["title"], "prior_text": other["abstract"], "prior_id": other.get("id")})  # fmt: skip
    real = []
    for run in ("topic-a-loop-1", "topic-a-loop-2", "topic-a-loop-3", "protocol-live-1"):
        f = ROOT / "docs" / "results" / run / "ideas.json"
        if f.exists():
            for it in json.loads(f.read_text(encoding="utf-8"))["ideas"]:
                real.append({"name": it["name"], "description": it["description"], "run": run})
    seen, uniq = set(), []
    for it in real:
        if it["name"] not in seen:
            seen.add(it["name"])
            uniq.append(it)
    tree = records("tree-explain")
    for j, it in enumerate(uniq):
        prior = (closest(f"{it['name']}. {it['description']}", tree, k=1) or tree[:1])[0]
        pairs.append({"id": f"r-{j:02d}", "label": "unlabelled", "kind": "real_idea", "split": "chris", "topic": "tree-explain",
                      "idea": f"{it['name']}: {it['description']}", "prior_title": prior["title"], "prior_text": prior["abstract"],
                      "prior_id": prior.get("id")})  # fmt: skip
    (OUT / "pairs.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs), encoding="utf-8")
    drawn = random.Random(SEED + 1).sample([p for p in pairs if p["kind"] == "real_idea"], min(10, len(uniq)))
    with (OUT / "chris_sheet.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "idea", "prior work (title)", "prior work (abstract)", "your_label (distinct / not_distinct)"])
        for p in drawn:
            w.writerow([p["id"], p["idea"], p["prior_title"], p["prior_text"][:1500], ""])
    test = [p for p in pairs if p["split"] == "test"]
    split = {"seed": SEED, "rule": "by source paper: the relabelled pair and the unrelated pair of one paper share a split",
             "n_pairs": len(pairs), "n_dev": sum(p["split"] == "dev" for p in pairs), "n_test": len(test),
             "n_test_not_distinct": sum(p["label"] == "not_distinct" for p in test), "n_test_distinct": sum(p["label"] == "distinct" for p in test),
             "n_real_ideas_for_chris": len(uniq), "chris_sheet": [p["id"] for p in drawn],
             "test_sha256": hashlib.sha256(json.dumps([{k: p[k] for k in ("id", "label", "idea", "prior_title")} for p in test], sort_keys=True).encode()).hexdigest(),
             "frozen_audit_sha256": None, "generation_cost_usd": round(budget.spent_usd, 4)}  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in split.items() if k != "chris_sheet"}, indent=1))


if __name__ == "__main__":
    main()
