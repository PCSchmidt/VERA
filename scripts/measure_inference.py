# ruff: noqa: E501
"""Measure the inference check (AUD-F-11, Increment 6) on its seeded set (`data/seeded_inference/`, built by
`scripts/build_inference_set.py`).

    dev     run the check on the dev split (may be repeated; used only to read the question's behaviour)
    freeze  hash the test split and the check's source into data/results/inference_hash_incr6.json (before `test`)
    test    the one run on the test split; refuses if the freeze is missing, stale, or a test result already exists

Each item goes through `vera.audit.inference.check` exactly as the paper stage runs it: the deterministic rules, then the
cheap judge path (Jev escalating to GLM when a Jev key is set, else GLM), with an unsure verdict counted as a failure.
Reported: detection per fault type and for the judge layer pooled, the false-positive rate on controls, each with a Wilson
95% interval, and the spend from the run's own ledger. The rules layer (named source, unsupported number) is reported
apart: it is caught by construction and says nothing about the judge. Spend cap for the whole measurement: $1 (SPEC).

Usage: uv run python scripts/measure_inference.py dev|freeze|test
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from vera.audit import inference
from vera.bench.retest import wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / "data" / "seeded_inference"
FREEZE = ROOT / "data" / "results" / "inference_hash_incr6.json"
RESULTS = ROOT / "data" / "results"
CHECK_FILES = ["vera/audit/inference.py", "vera/literature/synthesis.py", "vera/literature/anchoring.py"]
CAP_USD = 1.0
MIN_CONFIDENCE = 0.7  # as in the paper stage (LitDeps.min_confidence) and the paper audit


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def items(split: str) -> list[dict]:
    rows = [json.loads(ln) for ln in (SET / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["split"] == split]


def test_hash() -> str:
    test = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items("test"))
    return hashlib.sha256(test.encode("utf-8")).hexdigest()


def check_hashes() -> dict[str, str]:
    return {f: sha_bytes((ROOT / f).read_bytes()) for f in CHECK_FILES}


def spent(ledger: Ledger) -> float:
    return sum(r.cost_usd for r in ledger.records())


def run(split: str) -> dict:
    ledger_path = ROOT / "data" / "ledger" / f"inference_incr6_{split}.jsonl"
    if split == "test" and ledger_path.exists():
        sys.exit("a test run already exists: the test split is measured once")
    earlier = sum(spent(Ledger(p)) for p in (ROOT / "data" / "ledger").glob("inference_incr6_*.jsonl"))
    ledger = Ledger(ledger_path, run_id=f"inference_incr6_{split}")
    budget = Budget(max_usd=CAP_USD - earlier, max_wall_seconds=3600)
    judge = cheap_path(ledger=ledger, budget=budget, component="p2.inference_incr6")

    def ask(question, material):
        (v,) = judge.ask(material, [question])
        return v, v.confidence_source != "none" and v.confidence >= MIN_CONFIDENCE

    rows = []
    for it in items(split):
        reason, verdicts = inference.check(it["text"], it["premises"], it["claims"], ask)
        v = verdicts[0] if verdicts else None
        rows.append({"id": it["id"], "type": it["type"], "label": it["label"], "layer": it["layer"], "caught": reason is not None,
                     "reason": reason, "judge_answer": v.answer if v else None, "confidence": v.confidence if v else None,
                     "backend": v.backend if v else None})  # fmt: skip
    return {"rows": rows, "spend_usd": spent(ledger), "ledger": ledger_path.relative_to(ROOT).as_posix()}


def rate(rows: list[dict]) -> dict:
    k, n = sum(r["caught"] for r in rows), len(rows)
    lo, hi = wilson(k, n) if n else (0.0, 0.0)
    return {"k": k, "n": n, "rate": k / n if n else None, "ci95": [round(lo, 3), round(hi, 3)]}


def summarise(rows: list[dict]) -> dict:
    types = list(dict.fromkeys(r["type"] for r in rows))
    judge_faults = [r for r in rows if r["label"] == "fault" and r["layer"] == "judge"]
    return {
        "per_type": {t: rate([r for r in rows if r["type"] == t]) for t in types},
        "false_positive_on_controls": rate([r for r in rows if r["type"] == "control"]),
        "judge_layer_detection": rate(judge_faults),
        "judge_layer_caught_by_rules": sum(1 for r in judge_faults if r["caught"] and r["judge_answer"] is None),
        "rules_layer_detection": rate([r for r in rows if r["layer"] == "rules"]),
        "unsure": sum(1 for r in rows if r["reason"] == "judge_unsure"),
    }


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "freeze":
        if FREEZE.exists():
            sys.exit("already frozen: a new freeze needs a new test set")
        meta = json.loads((SET / "meta.json").read_text(encoding="utf-8"))
        if meta["test_sha256"] != test_hash():
            sys.exit("items.jsonl's test split differs from meta.json: rebuild the set first")
        FREEZE.write_text(json.dumps({"frozen_at": datetime.now(UTC).isoformat(timespec="seconds"), "test_sha256": test_hash(),
                                      "check_sha256": check_hashes()}, indent=1), encoding="utf-8")  # fmt: skip
        print(f"frozen: test {test_hash()[:12]}, check files {len(CHECK_FILES)}")
        return
    if cmd not in ("dev", "test"):
        sys.exit(__doc__)
    if cmd == "test":
        frozen = json.loads(FREEZE.read_text(encoding="utf-8")) if FREEZE.exists() else None
        if frozen is None or frozen["test_sha256"] != test_hash() or frozen["check_sha256"] != check_hashes():
            sys.exit("the freeze is missing or stale (the test split or the check changed after it): not running")
    out = run(cmd)
    result = {"split": cmd, "run_at": datetime.now(UTC).isoformat(timespec="seconds"), "summary": summarise(out["rows"]),
              "spend_usd": out["spend_usd"], "ledger": out["ledger"], "test_sha256": test_hash(),
              "check_sha256": check_hashes(), "rows": out["rows"]}  # fmt: skip
    (RESULTS / f"inference_incr6_{cmd}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["summary"], indent=1), f"\nspend ${out['spend_usd']:.4f}")


if __name__ == "__main__":
    main()
