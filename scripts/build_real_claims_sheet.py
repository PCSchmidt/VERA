"""Draw the real claims of the three topic runs for labelling: do the passages support them? (SPEC, judge re-test.)

The pool is each topic's claims as the synthesis stage passed them (for the two sections the final audit made repair,
`claims.pre_audit_repair.jsonl`: the version the claim-support judge had accepted). 30 are drawn by seed. For each, the
sheet shows what the judge is shown: the claim sentence and the passage that holds its quote, with the source's title.
A person labels `supported` yes or no (the passage states or clearly implies the claim as written, including direction,
numbers and qualifiers), writes data/claim_bench/real_claims_labels.csv, and `scripts/run_real_claims.py` compares the
judge path and the reference with the labels.

Writes data/claim_bench/real_claims_sheet.csv (id, topic, source, material, supported (yes/no)); the passages in it are
excerpts of other people's papers, so the sheet is git-ignored; the labels file is committed.

Usage: uv run python scripts/build_real_claims_sheet.py
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from vera.literature import questions, synthesis

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261003
N = 30


def jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> None:
    manifest = json.loads((ROOT / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    pool = []
    for tid in sorted(manifest):
        scope = json.loads((ROOT / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        run = ROOT / "runs" / scope["run_id"]
        before = run / "claims.pre_audit_repair.jsonl"
        claims = jsonl(before if before.exists() else run / "claims.jsonl")
        passages, records = jsonl(run / "passages.jsonl"), {r["key"]: r for r in jsonl(run / "retrieved.jsonl")}
        for n, c in enumerate(claims):
            passage = synthesis.matched_passage(c, passages)
            if passage:
                _, material = questions.claim_supported(c["claim"], passage, records[c["source_key"]]["title"])
                pool.append({"id": f"real-{tid}-{n:02d}", "topic": tid, "source": c["source_key"], "material": material,
                             "claim": c["claim"], "quote": c["quote"]})  # fmt: skip
    drawn = random.Random(SEED).sample(pool, min(N, len(pool)))
    drawn.sort(key=lambda r: r["id"])
    out = ROOT / "data" / "claim_bench" / "real_claims_sheet.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "topic", "source", "material (claim and passage)", "supported (yes/no)"])
        for r in drawn:
            w.writerow([r["id"], r["topic"], r["source"], r["material"], ""])
    (ROOT / "data" / "claim_bench" / "real_claims_pool.json").write_text(
        json.dumps({"seed": SEED, "pool": len(pool), "drawn": [r["id"] for r in drawn]}, indent=1), encoding="utf-8"
    )
    print(f"{len(drawn)} of {len(pool)} real claims drawn (seed {SEED}) -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
