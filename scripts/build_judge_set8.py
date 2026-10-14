# ruff: noqa: E501
"""Build the Increment 8 judge set (SPEC "The judge set for the new questions", JDG-P-04).

Each item is one of Increment 7's three new judge questions, asked exactly as the pipeline asks it, on real material from
the five papers made so far: Increment 6's P1-P3 (`data/paper_demo/`) and Increment 7's N1, N2 (`data/paper_rerun/`).
The question and the material come from the pipeline's own functions (`sentence_checks.within_quote`, `no_fact`,
`follows_strict`), so a judge sees here what it sees in a run.

- `claim.within_quote`: 24 kept claims per paper with their quotes (seeded sample);
- `sentence.no_fact`: up to 16 claim-free evidence sentences per paper (the old papers split as the audit splits them; the
  new papers' kept transitions);
- `paper.inference_follows` (clause-by-clause wording): every kept interpretation statement and synthesis sentence, with
  its premises.

Split by paper: dev is P1 and N1, test is P2, P3 and N2. No label is stored: the reference judge's modal answer is the label
(`scripts/measure_judge8.py`). Writes `data/judge8/items.jsonl` and `meta.json`; refuses to overwrite once the set is frozen.

    uv run python scripts/build_judge_set8.py
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.audit import sentences  # noqa: E402
from vera.literature import sentence_checks  # noqa: E402

OUT = ROOT / "data" / "judge8"
FREEZE = ROOT / "data" / "results" / "judge8_hash.json"
PAPERS = {
    "P1": ROOT / "data" / "paper_demo" / "how-much-useable-information-about-6x3n",
    "P2": ROOT / "data" / "paper_demo" / "discuss-the-evolution-of-prompting-guv8",
    "P3": ROOT / "data" / "paper_demo" / "rlm-vs-clm-3",
    "N1": ROOT / "data" / "paper_rerun" / "discuss-the-evolution-of-prompting-guv8",
    "N2": ROOT / "data" / "paper_rerun" / "rlm-vs-clm-2",
}
SPLIT = {"P1": "dev", "N1": "dev", "P2": "test", "P3": "test", "N2": "test"}
SEED = 20261014
CLAIMS_PER_PAPER = 24
SENTENCES_PER_PAPER = 16


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()] if path.exists() else []


def item(pid: str, kind: str, ref: str, question, material: str) -> dict:
    return {"id": f"{pid}-{kind}-{ref}", "paper": pid, "split": SPLIT[pid], "kind": kind, "ref": ref,
            "question": question.model_dump(mode="json"), "state": material}  # fmt: skip


def paper_items(pid: str, rng: random.Random) -> list[dict]:
    folder = PAPERS[pid]
    doc = json.loads((folder / "paper" / "paper.json").read_text(encoding="utf-8"))
    titles = {r["key"]: r["title"] for r in _jsonl(folder / "retrieved.jsonl") + _jsonl(folder / "paper" / "added_records.jsonl")}
    claims = {c["id"]: c for c in doc["claims"]}
    claim_text = {i: f"{c['claim']} (source: {titles.get(c['source_key'], c['source_key'])})" for i, c in claims.items()}
    out = []
    for c in rng.sample(doc["claims"], min(CLAIMS_PER_PAPER, len(doc["claims"]))):
        q, material = sentence_checks.within_quote(c["claim"], c["quote"], titles.get(c["source_key"]))
        out.append(item(pid, "within_quote", c["id"], q, material))
    if doc.get("sentences"):  # made with sentence statuses: the kept transitions are what no_fact is asked of
        loose = [(s["id"], s["section"], s["text"]) for s in doc["sentences"] if s["status"] == "pass" and s["kind"] == "transition"]
        synth = [s for s in doc["sentences"] if s["status"] == "pass" and s["kind"] == "synthesis"]
    else:  # made before: every claim-free evidence sentence, as the audit splits it
        evidence = [(s["heading"], s["text"]) for s in doc["sections"] if s["kind"] == "evidence"]
        entries = sentences.from_text(evidence, [c["id"] for c in doc["claims"]])
        loose = [(e["id"], e["section"], e["text"]) for e in entries if e["kind"] == "unrecorded"]
        synth = []
    for sid, heading, text in rng.sample(loose, min(SENTENCES_PER_PAPER, len(loose))):
        q, material = sentence_checks.no_fact(text, heading)
        out.append(item(pid, "no_fact", sid, q, material))
    statements = [(i["id"], i["text"], i["premises"]) for i in doc["inferences"] if i["status"] == "pass"]
    statements += [(s["id"], s["text"], s["premises"]) for s in synth]
    for ref, text, premises in statements:
        if not premises or any(p not in claim_text for p in premises):
            continue
        q, material = sentence_checks.follows_strict(text, premises, claim_text)
        out.append(item(pid, "inference", ref, q, material))
    return out


def main() -> None:
    if FREEZE.exists():
        sys.exit("the set is frozen (data/results/judge8_hash.json); it is not rebuilt")
    rng = random.Random(SEED)
    items = [it for pid in PAPERS for it in paper_items(pid, rng)]
    OUT.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items)
    (OUT / "items.jsonl").write_text(text, encoding="utf-8")
    counts = {s: {k: sum(1 for it in items if it["split"] == s and it["kind"] == k) for k in ("within_quote", "no_fact", "inference")}
              for s in ("dev", "test")}  # fmt: skip
    meta = {"built_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "seed": SEED, "split": SPLIT,
            "papers": {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in PAPERS.items()}, "counts": counts,
            "items_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}  # fmt: skip
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
