"""The Increment 2 re-test of the judge on the loop's real gate decisions (docs/04 T1, reverse-if 1).

The Increment 1 benchmark was near ceiling on two of three tasks and its targets were set after seeing its test split.
This set is built from what the loop actually asked its judge: every `loop.*` gate decision in the runs' gates.jsonl
that has a programmatic (shadow) answer, i.e. a label computed from the table the judge read, plus near-tie and
perturbed copies of the loop's own result tables (the Increment 1 relations) to reach a usable size. Items are
`BenchmarkItem`s, so the Increment 1 harness and metrics run on them unchanged. Split by source run, with the test
items' SHA-256 recorded before any backend sees them.

Not included, and counted as such: `loop.idea_worth_run` (a Score with no computable answer) and the audit's
`cite.contains_entry` / `num.claim_consistent` questions (no shadow answer; their accuracy was measured in
Increment 1 and by the seeded-fault evaluation).
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

from vera.bench.build import RELATIONS
from vera.loop import questions, tables
from vera.schemas import BenchmarkItem, Question

KINDS = ("loop.baseline_reproduced", "loop.beats_baseline", "loop.best_method", "loop.guidance_met")
CURRENT_BASELINE_WORDING = "names the column to compare"  # the per-dataset reproduction wording (smoke-005 onward)
SPLIT_SEED = 20261005


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


# ── real decisions ───────────────────────────────────────────────────────────────────────────────────


def load_gate_records(root: Path) -> dict[str, list[dict]]:
    """run id -> its gates.jsonl records, from every run directory under runs/ (including set-aside ones)."""
    out = {}
    for path in sorted((root / "runs").rglob("gates.jsonl")):
        out[path.parent.name] = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return out


def is_current(records: list[dict]) -> bool:
    """Runs from before the per-dataset reproduction wording asked a different baseline question."""
    base = [r for r in records if r["question"]["id"] == "loop.baseline_reproduced"]
    if not base:  # a run that started from a recorded baseline (the comparison runs: smoke-007's, current wording)
        return True
    return CURRENT_BASELINE_WORDING in base[0]["question"]["text"]


def real_items(records_by_run: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    """Distinct (question, material) pairs with a shadow answer, each with the runs that asked it; and a coverage
    count of every loop.* record seen, so nothing is dropped silently."""
    seen: dict[str, dict] = {}
    coverage = Counter()
    for run, records in sorted(records_by_run.items()):
        current = is_current(records)
        for r in records:
            qid = r["question"]["id"]
            if not qid.startswith("loop."):
                continue
            coverage["records"] += 1
            if not current:
                coverage["excluded_older_question_wording"] += 1
            elif qid not in KINDS or r["shadow_answer"] is None:
                coverage["excluded_no_shadow_answer"] += 1
            else:
                key = digest(qid, r["question"]["text"], r["material"])
                if key in seen:
                    seen[key]["runs"].append(run)
                    coverage["duplicates_merged"] += 1
                else:
                    seen[key] = {"kind": qid, "question": r["question"], "material": r["material"],
                                 "label": r["shadow_answer"], "runs": [run], "origin": "real"}  # fmt: skip
    coverage["distinct_real_items"] = len(seen)
    return list(seen.values()), dict(coverage)


# ── perturbed copies of the loop's own result tables ─────────────────────────────────────────────────


def perturb_results(results: dict, rng: random.Random) -> dict:
    """A copy with every idea's held-out mean moved to a random relation to the baseline's (Increment 1's relations)."""
    out = copy.deepcopy(results)
    for method, res in out.items():
        if method == tables.BASELINE:
            continue
        for d, cell in res.items():
            base = results[tables.BASELINE][d][tables.PRIMARY]["mean"]
            relation = rng.choices(list(RELATIONS), weights=[0.2, 0.25, 0.1, 0.25, 0.2])[0]
            lo, hi = RELATIONS[relation]
            cell[tables.PRIMARY]["mean"] = base if relation == "tie" else base * (1 - rng.uniform(lo, hi))
    return out


def perturbed_items(sources: list[dict], rng: random.Random, limit: int) -> list[dict]:
    """sources: {"run", "results", "datasets", "n_seeds"}; each yields beats_baseline items for every idea and dataset
    and best_method items where the best is not tied, on a perturbed copy of its own table."""
    pool = []
    for src in sources:
        results = perturb_results(src["results"], rng)
        datasets, n_seeds = src["datasets"], src["n_seeds"]
        for method in [m for m in results if m != tables.BASELINE]:
            for d in datasets:
                q, material, shadow = questions.beats_baseline(method, d, results, datasets, n_seeds)
                pool.append({"kind": q.id, "question": q.model_dump(mode="json"), "material": material,
                             "label": shadow, "runs": [src["run"]], "origin": "perturbed"})  # fmt: skip
        for d in datasets:
            q, material, shadow = questions.best_method(d, results, datasets, n_seeds)
            if shadow is not None:
                pool.append({"kind": q.id, "question": q.model_dump(mode="json"), "material": material,
                             "label": shadow, "runs": [src["run"]], "origin": "perturbed"})  # fmt: skip
    rng.shuffle(pool)
    return pool[:limit]


def distinct_result_sources(root: Path, run_ids: list[str]) -> list[dict]:
    """One source per distinct results table among the runs (the 16 comparison runs share a baseline, not ideas)."""
    seen: dict[str, dict] = {}
    for run in run_ids:
        for path in (root / "runs").rglob(f"{run}/artifacts/results.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            key = digest(json.dumps(data["results"], sort_keys=True))
            seen.setdefault(key, {"run": run, "results": data["results"], "datasets": data["datasets"],
                                  "n_seeds": data["n_seeds"]})  # fmt: skip
    return list(seen.values())


# ── assembling the set ───────────────────────────────────────────────────────────────────────────────


def assign_splits(runs: list[str]) -> dict[str, str]:
    """Half the runs to test, by seeded shuffle within each family (smoke, gen-<arm>, loop), so every kind of run is in
    both halves."""
    families: dict[str, list[str]] = {}
    for run in sorted(runs):
        family = run.rsplit("-", 1)[0] if run.startswith("gen-") else run.split("-")[0]
        families.setdefault(family, []).append(run)
    rng, split = random.Random(SPLIT_SEED), {}
    for i, family in enumerate(sorted(families)):
        members = families[family]
        rng.shuffle(members)
        take = (len(members) + 1) // 2 if i % 2 == 0 else len(members) // 2
        for j, run in enumerate(members):
            split[run] = "test" if j < take else "dev"
    return split


def to_item(raw: dict, index: int, split: str) -> BenchmarkItem:
    q = Question.model_validate(raw["question"])
    return BenchmarkItem(
        id=f"retest-{index:04d}",
        task="loop_gate",
        split=split,
        question=q,
        state=raw["material"],
        label=raw["label"],
        construction={
            "kind": raw["kind"],
            "origin": raw["origin"],
            "source": ",".join(sorted(set(raw["runs"]))[:3]),
            "seed": SPLIT_SEED,
        },  # fmt: skip
        generator="vera.bench.retest/1",
    )


def build_items(root: Path, max_perturbed: int = 60) -> tuple[list[BenchmarkItem], dict]:
    records = load_gate_records(root)
    real, coverage = real_items(records)
    runs = sorted(r for r, recs in records.items() if is_current(recs))
    split_of = assign_splits(runs)
    rng = random.Random(SPLIT_SEED)
    extra = perturbed_items(distinct_result_sources(root, runs), rng, max_perturbed)
    raws = sorted(
        [*real, *extra], key=lambda r: (r["origin"], r["kind"], digest(json.dumps(r["question"]), r["material"]))
    )
    items = [to_item(raw, i, split_of[sorted(raw["runs"])[0]]) for i, raw in enumerate(raws)]
    coverage |= {"runs_used": len(runs), "perturbed_items": len(extra), "items": len(items),
                 "by_origin_kind": dict(Counter(f"{r['origin']}:{r['kind']}" for r in raws))}  # fmt: skip
    return items, coverage


def items_hash(items: list[BenchmarkItem]) -> str:
    """SHA-256 over the items' JSON lines, sorted by id."""
    lines = sorted(i.model_dump_json() for i in items)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
