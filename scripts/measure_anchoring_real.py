"""The claim-anchoring checks on the 30 labelled real claims (Increment 4, lit2_ready).

The 30 claims are the ones data/claim_bench/real_claims_labels.csv labels for support (ids `real-<topic>-<n>`, n the
claim's index in the topic's claims as the synthesis stage passed them). Each goes through the editorial-connective
check and `lit.quote_covers_claim` (the cheap path, shown the quote and the source's title), and the result is reported
against the support label: anchoring is a different property from support, so the table shows both. Does not re-draw
the sample (the draw is fixed by its seed over the three Increment 3 topics).

Writes data/results/anchoring_real.json and a never-overwritten ledger data/ledger/run_anchorreal-<n>.jsonl.

Usage: uv run python scripts/measure_anchoring_real.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from vera.bench.retest import wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.literature import anchoring
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
MIN_CONFIDENCE = 0.7


def jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def main() -> None:
    labels = list(csv.DictReader((ROOT / "data" / "claim_bench" / "real_claims_labels.csv").open(encoding="utf-8")))
    n = 1
    while (ROOT / "data" / "ledger" / f"run_anchorreal-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"anchorreal-{n}", root=ROOT / "data" / "ledger")
    judge = cheap_path(ledger=ledger, budget=Budget(max_usd=0.2, max_wall_seconds=3600), component="p2.anchoring")
    rows = []
    for lab in labels:
        topic, idx = lab["id"].removeprefix("real-").rsplit("-", 1)
        scope = json.loads((ROOT / "data" / "topics" / f"scope_{topic}.json").read_text(encoding="utf-8"))
        run = ROOT / "runs" / scope["run_id"]
        titles = {r["key"]: r["title"] for r in jsonl(run / "retrieved.jsonl")}
        before = run / "claims.pre_audit_repair.jsonl"
        claim = jsonl(before if before.exists() else run / "claims.jsonl")[int(idx)]
        assert claim["source_key"] == lab["source"], lab["id"]
        marker = anchoring.marker_problem(claim["claim"], claim["quote"])
        dangling = anchoring.dangling_reference(claim["claim"])
        q, material = anchoring.quote_covers_claim(claim["claim"], claim["quote"], titles[claim["source_key"]])
        (v,) = judge.ask(material, [q])
        covers = v.answer is True and v.confidence_source != "none" and v.confidence >= MIN_CONFIDENCE
        rows.append({"id": lab["id"], "supported_label": lab["supported"], "marker": marker, "dangling": dangling,
                     "quote_covers": covers})  # fmt: skip
    failed = [r for r in rows if r["marker"] or r["dangling"] or not r["quote_covers"]]
    lo, hi = wilson(len(failed), len(rows))
    sup = [r for r in rows if r["supported_label"] == "yes"]
    sup_failed = [r for r in sup if r["marker"] or r["dangling"] or not r["quote_covers"]]
    unsup_failed = [r for r in rows if r["supported_label"] != "yes" and r in failed]
    out = {"claims": len(rows), "failed_anchoring": len(failed), "rate": round(len(failed) / len(rows), 4),
           "ci95": [round(lo, 4), round(hi, 4)], "marker": sum(bool(r["marker"]) for r in rows),
           "dangling_reference": sum(bool(r["dangling"]) for r in rows),
           "quote_does_not_cover": sum(not r["quote_covers"] for r in rows),
           "labelled_supported": len(sup), "labelled_supported_failing_anchoring": len(sup_failed),
           "labelled_unsupported": len(rows) - len(sup),
           "labelled_unsupported_failing_anchoring": len(unsup_failed),
           "rows": rows, "ledger": ledger.path.relative_to(ROOT).as_posix(),
           "labels_by": "an AI helper blind to every verdict (see real_claims_labels.csv), not Chris"}  # fmt: skip
    (ROOT / "data" / "results" / "anchoring_real.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print({k: v for k, v in out.items() if k != "rows"})


if __name__ == "__main__":
    main()
