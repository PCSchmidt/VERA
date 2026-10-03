"""Measure the claim-anchoring checks on the claims the Increment 3 synthesis stage passed (Increment 4, lit2_ready).

For each of the three topics, the claims as the synthesis stage passed them (`claims.pre_audit_repair.jsonl` where the
final audit made a repair, else `claims.jsonl`; 42 in all) go through the two checks of `vera.literature.anchoring`:
the deterministic editorial-connective check and the judge question `lit.quote_covers_claim` (shown the quote only),
asked of the cheap path. Reports how many fail each, by topic, with a Wilson interval and the failing sentences. The
SPEC's reverse-if: a failure rate above 10% on these claims means the check is too loose or the synthesis prompt needs
the one-assertion rule (which this increment adds, so the rate on newly written sections is measured on the fresh
topic).

Writes data/results/anchoring_measure.json and a never-overwritten ledger data/ledger/run_anchormeasure-<n>.jsonl.



Usage: uv run python scripts/measure_anchoring.py
"""

from __future__ import annotations

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
    n = 1
    while (ROOT / "data" / "ledger" / f"run_anchormeasure-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"anchormeasure-{n}", root=ROOT / "data" / "ledger")
    budget = Budget(max_usd=0.2, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget, component="p2.anchoring")
    topics = json.loads((ROOT / "data" / "topics" / "manifest.json").read_text(encoding="utf-8"))["topics"]
    rows = []
    for tid in sorted(topics):
        folder = ROOT / "data" / "literature" / tid
        scope = json.loads((ROOT / "data" / "topics" / f"scope_{tid}.json").read_text(encoding="utf-8"))
        records = jsonl(ROOT / "runs" / scope["run_id"] / "retrieved.jsonl")
        titles = {r["key"]: r["title"] for r in records}
        before = folder / "claims.pre_audit_repair.jsonl"
        for c in jsonl(before if before.exists() else folder / "claims.jsonl"):
            marker = anchoring.marker_problem(c["claim"], c["quote"])
            q, material = anchoring.quote_covers_claim(c["claim"], c["quote"], titles[c["source_key"]])
            (v,) = judge.ask(material, [q])
            confident = v.confidence_source != "none" and v.confidence >= MIN_CONFIDENCE
            rows.append({"topic": tid, "source_key": c["source_key"], "claim": c["claim"], "marker": marker,
                         "judge_covers": v.answer is True and confident, "judge_unsure": not confident})  # fmt: skip
    failed = [r for r in rows if r["marker"] or not r["judge_covers"]]
    lo, hi = wilson(len(failed), len(rows))
    out = {
        "claims": len(rows), "failed_either": len(failed), "rate": round(len(failed) / len(rows), 4),
        "ci95": [round(lo, 4), round(hi, 4)], "marker_failures": sum(bool(r["marker"]) for r in rows),
        "judge_failures": sum(not r["judge_covers"] for r in rows),
        "by_topic": {t: {"claims": sum(r["topic"] == t for r in rows),
                         "failed": sum(r["topic"] == t and bool(r["marker"] or not r["judge_covers"]) for r in rows)}
                     for t in sorted(topics)},  # fmt: skip
        "failing": [{k: r[k] for k in ("topic", "source_key", "claim", "marker", "judge_unsure")} for r in failed],
        "spend_usd": round(budget.spent_usd, 5), "ledger": ledger.path.relative_to(ROOT).as_posix(),
        "reverse_if": "a failure rate above 10% means the check is too loose or the synthesis prompt needs the rule",
    }  # fmt: skip
    (ROOT / "data" / "results" / "anchoring_measure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(
        {
            k: out[k]
            for k in ("claims", "failed_either", "rate", "ci95", "marker_failures", "judge_failures", "by_topic")
        }
    )
    for f in out["failing"]:
        print(f"  {f['topic']} {f['source_key']} marker={f['marker']} unsure={f['judge_unsure']}: {f['claim'][:110]}")


if __name__ == "__main__":
    main()
