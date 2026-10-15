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


def _light(folder: Path) -> str | None:
    for report in (folder / "audit_report.json", folder / "artifacts" / "audit_report.json"):
        if report.exists():
            return _json(report).get("overall")
    return None


def paper_of(root: Path, spec: dict) -> dict | None:
    """The review paper made from an example's review, if the showcase lists one: its light is its own audit's."""
    p = spec.get("paper")
    if not p:
        return None
    folder = root / p["dir"]
    return {
        "title": _json(folder / "paper.json")["title"], "dir": p["dir"], "retrieved": p.get("retrieved"),
        "made": p.get("made"), "spent_usd": p["spent_usd"], "budget_cap_usd": p.get("budget_cap_usd"),
        "audit": _light(folder), "outcome": p["outcome"], "known_issues": p.get("known_issues"),
    }  # fmt: skip


def example(root: Path, spec: dict) -> dict:
    folder = root / spec["dir"]
    light = _light(folder)
    request = _json(folder / "app_request.json") if (folder / "app_request.json").exists() else {}
    scope_path = root / spec["scope_file"] if spec.get("scope_file") else folder / "scope.json"
    scope = _json(scope_path) if scope_path.exists() else {}
    topic = _json(root / spec["topic_file"]) if spec.get("topic_file") else {}
    return {
        "id": spec["id"], "title": spec["title"], "kind": spec["kind"], "topic": topic.get("text") or request.get("topic"),
        "question": scope.get("question"), "guidance": spec.get("guidance") or request.get("guidance"),
        "budget_cap_usd": spec.get("budget_cap_usd") or request.get("max_usd"),
        "spent_usd": spec["spent_usd"], "audit": light,
        "outcome": spec["outcome"], "document": f"{spec['dir']}/{spec['document']}",
        "evidence": [f"{spec['dir']}/{n}" for n in spec.get("evidence", [])], "retrieved": spec.get("retrieved"),
        "known_issues": spec.get("known_issues"), "paper": paper_of(root, spec),
    }  # fmt: skip


def examples(root: Path, file: str = "examples.json") -> list[dict]:
    specs = _json(root / "data" / "app" / file)["examples"]
    return [example(root, s) for s in specs]


def build_facts(root: Path, examples_file: str = "examples.json") -> dict:
    items = examples(root, examples_file)
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
