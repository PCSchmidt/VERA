"""Run the judge on the real claims of the three topic runs, against the labels in real_claims_labels.csv.

The 30 claims were drawn by seed from the claims the synthesis stage passed (scripts/build_real_claims_sheet.py) and
labelled by an AI helper blind to every verdict (the labels file says who). Both routings of the constructed benchmark
(the decided GLM-direct and Jev-first) are run, and the reference, Claude Sonnet 5.5. The helper that labelled is of the
same model family as the reference, so agreement with the reference is not independent evidence; it is reported for
completeness. Reports per-item agreement with Wilson 95% intervals, false accepts (an unsupported claim passed: the
case that matters for a literature section) and false rejects, and which claims each path got wrong. Resumable.

Usage: uv run python scripts/run_real_claims.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from vera.bench.candidates import make_backend
from vera.bench.harness import load_recs, run_backend
from vera.bench.metrics import backend_metrics, modal_answers, same
from vera.ledger import Ledger
from vera.literature import questions
from vera.schemas import BenchmarkItem, Budget

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_claim_bench import REPEATS, Routed, rate  # noqa: E402 - the benchmark's wrappers, shared

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data" / "claim_bench"


def load_items() -> list[BenchmarkItem]:
    question = questions.claim_supported("x", {"locator": "x", "text": "x"}, "x")[0]
    sheet = {r["id"]: r for r in csv.DictReader((BENCH / "real_claims_sheet.csv").open(encoding="utf-8"))}
    labels = {r["id"]: r for r in csv.DictReader((BENCH / "real_claims_labels.csv").open(encoding="utf-8"))}
    if set(sheet) != set(labels):
        raise SystemExit("the labels do not cover exactly the drawn claims")
    return [
        BenchmarkItem(
            id=i,
            task="claim_support",
            split="test",
            question=question,
            state=sheet[i]["material (claim and passage)"],
            label=labels[i]["supported"] == "yes",
            construction={"kind": "real", "topic": sheet[i]["topic"]},
            generator="real claim from a topic run",
        )
        for i in sorted(sheet)
    ]


def main() -> None:
    items = load_items()
    chosen = json.loads((BENCH / "results.json").read_text(encoding="utf-8"))["dev"]["chosen"]
    n = 1
    while (ROOT / "data" / "ledger" / f"run_realclaims-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"realclaims-{n}", root=ROOT / "data" / "ledger")
    budget, ref_budget = Budget(max_usd=0.2, max_wall_seconds=3600), Budget(max_usd=0.5, max_wall_seconds=3600)
    arms = {name: Routed(name, ledger, budget, via_jev=name == "jev_glm") for name in ("glm_direct", "jev_glm")}
    reference = make_backend("sonnet-ref", ledger=ledger, budget=ref_budget, component="p2.realclaims")
    raw = BENCH / "raw"
    for name, arm in arms.items():  # both routings: no selection happens here, so both are reported
        run_backend(arm, items, REPEATS["test"], raw / f"real_{name}.jsonl", pause_s=3)
    run_backend(reference, items, REPEATS["reference"], raw / "real_reference.jsonl", pause_s=3)
    by_id = {i.id: i for i in items}
    r_recs = load_recs(raw / "real_reference.jsonl")
    r_modes = modal_answers(r_recs)

    def summary(modes: dict) -> dict:
        ids = list(modes)
        return {
            "agreement": rate([same(modes[i], by_id[i].label) for i in ids]),
            "false_accept": rate([bool(modes[i]) for i in ids if by_id[i].label is False]),
            "false_reject": rate([not modes[i] for i in ids if by_id[i].label is True]),
            "wrong": [i for i in ids if not same(modes[i], by_id[i].label)],
        }

    paths = {}
    for name in arms:
        recs = load_recs(raw / f"real_{name}.jsonl")
        modes = modal_answers(recs)
        paths[name] = summary(modes) | {
            "metrics": backend_metrics(recs, r_modes),
            "agreement_with_reference": rate([same(modes[i], r_modes[i]) for i in modes]),
        }
    results = {
        "n": len(items), "n_supported": sum(i.label for i in items), "dev_chosen_path": chosen, "repeats": REPEATS,
        "paths": paths, "reference": summary(r_modes) | {"metrics": backend_metrics(r_recs, r_modes)},
        "labels": "an AI helper (Claude Code), blind to every verdict; the reference judge is the same model family",
        "spend_usd": {"paths": budget.spent_usd, "reference": ref_budget.spent_usd},
        "ledger": ledger.path.relative_to(ROOT).as_posix(),
    }  # fmt: skip
    (BENCH / "real_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    for who, r in [*results["paths"].items(), ("reference", results["reference"])]:
        print(f"{who}: agreement {r['agreement']['k']}/{r['agreement']['n']}; "
              f"false accept {r['false_accept']['k']}/{r['false_accept']['n']}; "
              f"false reject {r['false_reject']['k']}/{r['false_reject']['n']}; wrong {r['wrong']}")  # fmt: skip


if __name__ == "__main__":
    main()
