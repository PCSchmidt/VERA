# ruff: noqa: E501
"""Measure the backends on the Increment 8 judge set against the reference (SPEC "Measuring the backends", JDG-P-04).

    dev     run every backend on the dev split (P1, N1); may be repeated; question wording may change only after this
    freeze  hash the test items and the measuring code into data/results/judge8_hash.json, before any backend sees a test item
    test    the one run on the test split (P2, P3, N2); refuses if the freeze is missing or stale, or a test result exists

Backends, each on every item, through the Increment 1 harness (`vera.bench.harness.run_backend`, unchanged): the reference
(Claude Sonnet 5.5, 2 repeats), Jev alone, GLM alone, and the decided path as configured before this increment (Jev, then
GLM below 0.7; 3 repeats each). The label is the reference's modal answer. Reported per question and backend: item-level
agreement with the reference (each item's modal answer against the reference's; Wilson 95%), flip rate across repeats,
share of verdicts below the 0.7 threshold, calibration against the reference (ECE, 10 bins), cost per verdict and p50
latency; for the decided path, how often Jev and GLM disagree on an item; whether each backend meets JDG-P-01 (97%
agreement) and JDG-P-03 (flip rate at most 2%), and the route those bars choose (the cheapest backend meeting both, else
the one agreeing best). Where an item is also in Increment 7's real-case set, the reference's agreement with those labels
is reported. Spend from the run's ledger; cap $3 for dev and test together (SPEC).

Usage: uv run python scripts/measure_judge8.py dev|freeze|test
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vera.bench.candidates import make_backend  # noqa: E402
from vera.bench.harness import load_recs, run_backend  # noqa: E402
from vera.bench.metrics import modal_answers, percentile, same  # noqa: E402
from vera.bench.retest import wilson  # noqa: E402
from vera.judge.cheap_path import LOOP_JUDGE_MAX_TOKENS, LOOP_JUDGE_REASONING, cheap_path  # noqa: E402
from vera.ledger import Ledger  # noqa: E402
from vera.schemas import Budget, Question  # noqa: E402

SET = ROOT / "data" / "judge8"
RESULTS = ROOT / "data" / "results"
FREEZE = RESULTS / "judge8_hash.json"
CHECK_FILES = ["scripts/build_judge_set8.py", "scripts/measure_judge8.py", "vera/literature/sentence_checks.py",
               "vera/judge/cheap_path.py", "vera/judge/router.py", "vera/bench/harness.py", "vera/bench/metrics.py",
               "vera/bench/candidates.py"]  # fmt: skip
CAP_USD = 3.0
THRESHOLD = 0.7
BAR_AGREEMENT, BAR_FLIP = 0.97, 0.02  # JDG-P-01, JDG-P-03, stated before the first measurement
REPEATS = {"reference": 2, "jev": 3, "glm": 3, "decided": 3}
KINDS = ("within_quote", "no_fact", "inference")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def items(split: str) -> list[dict]:
    rows = [json.loads(ln) for ln in (SET / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["split"] == split]


def test_hash() -> str:
    return hashlib.sha256("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items("test")).encode("utf-8")).hexdigest()


def check_hashes() -> dict[str, str]:
    return {f: sha_bytes((ROOT / f).read_bytes()) for f in CHECK_FILES}


class Named:
    """The decided path under a name, so the harness can record it."""

    def __init__(self, name: str, inner) -> None:
        self.name, self.inner = name, inner

    def ask(self, state, questions, threshold=None):
        return self.inner.ask(state, questions, threshold)


def backends(ledger: Ledger, budget: Budget) -> dict:
    comp = "p2.judge8"
    glm = make_backend("glm-flash", ledger=ledger, budget=budget, component=comp)
    glm.max_tokens, glm.reasoning = max(glm.max_tokens, LOOP_JUDGE_MAX_TOKENS), LOOP_JUDGE_REASONING  # as cheap_path sets it
    return {"reference": make_backend("sonnet-ref", ledger=ledger, budget=budget, component=comp),
            "jev": make_backend("jev", ledger=ledger, budget=budget, component=comp), "glm": glm,
            "decided": Named("decided", cheap_path(ledger=ledger, budget=budget, component=comp))}  # fmt: skip


def run(split: str) -> Path:
    raw = SET / "raw" / split
    ledger_path = ROOT / "data" / "ledger" / f"judge8_{split}.jsonl"
    if split == "test" and any(raw.glob("*.jsonl")):
        sys.exit("a test run already exists: the test split is measured once")
    earlier = sum(sum(r.cost_usd for r in Ledger(p).records()) for p in (ROOT / "data" / "ledger").glob("judge8_*.jsonl"))
    ledger = Ledger(ledger_path, run_id=f"judge8_{split}")
    budget = Budget(max_usd=CAP_USD - earlier, max_wall_seconds=4 * 3600)
    objs = [SimpleNamespace(id=i["id"], state=i["state"], question=Question.model_validate(i["question"]), task=i["kind"], label=None)
            for i in items(split)]  # fmt: skip
    for name, backend in backends(ledger, budget).items():
        run_backend(backend, objs, REPEATS[name], raw / f"{name}.jsonl", pause_s=2)
    return raw


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n) if n else (0.0, 1.0)
    return {"k": k, "n": n, "rate": round(k / n, 4) if n else None, "ci95": [round(lo, 3), round(hi, 3)]}


def ece_vs(recs: list, ref: dict, bins: int = 10) -> float:
    scored = [r for r in recs if r.item in ref and r.source != "none"]
    if not scored:
        return 0.0
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        group = [r for r in scored if lo <= r.confidence < hi or (b == bins - 1 and r.confidence == 1.0)]
        if group:
            acc = sum(same(r.answer, ref[r.item]) for r in group) / len(group)
            conf = sum(r.confidence for r in group) / len(group)
            total += len(group) / len(scored) * abs(acc - conf)
    return round(total, 4)


def realcase_overlap(split_items: list[dict], ref: dict) -> dict:
    """The reference against Increment 7's real-case labels, where the same claim, sentence or statement is in both sets."""
    rc = SET.parent / "realcase"
    if not (rc / "labels_test.json").exists():
        return {}
    labels = json.loads((rc / "labels_test.json").read_text(encoding="utf-8"))["labels"]
    rc_items = [json.loads(ln) for ln in (rc / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    by_ref = {(r["paper"], r["ref"]): labels.get(r["sheet_id"]) for r in rc_items if r["type"] in ("claim", "inference")}
    by_text = {(r["paper"], r["sentence"]): labels.get(r["sheet_id"]) for r in rc_items if r["type"] == "sentence"}
    out: dict[str, list[bool]] = defaultdict(list)
    for it in split_items:
        if it["id"] not in ref:
            continue
        if it["kind"] == "within_quote":
            lab = by_ref.get((it["paper"], it["ref"]))
            expect = None if lab is None else lab == "W"
        elif it["kind"] == "inference":
            lab = by_ref.get((it["paper"], it["ref"]))
            expect = None if lab is None else lab == "F"
        else:
            text = it["state"].split("Sentence: ", 1)[-1]
            lab = by_text.get((it["paper"], text))
            expect = None if lab is None else lab == "N"
        if expect is not None:
            out[it["kind"]].append(ref[it["id"]] is expect)
    return {k: rate(sum(v), len(v)) for k, v in out.items()}


def summarise(split: str, raw: Path) -> dict:
    split_items = items(split)
    kind_of = {i["id"]: i["kind"] for i in split_items}
    recs = {name: load_recs(raw / f"{name}.jsonl") for name in REPEATS}
    ref = modal_answers(recs["reference"])
    out: dict = {}
    for kind in KINDS:
        ids = {i for i, k in kind_of.items() if k == kind}
        row: dict = {"items": len(ids)}
        for name in ("jev", "glm", "decided", "reference"):
            mine = [r for r in recs[name] if r.item in ids]
            modes = modal_answers(mine)
            by_item: dict[str, set] = defaultdict(set)
            for r in mine:
                by_item[r.item].add(json.dumps(r.answer))
            agree = sum(same(modes[i], ref[i]) for i in modes if i in ref)
            flips = sum(len(v) > 1 for v in by_item.values())
            row[name] = {
                "agreement_with_reference": rate(agree, sum(1 for i in modes if i in ref)),
                "flip_rate": rate(flips, len(by_item)),
                "below_threshold": round(sum(r.confidence < THRESHOLD for r in mine) / len(mine), 4) if mine else None,
                "malformed": sum(r.source == "none" for r in mine),
                "ece_vs_reference": ece_vs(mine, ref),
                "cost_per_verdict_usd": round(sum(r.cost_usd for r in mine) / len(mine), 7) if mine else None,
                "latency_p50_ms": percentile([float(r.latency_ms) for r in mine], 50),
            }
            if name != "reference":
                a, f = row[name]["agreement_with_reference"]["rate"] or 0, row[name]["flip_rate"]["rate"] or 0
                row[name]["meets_bars"] = a >= BAR_AGREEMENT and f <= BAR_FLIP
        jev_modes = modal_answers([r for r in recs["jev"] if r.item in ids])
        glm_modes = modal_answers([r for r in recs["glm"] if r.item in ids])
        both = [i for i in jev_modes if i in glm_modes]
        row["jev_glm_disagree"] = rate(sum(not same(jev_modes[i], glm_modes[i]) for i in both), len(both))
        candidates = [n for n in ("jev", "glm", "decided") if row[n]["meets_bars"]]
        if candidates:
            route = min(candidates, key=lambda n: row[n]["cost_per_verdict_usd"] or 0)
            row["route"] = {"backend": route, "why": "cheapest backend meeting both bars"}
        else:
            route = max(("jev", "glm", "decided"), key=lambda n: row[n]["agreement_with_reference"]["rate"] or 0)
            row["route"] = {"backend": route, "why": "no backend meets both bars; this one agrees best with the reference"}
        out[kind] = row
    out["reference_vs_realcase_labels"] = realcase_overlap(split_items, ref)
    return out


def spent() -> float:
    return sum(sum(r.cost_usd for r in Ledger(p).records()) for p in (ROOT / "data" / "ledger").glob("judge8_*.jsonl"))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "freeze":
        if FREEZE.exists():
            sys.exit("already frozen: a new freeze needs a new test set")
        if any((SET / "raw" / "test").glob("*.jsonl")):
            sys.exit("a test run exists: the freeze must come before it")
        FREEZE.write_text(json.dumps({"frozen_at": datetime.now(UTC).isoformat(timespec="seconds"), "test_sha256": test_hash(),
                                      "check_sha256": check_hashes()}, indent=1), encoding="utf-8")  # fmt: skip
        print(f"frozen: test {test_hash()[:12]}, {len(CHECK_FILES)} code files")
        return
    if cmd not in ("dev", "test"):
        sys.exit(__doc__)
    if cmd == "test":
        frozen = json.loads(FREEZE.read_text(encoding="utf-8")) if FREEZE.exists() else None
        if frozen is None or frozen["test_sha256"] != test_hash() or frozen["check_sha256"] != check_hashes():
            sys.exit("the freeze is missing or stale (the test split or the measuring code changed after it): not running")
    raw = run(cmd)
    result = {"split": cmd, "run_at": datetime.now(UTC).isoformat(timespec="seconds"), "bars": {"agreement": BAR_AGREEMENT, "flip_rate": BAR_FLIP},
              "repeats": REPEATS, "summary": summarise(cmd, raw), "spend_usd_all_judge8": round(spent(), 4),
              "test_sha256": test_hash(), "check_sha256": check_hashes()}  # fmt: skip
    (RESULTS / f"judge8_{cmd}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: {n: (v[n]["agreement_with_reference"]["rate"], v[n]["flip_rate"]["rate"]) for n in ("jev", "glm", "decided")} | {"route": v["route"]["backend"]}
                      for k, v in result["summary"].items() if k in KINDS}, indent=1), f"\nspend ${result['spend_usd_all_judge8']:.4f}")


if __name__ == "__main__":
    main()
