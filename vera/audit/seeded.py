"""Seeded faults for the audit (docs/06 §1): plant known faults in real write-ups, then measure detection.

Base papers are write-ups the loop itself produced (data/seeded/base/<id>/{paper.md, results.json, retrieved.jsonl});
a base is a *control* (it must audit without a `fail`) and the source of one planted copy per fault type:

  fabricated_citation   a plausible reference that does not exist, added to the list and cited in the abstract
  unretrieved_citation  an in-text citation of a key that was never retrieved
  altered_reference     one word of a real reference's title changed (a near-miss, the benchmark's hard case)
  numeric_prose         one number in a results sentence changed by a digit
  numeric_table         one mean in the results table changed by a digit
  fabricated_claim      a sentence with an improvement figure that appears nowhere in the results

The set is split dev/test by base paper, with the test items' SHA-256 recorded (data/seeded/split.json) before the
audit is run on them; the audit is developed against dev only (docs/06 §5). `plant` is deterministic given its seed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
from pathlib import Path

from vera.audit.numbers import RESULT_WORDS, known_values, matches, numbers_in, sentences

FAULT_TYPES = [
    "fabricated_citation", "unretrieved_citation", "altered_reference", "numeric_prose", "numeric_table",
    "fabricated_claim",
]  # fmt: skip
FAKE_REFERENCES = [
    ("Maria Keller, Tomas Ruiz", "Adaptive Cartesian Priors for Additive Tree Explanations", "2024"),
    ("Priya Nair, Lukas Brandt", "Orthogonal Boosting Decompositions with Calibrated Interaction Budgets", "2025"),
    ("Chen Wei, Anna Lindqvist", "Recursive Functional ANOVA for Gradient Boosted Ensembles", "2023"),
    ("Samuel Okafor, Eva Novak", "Hierarchical Shapley Surrogates for Tree Ensembles under Dependence", "2024"),
    ("Ravi Menon, Jonas Eberle", "Learning Sparse Interaction Graphs from Boosted Trees", "2025"),
    ("Isabel Duarte, Kenji Mori", "Cartesian Partition Refinement for Piecewise Constant Explainers", "2022"),
]
WORD_SWAPS = [("Tree", "Forest"), ("Scalable", "Distributed"), ("Explainability", "Interpretability"),
              ("Boosting", "Learning"), ("Decomposition", "Attribution")]  # fmt: skip
CLAIM_FIGURES = [37, 38, 41, 44, 52]


def perturb_digit(x: str, rng: random.Random) -> str:
    """x with one digit changed (never the leading digit of a number like 0.57 into a leading zero)."""
    positions = [i for i, c in enumerate(x) if c.isdigit()]
    for _ in range(20):
        i = rng.choice(positions)
        new = rng.choice([d for d in "0123456789" if d != x[i]])
        y = x[:i] + new + x[i + 1 :]
        if y != x and float(y) > 0:
            return y
    raise ValueError(f"could not perturb {x}")


def _body_end(text: str) -> int:
    return text.index("## References")


def plant(kind: str, text: str, results_json: dict, rng: random.Random) -> tuple[str, str, str] | None:
    """(new text, location, description), or None if this paper has nowhere to plant the fault."""
    known = known_values(results_json)
    if kind == "fabricated_citation":
        authors, title, year = rng.choice(FAKE_REFERENCES)
        entry = (
            f"[R3] {authors}. {title}. {year}. arXiv:{year[2:]}{rng.randint(1, 12):02d}.{rng.randint(10000, 99999)}."
        )
        head, sep, tail = text.partition("## Abstract")
        if not sep:
            return None
        first, para_sep, rest = tail.lstrip("\n").partition("\n\n")
        new = f"{head}## Abstract\n\n{first.rstrip()} Closely related work [R3] studies this setting.{para_sep}{rest}"
        return new.rstrip() + "\n" + entry + "\n", "References and Abstract", f"fabricated reference {title!r}"
    if kind == "unretrieved_citation":
        body = text[: _body_end(text)]
        for key in ("[R1]", "[R2]"):
            if key in body:
                i = body.index(key)
                return text[:i] + "[R7]" + text[i + 4 :], "body", f"{key} replaced by [R7], which was never retrieved"
        return None
    if kind == "altered_reference":
        for old, new_word in WORD_SWAPS:
            m = re.search(rf"^(\[R\d+\].*?\. )(.*{old}.*?)(\. \d{{4}}\.)", text, re.MULTILINE)
            if m and "## References" in text[: m.start()]:
                title = m.group(2).replace(old, new_word, 1)
                return text[: m.start(2)] + title + text[m.end(2) :], "References", f"{old!r} changed to {new_word!r}"
        return None
    body = text[: _body_end(text)]
    if kind == "numeric_prose":
        candidates = [
            (s, x) for _, s in sentences(text) if RESULT_WORDS.search(s) for x in numbers_in(s) if matches(x, known)
        ]
        rng.shuffle(candidates)
        for sentence, x in candidates:
            for _ in range(10):
                y = perturb_digit(x, rng)
                if not matches(y, known) and sentence in body:
                    new_sentence = sentence.replace(x, y, 1)
                    return text.replace(sentence, new_sentence, 1), "Results", f"{x} changed to {y} in prose"
        return None
    if kind == "numeric_table":
        cells = [(m.start(1), m.group(1)) for m in re.finditer(r"\| ([\d.]+) ± [\d.]+ ", body)]
        rng.shuffle(cells)
        for pos, x in cells:
            for _ in range(10):
                y = perturb_digit(x, rng)
                if y != x:
                    return text[:pos] + y + text[pos + len(x) :], "Results table", f"table mean {x} changed to {y}"
        return None
    if kind == "fabricated_claim":
        figure = next((f for f in rng.sample(CLAIM_FIGURES, len(CLAIM_FIGURES)) if not matches(str(f), known)), None)
        head, sep, tail = text.partition("## Results")
        if figure is None or not sep:
            return None
        claim = f"Overall, the best idea lowered the baseline residual by {figure}% across datasets."
        first, para_sep, rest = tail.lstrip("\n").partition("\n\n")
        return f"{head}## Results\n\n{first.rstrip()} {claim}{para_sep}{rest}", "Results", f"invented claim: {figure}%"
    raise ValueError(f"unknown fault type {kind!r}")


def item_hash(items: list[dict]) -> str:
    """SHA-256 over the items' JSON lines, sorted by fault id (as the benchmark's test hash is computed)."""
    lines = sorted(json.dumps(i, sort_keys=True, ensure_ascii=False) for i in items)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def detection_summary(rows: list[dict]) -> dict:
    """rows: {fault_id, fault_type, detected (any `fail` finding)}; controls have fault_type 'control' (a detection
    on a control is a false positive). Returns per-type detection and the control false-positive rate."""
    planted = [r for r in rows if r["fault_type"] != "control"]
    controls = [r for r in rows if r["fault_type"] == "control"]
    by_type = {}
    for t in FAULT_TYPES:
        sel = [r for r in planted if r["fault_type"] == t]
        by_type[t] = {
            "n": len(sel),
            "detected": sum(r["detected"] for r in sel),  # red: at least one `fail`
            "flagged": sum(r["detected"] or r.get("n_warn", 0) > 0 for r in sel),  # amber or red
        }
    return {
        "planted": len(planted), "detected": sum(r["detected"] for r in planted),
        "detection_rate": sum(r["detected"] for r in planted) / max(len(planted), 1), "by_type": by_type,
        "flagged": sum(r["detected"] or r.get("n_warn", 0) > 0 for r in planted),
        "controls": len(controls), "false_fails": sum(r["detected"] for r in controls),
        "controls_flagged": sum(r["detected"] or r.get("n_warn", 0) > 0 for r in controls),
    }  # fmt: skip


# ── evaluation ───────────────────────────────────────────────────────────────────────────────────────

SEEDED_DIR = Path("data") / "seeded"


def load_manifest(root: Path) -> list[dict]:
    with (root / SEEDED_DIR / "manifest.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def item_path(root: Path, row: dict) -> Path:
    if row["fault_type"] == "control":
        return root / SEEDED_DIR / "base" / row["paper_id"] / "paper.md"
    return root / SEEDED_DIR / "papers" / f"{row['fault_id'].replace(':', '__')}.md"


def compute_test_hash(root: Path, rows: list[dict] | None = None) -> str:
    """SHA-256 over the test items (manifest row + the text's own hash), as build_seeded_faults.py wrote it."""
    rows = rows if rows is not None else load_manifest(root)
    items = [
        {**r, "sha256": hashlib.sha256(item_path(root, r).read_bytes()).hexdigest()}
        for r in rows
        if r["split"] == "test"
    ]
    return item_hash(items)


def verify_split(root: Path) -> dict:
    """Raise unless the test items are exactly what they were when the split was fixed."""
    split = json.loads((root / SEEDED_DIR / "split.json").read_text(encoding="utf-8"))
    now = compute_test_hash(root)
    if now != split["test_sha256"]:
        raise ValueError(f"the test items changed since the split was fixed: {now} != {split['test_sha256']}")
    return split


def audit_item(root: Path, row: dict, *, ask, lookup, target: dict | None = None):
    from vera.audit import run_audit  # noqa: PLC0415

    base = root / SEEDED_DIR / "base" / row["paper_id"]
    results = json.loads((base / "results.json").read_text(encoding="utf-8"))
    retrieved = [json.loads(ln) for ln in (base / "retrieved.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    text = item_path(root, row).read_text(encoding="utf-8")
    return run_audit(text, results, retrieved, ask=ask, lookup=lookup, paper_id=row["fault_id"],
                     paper_source=str(item_path(root, row).relative_to(root)), target=target)  # fmt: skip


def evaluate(root: Path, split: str, *, ask, lookup, target: dict | None = None) -> tuple[list[dict], dict]:
    """Audit every item of `split`. Detected = the audit raised at least one `fail` finding."""
    if split == "test":
        verify_split(root)  # a changed test set is never evaluated silently
    rows, out = [r for r in load_manifest(root) if r["split"] == split], []
    for row in rows:
        run = audit_item(root, row, ask=ask, lookup=lookup, target=target)
        fails = [f for f in run.report.findings if f.severity == "fail"]
        warns = sum(f.severity == "warn" for f in run.report.findings)
        out.append(
            {
                "fault_id": row["fault_id"], "fault_type": row["fault_type"], "detected": bool(fails),
                "overall": run.report.overall, "n_fail": len(fails), "n_warn": warns,
                "cost_usd": run.report.total_cost_usd, "first_fail": fails[0].summary[:200] if fails else None,
            }
        )  # fmt: skip
    return out, detection_summary(out)
