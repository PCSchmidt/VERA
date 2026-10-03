"""Repair a topic run's literature section after its final audit failed some claims, then audit it again.

Reads runs/<run_id>/artifacts/audit_report.json (scripts/audit_topic.py). For each `claim_support` failure the generator
rewrites the sentence to what its quote supports, or drops it; each rewrite is re-checked (quote verbatim in its
source, judge confident yes). The section before the repair is kept as literature.pre_audit_repair.md and
claims.pre_audit_repair.jsonl (never overwritten), what happened to each failed claim is in
artifacts/audit_repair.json, and the audit is run again on the result. The report decides whether it passes.

Usage: uv run python scripts/repair_topic.py scope-credal-dro-2 scope-llm-judge-numbers-3
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from vera.backends.generator import OpenRouterGenerator
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.literature import audit_repair, synthesis
from vera.schemas import Budget

ROOT = Path(__file__).resolve().parents[1]
MIN_CONFIDENCE = 0.7


def jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def repair_run(run_id: str, max_usd: float) -> dict:
    run_dir = ROOT / "runs" / run_id
    report = json.loads((run_dir / "artifacts" / "audit_report.json").read_text(encoding="utf-8"))
    md = (run_dir / "literature.md").read_text(encoding="utf-8")
    text = md.partition("## References")[0].replace("## Literature review", "", 1).strip()
    claims, passages = jsonl(run_dir / "claims.jsonl"), jsonl(run_dir / "passages.jsonl")
    records = {r["key"]: r for r in jsonl(run_dir / "retrieved.jsonl")}
    bad = audit_repair.failed_claims(report, text, claims)
    if not bad:
        return {"run_id": run_id, "failed": 0, "note": "nothing to repair"}
    for name, src in (
        ("literature.pre_audit_repair.md", "literature.md"),
        ("claims.pre_audit_repair.jsonl", "claims.jsonl"),
    ):
        if not (run_dir / name).exists():  # the first version is kept, whatever happens next
            shutil.copy(run_dir / src, run_dir / name)
    scope = json.loads((run_dir / "scope.json").read_text(encoding="utf-8"))
    ledger = Ledger.for_run(run_id, root=ROOT / "data" / "ledger", resume=True)
    budget = Budget(max_usd=max_usd, max_wall_seconds=3600)
    generator = OpenRouterGenerator("sonnet", "anthropic/claude-sonnet-5.5", ledger=ledger, budget=budget,
                                    max_tokens=8000, reasoning={"effort": "minimal"})  # fmt: skip
    judge = cheap_path(ledger=ledger, budget=budget)

    def ask(question, material):
        (verdict,) = judge.ask(material, [question])
        verdict = verdict.model_copy(update={"producer_id": "p3.synthesize"})
        return verdict, verdict.confidence_source != "none" and verdict.confidence >= MIN_CONFIDENCE

    text, claims, log = audit_repair.repair(
        scope["question"], text, claims, bad, passages, records,
        lambda prompt: generator.generate(synthesis.SYSTEM, prompt, component="p3.synthesize"), ask,
    )  # fmt: skip
    (run_dir / "literature.md").write_text(synthesis.render(text, claims, records), encoding="utf-8")
    (run_dir / "claims.jsonl").write_text(synthesis.dump_jsonl(claims), encoding="utf-8")
    lit_json = run_dir / "artifacts" / "literature.json"
    stats = json.loads(lit_json.read_text(encoding="utf-8"))
    stats["n_claims_kept"] = len(claims)
    passes = stats.get("audit_repair", {}).get("passes", [])
    passes.append({"failed": len(bad), "rewritten": sum(e["outcome"] == "rewritten" for e in log),
                   "removed": sum(e["outcome"] == "removed" for e in log)})  # fmt: skip
    stats["audit_repair"] = {"passes": passes, "failed": sum(p["failed"] for p in passes),
                             "rewritten": sum(p["rewritten"] for p in passes),
                             "removed": sum(p["removed"] for p in passes)}  # fmt: skip
    lit_json.write_text(json.dumps(stats, indent=1, ensure_ascii=False), encoding="utf-8")
    log_file = run_dir / "artifacts" / "audit_repair.json"
    history = json.loads(log_file.read_text(encoding="utf-8")) if log_file.exists() else []
    history = (
        history
        if history and "pass" in history[0]
        else [{"pass": 0, "note": "earlier passes: see ledger", "log": history}]
    )
    history.append({"pass": len(passes), "log": log})  # every pass is kept
    log_file.write_text(json.dumps(history, indent=1, ensure_ascii=False), encoding="utf-8")
    sys.path.insert(0, str(ROOT / "scripts"))
    import audit_topic  # noqa: PLC0415

    return {"run_id": run_id, "failed": len(bad), **stats["audit_repair"], "repair_usd": round(budget.spent_usd, 4),
            "audit_after": audit_topic.audit_run(run_id, max_usd)}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_ids", nargs="+")
    ap.add_argument("--max-usd", type=float, default=0.25)
    args = ap.parse_args()
    for run_id in args.run_ids:
        print(json.dumps(repair_run(run_id, args.max_usd)))


if __name__ == "__main__":
    main()
