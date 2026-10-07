# ruff: noqa: E501
"""The numbers and examples the landing page shows, read from the project's own files (never typed into the page).

`data/app/examples.json` lists which committed runs the Examples page shows; everything else (what they cost, their audit
light, the question and guidance that produced them, the maintainer's blind scores) is read from the run's files, the
ledgers and `data/results/rubric4_chris.json`. A test checks the static page contains no figure of its own.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

CRITERIA = {
    "answers_question": "answering the question asked",
    "coverage": "coverage of the important papers",
    "correctness": "correctness against the sources",
    "reproducibility": "reproducibility",
    "honesty": "honesty about limits",
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ledger_total(root: Path, ledger: str) -> float:
    path = root / ledger
    return sum(json.loads(ln)["cost_usd"] for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def example(root: Path, spec: dict) -> dict:
    folder = root / spec["dir"]
    light = _json(folder / "audit_report.json").get("overall") if (folder / "audit_report.json").exists() else None
    scope = _json(root / spec["scope_file"]) if spec.get("scope_file") else {}
    topic = _json(root / spec["topic_file"]) if spec.get("topic_file") else {}
    return {
        "id": spec["id"], "title": spec["title"], "kind": spec["kind"], "topic": topic.get("text"),
        "question": scope.get("question"), "guidance": spec["guidance"], "budget_cap_usd": spec["budget_cap_usd"],
        "spent_usd": spec["spent_usd"], "audit": light,
        "outcome": spec["outcome"], "document": f"{spec['dir']}/{spec['document']}",
        "evidence": [f"{spec['dir']}/{n}" for n in spec.get("evidence", [])], "retrieved": spec.get("retrieved"),
    }  # fmt: skip


def examples(root: Path) -> list[dict]:
    specs = _json(root / "data" / "app" / "examples.json")["examples"]
    return [example(root, s) for s in specs]


def build_facts(root: Path) -> dict:
    items = examples(root)
    lit = [e["spent_usd"] for e in items if e["kind"] == "literature"]
    paper = [e["spent_usd"] for e in items if e["kind"] == "paper"]
    rubric = _json(root / "data" / "results" / "rubric4_chris.json")["entries"]
    reviews = [e["scores"] for e in rubric if e["output"].startswith("L")]
    by_criterion = {c: round(mean(r[c] for r in reviews), 1) for c in CRITERIA}
    weakest = min(by_criterion, key=by_criterion.get)
    strongest = max(by_criterion, key=by_criterion.get)
    return {
        "literature_cost_usd": {"low": min(lit), "high": max(lit)} if lit else None,
        "paper_cost_usd": {"low": min(paper), "high": max(paper)} if paper else None,
        "review_scores": {
            "n_reviews": len(reviews), "scale": 5, "by_criterion": by_criterion,
            "weakest": CRITERIA[weakest], "weakest_mean": by_criterion[weakest],
            "strongest": CRITERIA[strongest], "strongest_mean": by_criterion[strongest],
        },
        "examples": items,
    }  # fmt: skip
