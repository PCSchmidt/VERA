"""Run the claim-support benchmark (data/claim_bench/): does the judge path see whether a passage supports a claim?

The question is `lit.claim_supported`, the one the synthesis stage and the final literature audit ask. Two routings are
compared on the **dev** items only (topic credal-dro): `glm_direct`, the decided configuration (`lit.` questions go
straight to GLM-5.3 Flash at minimal reasoning), and `jev_glm` (the same question sent through Jev first, escalating
to GLM below confidence 0.7). The routing with the higher dev agreement with the labels is carried to the **test**
items (the other topics), 3 repeats, with Claude Sonnet 5.5 as the reference (2 repeats); a tie keeps the decided
configuration. The test items' hash is verified first. Verdicts are resumable (vera.bench.harness). Agreement is per
item (the modal answer over repeats), with Wilson 95% intervals; false accepts (an unsupported claim passed) and false
rejects (a supported claim failed) are reported separately because they cost different things.

Usage: uv run python scripts/run_claim_bench.py
"""

from __future__ import annotations

import json
from pathlib import Path

from vera.bench.candidates import make_backend
from vera.bench.claims import items_hash
from vera.bench.harness import load_recs, run_backend
from vera.bench.metrics import backend_metrics, modal_answers, same
from vera.bench.retest import wilson
from vera.judge.cheap_path import cheap_path
from vera.ledger import Ledger
from vera.schemas import BenchmarkItem, Budget

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data" / "claim_bench"
REPEATS = {"dev": 2, "test": 3, "reference": 2}


class Routed:
    """The cheap path as a JudgeBackend for the harness. With `via_jev` the question id loses its `lit.` prefix, so the
    path sends it Jev-first instead of straight to GLM."""

    cost_rank = 1

    def __init__(self, name: str, ledger: Ledger, budget: Budget, *, via_jev: bool) -> None:
        self.name, self.via_jev = name, via_jev
        self.path = cheap_path(ledger=ledger, budget=budget, component="p2.claimbench")

    def ask(self, state, questions):
        if self.via_jev:
            questions = [q.model_copy(update={"id": q.id.replace("lit.", "claim.", 1)}) for q in questions]
        return self.path.ask(state, questions)


def rate(flags: list[bool]) -> dict:
    k, n = sum(flags), len(flags)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 4), round(hi, 4)]}


def split_rates(modes: dict, by_id: dict) -> dict:
    """Agreement with the label overall and by construction kind; false accepts and false rejects."""
    ids = list(modes)
    agree = [same(modes[i], by_id[i].label) for i in ids]
    kinds = sorted({by_id[i].construction["kind"] for i in ids})
    return {
        "agreement": rate(agree),
        "by_kind": {
            k: rate([a for a, i in zip(agree, ids, strict=True) if by_id[i].construction["kind"] == k]) for k in kinds
        },  # fmt: skip
        "false_accept": rate([bool(modes[i]) for i in ids if by_id[i].label is False]),  # unsupported claim passed
        "false_reject": rate([not modes[i] for i in ids if by_id[i].label is True]),  # supported claim failed
    }


def main() -> None:
    items = [BenchmarkItem.model_validate_json(ln) for ln in (BENCH / "items.jsonl").read_text("utf-8").splitlines()]
    split = json.loads((BENCH / "split.json").read_text(encoding="utf-8"))
    test = [i for i in items if i.split == "test"]
    dev = [i for i in items if i.split == "dev"]
    if items_hash(test) != split["test_sha256"]:
        raise SystemExit("the test items changed since the split was fixed: refusing to run")
    n = 1
    while (ROOT / "data" / "ledger" / f"run_claimbench-{n}.jsonl").exists():
        n += 1
    ledger = Ledger.for_run(f"claimbench-{n}", root=ROOT / "data" / "ledger")
    budget, ref_budget = Budget(max_usd=0.4, max_wall_seconds=7200), Budget(max_usd=1.0, max_wall_seconds=7200)
    arms = {"glm_direct": Routed("glm_direct", ledger, budget, via_jev=False),
            "jev_glm": Routed("jev_glm", ledger, budget, via_jev=True)}  # fmt: skip
    raw = BENCH / "raw"
    dev_by_id = {i.id: i for i in dev}
    dev_results = {}
    for name, arm in arms.items():  # dev only: the routing is chosen here
        run_backend(arm, dev, REPEATS["dev"], raw / f"{name}_dev.jsonl", pause_s=3)
        modes = modal_answers(load_recs(raw / f"{name}_dev.jsonl"))
        dev_results[name] = split_rates(modes, dev_by_id)
    chosen = max(arms, key=lambda a: (dev_results[a]["agreement"]["rate"], a == "glm_direct"))
    print("dev agreement:", {a: (r["agreement"]["k"], r["agreement"]["n"]) for a, r in dev_results.items()},
          "chosen:", chosen)  # fmt: skip
    reference = make_backend("sonnet-ref", ledger=ledger, budget=ref_budget, component="p2.claimbench")
    run_backend(arms[chosen], test, REPEATS["test"], raw / f"{chosen}_test.jsonl", pause_s=3)
    run_backend(reference, test, REPEATS["reference"], raw / "reference_test.jsonl", pause_s=3)

    by_id = {i.id: i for i in test}
    c_recs, r_recs = load_recs(raw / f"{chosen}_test.jsonl"), load_recs(raw / "reference_test.jsonl")
    c_modes, r_modes = modal_answers(c_recs), modal_answers(r_recs)
    results = {
        "test_items": len(test), "test_sha256": split["test_sha256"], "repeats": REPEATS,
        "dev": {"arms": dev_results, "chosen": chosen,
                "rule": "higher dev agreement with the labels; a tie keeps glm_direct, the decided configuration"},
        "test": {
            "chosen_path": split_rates(c_modes, by_id) | {
                "agreement_with_reference": rate([same(c_modes[i], r_modes[i]) for i in c_modes if i in r_modes]),
                "metrics": backend_metrics(c_recs, r_modes)},
            "reference": split_rates(r_modes, by_id) | {"metrics": backend_metrics(r_recs, r_modes)},
        },
        "spend_usd": {"routing_and_dev": budget.spent_usd, "reference": ref_budget.spent_usd},
        "ledger": ledger.path.relative_to(ROOT).as_posix(),
    }  # fmt: skip
    (BENCH / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    t = results["test"]
    for who in ("chosen_path", "reference"):
        r = t[who]
        print(f"{who}: agreement {r['agreement']['k']}/{r['agreement']['n']} CI {r['agreement']['ci95']}; "
              f"false accept {r['false_accept']['k']}/{r['false_accept']['n']}; "
              f"false reject {r['false_reject']['k']}/{r['false_reject']['n']}")  # fmt: skip
    print("spend:", results["spend_usd"])


if __name__ == "__main__":
    main()
