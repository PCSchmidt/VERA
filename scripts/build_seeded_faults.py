"""Build the seeded-fault set for the audit (docs/06 §1, §5) under data/seeded/.

  base/<id>/{paper.md, results.json, retrieved.jsonl}   write-ups the loop produced, each with its own logs
  papers/<fault_id>.md                                  the base paper with one fault planted (vera.audit.seeded)
  manifest.csv                                          paper_id, fault_id, fault_type, location, description, split
  split.json                                            dev/test bases and the test items' SHA-256

Bases come from finished runs (`--from-run smoke-006`), and more drafts of the same results can be generated with the
loop's own write-up stage (`--regen 2`: costs a fraction of a cent each; needs OPENROUTER_API_KEY). Planting needs no
network and is deterministic. The split is by base paper and is fixed (seeded shuffle) with the test hash written
here, before the audit is run on the test items; rebuilding an existing set refuses to overwrite split.json.

Usage: uv run python scripts/build_seeded_faults.py --from-run smoke-004 --from-run smoke-006 --regen 2
       uv run python scripts/build_seeded_faults.py            # re-plant from the bases already in data/seeded/base
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SEEDED = ROOT / "data" / "seeded"
SPLIT_SEED = 20261004
FIELDS = ["paper_id", "fault_id", "fault_type", "location", "description", "split"]


def copy_run(run_id: str) -> str:
    base = f"run-{run_id}"
    dest = SEEDED / "base" / base
    src = ROOT / "runs" / run_id
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "paper.md", dest / "paper.md")
    shutil.copy(src / "artifacts" / "results.json", dest / "results.json")
    shutil.copy(src / "retrieved.jsonl", dest / "retrieved.jsonl")
    return base


def regenerate(source: str, n: int) -> list[str]:
    """More drafts of a base's results, from the loop's own write-up stage (same prompt, guidance and checks)."""
    from run_loop import GUIDANCE  # noqa: PLC0415 - the guidance the loop's runs use

    from vera.backends.generator import OpenRouterGenerator  # noqa: PLC0415
    from vera.ledger import Ledger  # noqa: PLC0415
    from vera.loop.stages import LoopDeps  # noqa: PLC0415
    from vera.loop.writeup import WRITE_SYSTEM, assemble, check_guidance, writeup_prompt  # noqa: PLC0415
    from vera.schemas import Budget, ProblemSpec, RunSpec  # noqa: PLC0415

    base_dir = SEEDED / "base" / source
    results = json.loads((base_dir / "results.json").read_text(encoding="utf-8"))
    refs = [json.loads(ln) for ln in (base_dir / "retrieved.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    spec = RunSpec(
        run_id="seeded-bases",
        problem=ProblemSpec(parent_id="2510.24815", repo_url="x", repo_commit="a" * 40, metric="residual_mse_pct",
                            datasets=results["datasets"], subset={"n_seeds": results["n_seeds"]}),
        guidance=GUIDANCE, budget=Budget(max_usd=0.2, max_wall_seconds=3600),
    )  # fmt: skip
    ledger = Ledger.for_run(f"seeded-bases-{source}-{n}", root=ROOT / "data" / "ledger")
    budget = spec.budget.model_copy()
    gen = OpenRouterGenerator("glm-flash", "z-ai/glm-5.3-flash", ledger=ledger, budget=budget, max_tokens=8000,
                              reasoning={"effort": "minimal"})  # fmt: skip
    deps = LoopDeps(spec=spec, target={}, generator=gen, judge=None, sandbox=None, budget=budget,  # type: ignore[arg-type]
                    run_dir=SEEDED, data_dir=SEEDED)  # fmt: skip
    state = {"results": results["results"], "ideas": results["ideas"], "best": results["best"],
             "verdicts": {"baseline": {"answer": True}}}  # fmt: skip
    made = []
    existing = len([p for p in (SEEDED / "base").iterdir() if p.name.startswith(f"{source}-")])
    for i in range(n):
        for _attempt in range(3):
            reply = gen.generate(WRITE_SYSTEM, writeup_prompt(deps, state, refs, None, None), component="p3.write_up")
            text = assemble(reply, state, deps, refs)
            if not check_guidance(text, GUIDANCE, refs):
                break
        else:
            print(f"  draft {i + 1} of {source} never met the guidance; skipped")
            continue
        base = f"{source}-{chr(ord('a') + existing + i)}"
        dest = SEEDED / "base" / base
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "paper.md").write_text(text, encoding="utf-8")
        shutil.copy(base_dir / "results.json", dest / "results.json")
        shutil.copy(base_dir / "retrieved.jsonl", dest / "retrieved.jsonl")
        made.append(base)
    print(f"generated {len(made)} draft(s) from {source}, ${budget.spent_usd:.4f}")
    return made


def plant_all() -> list[dict]:
    from vera.audit.seeded import FAULT_TYPES, plant  # noqa: PLC0415

    rows = []
    (SEEDED / "papers").mkdir(parents=True, exist_ok=True)
    for base_dir in sorted((SEEDED / "base").iterdir()):
        base = base_dir.name
        text = (base_dir / "paper.md").read_text(encoding="utf-8")
        results = json.loads((base_dir / "results.json").read_text(encoding="utf-8"))
        rows.append({"paper_id": base, "fault_id": f"{base}:control", "fault_type": "control", "location": "",
                     "description": "unmodified write-up"})  # fmt: skip
        for kind in FAULT_TYPES:
            rng = random.Random(f"{SPLIT_SEED}:{base}:{kind}")
            planted = plant(kind, text, results, rng)
            if planted is None:
                print(f"  {base}: no place to plant {kind}")
                continue
            new, location, description = planted
            fault_id = f"{base}:{kind}"
            (SEEDED / "papers" / f"{fault_id.replace(':', '__')}.md").write_text(new, encoding="utf-8")
            rows.append({"paper_id": base, "fault_id": fault_id, "fault_type": kind, "location": location,
                         "description": description})  # fmt: skip
    return rows


def write_split(rows: list[dict]) -> None:
    from vera.audit.seeded import item_hash  # noqa: PLC0415

    split_file = SEEDED / "split.json"
    if split_file.exists():
        raise SystemExit("data/seeded/split.json exists: the split and its test hash are fixed. Delete it only to "
                         "start a new set (and say why in the review).")  # fmt: skip
    bases = sorted({r["paper_id"] for r in rows})
    # stratified by results family (the run a base's results came from), so dev and test each hold both kinds of
    # paper: within a family bases are shuffled by seed, and test takes half, rounding up for every other family
    families: dict[str, list[str]] = {}
    for base in bases:
        families.setdefault(base.removesuffix("-a").removesuffix("-b").removesuffix("-c"), []).append(base)
    rng = random.Random(SPLIT_SEED)
    test_bases: set[str] = set()
    for i, family in enumerate(sorted(families)):
        members = sorted(families[family])
        rng.shuffle(members)
        take = (len(members) + 1) // 2 if i % 2 == 0 else len(members) // 2
        test_bases |= set(members[:take])
    for r in rows:
        r["split"] = "test" if r["paper_id"] in test_bases else "dev"
    items = []
    for r in rows:
        if r["split"] == "test":
            path = SEEDED / "papers" / f"{r['fault_id'].replace(':', '__')}.md"
            path = path if r["fault_type"] != "control" else SEEDED / "base" / r["paper_id"] / "paper.md"
            items.append({**r, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    split_file.write_text(json.dumps({
        "seed": SPLIT_SEED, "dev_bases": sorted(set(bases) - test_bases), "test_bases": sorted(test_bases),
        "test_items": len(items), "test_sha256": item_hash(items),
        "note": "fixed before the audit was run on any test item (docs/06 section 5)",
    }, indent=1), encoding="utf-8")  # fmt: skip
    with (SEEDED / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    digest = json.loads(split_file.read_text(encoding="utf-8"))["test_sha256"]
    print(f"{len(rows)} items; test bases {sorted(test_bases)}; test hash {digest[:12]}…")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-run", action="append", default=[], help="a finished run in runs/ to use as a base")
    ap.add_argument("--regen", type=int, default=0, help="extra drafts to generate per --from-run base")
    args = ap.parse_args()
    for run_id in args.from_run:
        base = copy_run(run_id)
        if args.regen:
            regenerate(base, args.regen)
    write_split(plant_all())


if __name__ == "__main__":
    main()
