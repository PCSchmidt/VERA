"""Gate `retrieval_ready`: the three topics were retrieved live, measured against their key papers, and the relevance
screen was checked by the user on a drawn sample.

Requires, for every topic in data/topics/manifest.json:
- data/retrieval/<id>/retrieved.jsonl: the retrieval log, each record with a key, title, id, source, the query and rank
  that found it and its retrieval date;
- the run's ledger (the run id is in data/topics/scope_<id>.json) within the per-topic cap ($2 by default);
and overall:
- docs/results/retrieval_recall.md naming every topic (the key-paper recall table, T5 reverse-if (1));
- data/retrieval/relevance_check.csv with 15 candidates per topic, each with the user's verdict (yes or no), and
  data/retrieval/relevance_key.json holding the model's verdicts for them. The check reports the agreement between the
  screen and the user (confident verdicts only) with a 95% Wilson interval; a low agreement is reported, not blocked:
  it is evidence for the review, not a gate condition.
"""

from __future__ import annotations

import csv
import json
import math

from _common import block, ok, repo_root_arg

SAMPLE_PER_TOPIC = 15
RECORD_FIELDS = ("key", "title", "id", "source", "query", "rank", "retrieved")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def main() -> None:
    parser = repo_root_arg(__doc__)
    parser.add_argument("--cap-usd", type=float, default=2.0)
    args = parser.parse_args()
    root = args.root
    topics = json.loads((root / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    for tid in topics:
        log = root / "data" / "retrieval" / tid / "retrieved.jsonl"
        if not log.exists():
            block(f"{tid}: data/retrieval/{tid}/retrieved.jsonl not found (scripts/measure_retrieval.py)")
        records = [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not records:
            block(f"{tid}: the retrieval log is empty")
        bad = [r.get("key") for r in records if any(r.get(f) in (None, "") for f in RECORD_FIELDS)]
        if bad:
            block(f"{tid}: retrieval records missing a field of {RECORD_FIELDS}: {bad[:3]}")
        scope = json.loads((root / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        ledger = root / "data" / "ledger" / f"run_{scope['run_id']}.jsonl"
        if not ledger.exists():
            block(f"{tid}: ledger of run {scope['run_id']!r} not found")
        spent = sum(json.loads(ln)["cost_usd"] for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip())
        if spent > args.cap_usd:
            block(f"{tid}: ${spent:.4f} spent, over the ${args.cap_usd} per-topic cap")
    recall = root / "docs" / "results" / "retrieval_recall.md"
    if not recall.exists():
        block("docs/results/retrieval_recall.md not found (scripts/measure_retrieval.py)")
    text = recall.read_text(encoding="utf-8")
    missing = [t for t in topics if f"## {t}" not in text]
    if missing:
        block(f"the recall table lacks topics {missing}")
    sheet = root / "data" / "retrieval" / "relevance_check.csv"
    key_file = root / "data" / "retrieval" / "relevance_key.json"
    if not sheet.exists() or not key_file.exists():
        block("data/retrieval/relevance_check.csv or relevance_key.json not found")
    rows = list(csv.DictReader(sheet.open(encoding="utf-8", newline="")))
    key = json.loads(key_file.read_text(encoding="utf-8"))
    agree = n = unsure = 0
    for tid in topics:
        mine = [r for r in rows if r["topic"] == tid]
        if len(mine) != SAMPLE_PER_TOPIC:
            block(f"{tid}: {len(mine)} rows in the relevance sheet, need {SAMPLE_PER_TOPIC}")
        for r in mine:
            verdict = r["your_verdict"].strip().lower()
            if verdict not in ("yes", "no"):
                block(f"{tid} {r['key']}: your_verdict must be yes or no (it is {verdict!r})")
            model = key.get(f"{tid}:{r['key']}")
            if not model or not model["confident"]:
                unsure += 1
                continue
            n += 1
            agree += (model["answer"] is True) == (verdict == "yes")
    lo, hi = wilson(agree, n)
    ok(f"{len(topics)} topics retrieved and measured; relevance screen agrees with you on {agree} of {n} confident "
       f"verdicts ({agree / max(n, 1):.0%}, 95% CI {lo:.0%}-{hi:.0%}), {unsure} unsure ones set aside")  # fmt: skip


if __name__ == "__main__":
    main()
