# ruff: noqa: E501
"""Build the seeded-fault set v3 (data/seeded_v3/) and fix its test split before the v3 audit runs on it.

Documents: write-ups the loop produced (papers, with their results, retrieval log, the code of their ideas and, for the protocol
runs, their figures) and literature sections of topic runs. The split is by source run and the test sources are runs the v3 audit
was not developed on. For each document one unmodified control and one planted copy per applicable fault type
(`vera.audit.seeded_v3`: the v2 faults plus method-code, figure and reproduction-basis faults). Writes

  data/seeded_v3/base/<doc>/...      the documents (a literature document's passages stay local: git-ignored)
  data/seeded_v3/items/<fault>/...   the planted copies (paper.md, and methods.json or figures.json when the fault is there)
  data/seeded_v3/manifest.csv, split.json (counts, the test items' SHA-256, `frozen_audit_sha256` null until the freeze)

Usage: uv run python scripts/build_seeded_v3.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
from pathlib import Path

from vera.audit import seeded_v2, seeded_v3

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "seeded_v3"
SEED = 20261012
DOCS = {  # id -> (kind, run directory, split)
    "gen-sonnet-2": ("paper", "runs/gen-sonnet-2", "dev"),
    "gen-sonnet-3": ("paper", "runs/gen-sonnet-3", "dev"),
    "topic-a-loop-1": ("paper", "runs/topic-a-loop-1", "dev"),
    "protocol-live-3": ("paper", "runs/protocol-live-3", "dev"),
    "topic-tabular": ("lit", "runs/topic4-tabular-resynth", "dev"),
    "topic-credal-dro": ("lit", "runs/scope-credal-dro-2", "dev"),
    "protocol-live-1": ("paper", "runs/protocol-live-1", "test"),
    "protocol-live-2": ("paper", "runs/protocol-live-2", "test"),
    "topic-a-loop-2": ("paper", "runs/topic-a-loop-2", "test"),
    "topic-a-loop-3": ("paper", "runs/topic-a-loop-3", "test"),
    "topic-conformal": ("lit", "runs/topic4-conformal-resynth", "test"),
    "topic-research-agents": ("lit", "runs/topic4-agents-resynth", "test"),
}  # fmt: skip
PAPER_FILES = [("paper.md", "paper.md"), ("artifacts/results.json", "results.json"), ("retrieved.jsonl", "retrieved.jsonl")]
LIT_FILES = [("literature.md", "literature.md"), ("claims.jsonl", "claims.jsonl"), ("passages.jsonl", "passages.jsonl"), ("retrieved.jsonl", "retrieved.jsonl")]


def idea_code(run: Path) -> dict[str, str]:
    """idea name -> the code of its last valid attempt, from the run's subset-experiment artifact."""
    for name in ("subset_exp.json", "subset_exp_raw.json"):
        f = run / "artifacts" / name
        if f.exists():
            log = json.loads(f.read_text(encoding="utf-8")).get("log", {})
            out = {}
            for idea, entry in log.items():
                good = [a for a in entry.get("attempts", []) if a.get("error") is None and a.get("code")]
                if entry.get("ok") and good:
                    out[idea] = good[-1]["code"]
            return out
    return {}


def main() -> None:
    if (OUT / "split.json").exists():
        raise SystemExit("data/seeded_v3/split.json exists: the split is fixed once; delete it on purpose to rebuild")
    rows: list[dict] = []
    for doc, (kind, run, split) in DOCS.items():
        base = OUT / "base" / doc
        base.mkdir(parents=True, exist_ok=True)
        for src, name in PAPER_FILES if kind == "paper" else LIT_FILES:
            shutil.copy(ROOT / run / src, base / name)
        methods, figures = {}, None
        if kind == "paper":
            methods = idea_code(ROOT / run)
            if methods:
                (base / "methods.json").write_text(json.dumps(methods), encoding="utf-8")
            fig = ROOT / run / "figures" / "figures.json"
            if fig.exists():
                figures = json.loads(fig.read_text(encoding="utf-8"))
                (base / "figures.json").write_text(json.dumps(figures), encoding="utf-8")
        rows.append({"fault_id": f"{doc}:control", "doc": doc, "kind": kind, "fault_type": "control", "location": "",
                     "description": "unmodified document", "subtle": "", "split": split})  # fmt: skip
        for fault in seeded_v3.PAPER_FAULTS if kind == "paper" else seeded_v3.LIT_FAULTS:
            rng = random.Random(f"{SEED}:{doc}:{fault}")
            item = OUT / "items" / f"{doc}__{fault}"
            if kind == "paper":
                text = (base / "paper.md").read_text(encoding="utf-8")
                results = json.loads((base / "results.json").read_text(encoding="utf-8"))
                planted = seeded_v3.plant_paper(fault, text, results, rng, methods=methods, figures=json.loads(json.dumps(figures)) if figures else None)
                if planted is None:
                    continue
                new_text, location, description, extra = planted
                item.mkdir(parents=True, exist_ok=True)
                (item / "paper.md").write_text(new_text, encoding="utf-8")
                for name, content in extra.items():
                    (item / name).write_text(content, encoding="utf-8")
            else:
                text = (base / "literature.md").read_text(encoding="utf-8")
                claims = seeded_v2.load_jsonl(base / "claims.jsonl")
                planted = seeded_v2.plant_literature(fault, text, claims, rng)
                if planted is None:
                    continue
                new_text, new_claims, location, description = planted
                item.mkdir(parents=True, exist_ok=True)
                (item / "literature.md").write_text(new_text, encoding="utf-8")
                (item / "claims.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in new_claims), encoding="utf-8")
            rows.append({"fault_id": f"{doc}:{fault}", "doc": doc, "kind": kind, "fault_type": fault, "location": location,
                         "description": description, "subtle": "yes" if fault in seeded_v3.SUBTLE else "", "split": split})  # fmt: skip
    cols = ["fault_id", "doc", "kind", "fault_type", "location", "description", "subtle", "split"]
    with (OUT / "manifest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    test = [r for r in rows if r["split"] == "test"]
    sources = sorted({r["doc"] for r in test})
    split = {"seed": SEED, "rule": "by source run (document): dev and test share no document; the test sources were not used to develop the v3 audit",
             "dev_docs": sorted(d for d, v in DOCS.items() if v[2] == "dev"), "test_docs": sources, "n_items": len(rows),
             "n_test_faults": sum(r["fault_type"] != "control" for r in test), "n_test_controls": sum(r["fault_type"] == "control" for r in test),
             "test_fault_types": sorted({r["fault_type"] for r in test if r["fault_type"] != "control"}),
             "test_sha256": test_hash(test), "frozen_audit_sha256": None,
             "known_misses_not_tuned_for": ["reversed_comparison", "misattributed_number", "overstated_claim"],
             "note": "fixed before the v3 audit ran on any test item; the audit's own hash is frozen before the test run"}  # fmt: skip
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    shown = ("n_items", "n_test_faults", "n_test_controls", "test_docs", "test_fault_types", "test_sha256")
    print(json.dumps({k: split[k] for k in shown}, indent=1))


def item_files(row: dict) -> list[Path]:
    here = OUT / ("base" / Path(row["doc"]) if row["fault_type"] == "control" else Path("items") / f"{row['doc']}__{row['fault_type']}")
    if row["kind"] == "paper":
        files = [here / "paper.md", here / "methods.json", here / "figures.json"]
    else:
        files = [here / "literature.md", here / "claims.jsonl"]
    return [p for p in files if p.exists()]


def test_hash(rows: list[dict]) -> str:
    items = [{**r, "sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in item_files(r)]} for r in rows]
    return seeded_v2.item_json(items)


if __name__ == "__main__":
    main()
