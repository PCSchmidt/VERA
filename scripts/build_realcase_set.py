# ruff: noqa: E501
"""Build the real-case set (Increment 7, SPEC "The real-case set"): real text from Increment 6's three papers.

Items are cited claims (with their quotes), claim-free evidence sentences (with the claims of their section) and kept
interpretation statements (with their premises), taken from `data/paper_demo/*/paper/`. None is written by the checks'
author. The split is by paper: dev is P1 (the external review read it closely), test is P2 and P3. Every item the
external review or the independent scorer named is in, with a seeded random sample of the rest; the test sheet is
shuffled and shows no mark of which were named, nor the papers' claim ids.

Writes `data/realcase/items.jsonl`, `data/realcase/meta.json` and `data/realcase/test_sheet.md` (for Chris to label;
`scripts/record_realcase_labels.py` reads it back). Run once; it refuses to overwrite a set that has labels.

    uv run python scripts/build_realcase_set.py
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "paper_demo"
OUT = ROOT / "data" / "realcase"
PAPERS = {"P1": "how-much-useable-information-about-6x3n", "P2": "discuss-the-evolution-of-prompting-guv8",
          "P3": "rlm-vs-clm-3"}  # fmt: skip
SPLIT = {"P1": "dev", "P2": "test", "P3": "test"}
SEED = 20261013
QUOTA = {"dev": {"claim": 20, "sentence": 15, "inference": 15}, "test": {"claim": 40, "sentence": 26, "inference": 24}}
LABELS = {
    "claim": {"W": "says no more than its quote", "M": "says more than its quote", "X": "needs context outside the quote"},
    "sentence": {"N": "states no fact (a transition)", "F": "follows from the claims listed",
                 "D": "does not follow from them, or contradicts them"},
    "inference": {"F": "follows from its premises", "O": "overreaches or does not follow"},
}  # fmt: skip
# Named by the independent scorer (data/results/rubric6_evaluator.json) or the external review
# (docs/results/incr6_external_review.md, P1 only). Sentences are named by their opening words.
NAMED = {
    "P1": {"claim": ["C14", "C28", "C41", "C53", "C46"], "inference": ["I1", "I3", "I8", "I11", "I15"],
           "sentence": ["The two studies therefore disagree", "GRL", "SpecRover"]},
    "P2": {"claim": ["C25", "C31", "C39", "C40", "C42", "C46"], "inference": ["I7", "I17"],
           "sentence": ["Another paper, by contrast"]},
    "P3": {"claim": ["C20", "C25", "C48"], "inference": ["I3"],
           "sentence": ["no passage covers recursive language models", "the compression line"]},
}  # fmt: skip
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_CITE = re.compile(r"\[R\d+\]")


def load(pid: str) -> tuple[dict, dict, dict]:
    run = DEMO / PAPERS[pid]
    paper = json.loads((run / "paper" / "paper.json").read_text(encoding="utf-8"))
    verify = json.loads((run / "paper" / "verify.json").read_text(encoding="utf-8"))
    titles = {r["key"]: r["title"] for r in map(json.loads, (run / "retrieved.jsonl").read_text("utf-8").splitlines()) if r}
    return paper, verify, titles


def pool(pid: str) -> dict[str, list[dict]]:
    paper, verify, titles = load(pid)
    claims = {c["id"]: c for c in paper["claims"]}
    out: dict[str, list[dict]] = {"claim": [], "sentence": [], "inference": []}
    for c in paper["claims"]:
        out["claim"].append({"id": f"{pid}-{c['id']}", "ref": c["id"], "type": "claim", "source": titles.get(c["source_key"], c["source_key"]),
                             "claim": c["claim"], "quote": c["quote"]})  # fmt: skip
    section_claims = {s["heading"]: [c["id"] for c in s["claims"]] for s in verify["sections"]}
    n = 0
    for s in (s for s in paper["sections"] if s["kind"] == "evidence"):
        for para in s["text"].split("\n\n"):
            for sent in _SENT.split(para.strip()):
                if sent and not _CITE.search(sent):
                    n += 1
                    ids = section_claims.get(s["heading"], [])
                    out["sentence"].append({"id": f"{pid}-S{n}", "ref": sent[:60], "type": "sentence", "section": s["heading"],
                                            "sentence": sent, "claims": {i: claims[i]["claim"] for i in ids if i in claims}})  # fmt: skip
    for i in (i for i in paper["inferences"] if i["status"] == "pass"):
        out["inference"].append({"id": f"{pid}-{i['id']}", "ref": i["id"], "type": "inference", "section": i["section"], "statement": i["text"],
                                 "premises": {p: claims[p]["claim"] for p in i["premises"] if p in claims}})  # fmt: skip
    return out


def is_named(pid: str, item: dict) -> bool:
    names = NAMED[pid][item["type"]]
    if item["type"] == "sentence":
        return any(n.lower() in item["sentence"].lower() for n in names)
    return item["ref"] in names


def select(rng: random.Random) -> list[dict]:
    chosen = []
    for split in ("dev", "test"):
        pids = [p for p in PAPERS if SPLIT[p] == split]
        for kind, quota in QUOTA[split].items():
            items = [dict(it, paper=p, split=split, named=is_named(p, it)) for p in pids for it in pool(p)[kind]]
            named = [it for it in items if it["named"]]
            rest = [it for it in items if not it["named"]]
            chosen += named + rng.sample(rest, max(0, min(len(rest), quota - len(named))))
    return chosen


def sheet(items: list[dict]) -> str:
    lines = ["# Real-case labelling sheet (Increment 7, test split)", "",
             "Label each item with one letter after `Label:`. Judge only from what is shown. Do not open",
             "`data/realcase/items.jsonl` (it records which items others flagged) until the set is frozen.", ""]  # fmt: skip
    for kind, opts in LABELS.items():
        lines.append(f"- **{kind}**: " + "; ".join(f"`{k}` {v}" for k, v in opts.items()))
    lines.append("")
    for it in items:
        lines += [f"## {it['sheet_id']} · {it['type']}", ""]
        if it["type"] == "claim":
            lines += [f"Source: {it['source']}", "", f"Claim: {it['claim']}", "", f"Quote: “{it['quote']}”"]
        elif it["type"] == "sentence":
            lines += [f"Section: {it['section']}", "", f"Sentence: {it['sentence']}", "", "Claims of its section:"]
            lines += [f"- {t}" for t in it["claims"].values()] or ["- (none)"]
        else:
            lines += [f"Section: {it['section']}", "", f"Statement: {it['statement']}", "", "Its premises:"]
            lines += [f"- {t}" for t in it["premises"].values()]
        lines += ["", f"Label ({'/'.join(LABELS[it['type']])}): ", ""]
    return "\n".join(lines)


def main() -> None:
    if any((OUT / f).exists() for f in ("labels_test.json", "labels_dev.json")):
        sys.exit("labels exist for this set; it is not rebuilt")
    rng = random.Random(SEED)
    items = select(rng)
    test = [it for it in items if it["split"] == "test"]
    rng.shuffle(test)
    for n, it in enumerate(test, start=1):
        it["sheet_id"] = f"T{n:02d}"
    dev = [it for it in items if it["split"] == "dev"]
    for n, it in enumerate(dev, start=1):
        it["sheet_id"] = f"D{n:02d}"
    OUT.mkdir(parents=True, exist_ok=True)
    rows = dev + test
    (OUT / "items.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    text = sheet(test)
    (OUT / "test_sheet.md").write_text(text, encoding="utf-8")
    counts = {s: {k: sum(1 for r in rows if r["split"] == s and r["type"] == k) for k in LABELS} for s in ("dev", "test")}
    named = {s: {k: sum(1 for r in rows if r["split"] == s and r["type"] == k and r["named"]) for k in LABELS} for s in ("dev", "test")}
    meta = {"built_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "seed": SEED, "papers": PAPERS, "split": SPLIT,
            "counts": counts, "named": named, "labels": LABELS,
            "sheet_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "sources": ["data/paper_demo/*/paper/paper.json", "data/results/rubric6_evaluator.json",
                        "docs/results/incr6_external_review.md"]}  # fmt: skip
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"counts": counts, "named": named}))


if __name__ == "__main__":
    main()
