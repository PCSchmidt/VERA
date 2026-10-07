# ruff: noqa: E501
"""Seeded faults, version 3 (Increment 4): the v2 faults plus method-code, figure and reproduction-basis faults.

The v2 fault types stay as they were (`vera.audit.seeded_v2`, with the three known misses `reversed_comparison`,
`misattributed_number` and `overstated_claim`, reported again and not tuned for on the test split). New paper faults:

  method_code_missing_step   a sentence added to the paper's account of an idea that describes a step its code does not perform
  method_code_undescribed    a substantial function added to the idea's code that the paper does not describe          (subtle)
  figure_altered             one plotted point of a figure changed, its source cell and the table left right
  reproduction_basis_wrong   the row set (in-sample or held-out) the baseline was reproduced on, swapped in its sentence (subtle)

A planter returns `(new paper text, location, description, extra files)` or None when the document has nowhere to plant the
fault: the extra files are the items' own `methods.json` or `figures.json` when the fault is in the code or the figure.

`audit_source_sha256` hashes the audit's own source including the new modules: the freeze for v3.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

from vera.audit import seeded_v2
from vera.audit.method_code import idea_paragraphs, method_section
from vera.audit.numbers import sentences

PAPER_FAULTS = [*seeded_v2.PAPER_FAULTS, "method_code_missing_step", "method_code_undescribed", "figure_altered",
                "reproduction_basis_wrong"]  # fmt: skip
LIT_FAULTS = list(seeded_v2.LIT_FAULTS)
SUBTLE = seeded_v2.SUBTLE | {"method_code_undescribed", "reproduction_basis_wrong"}
FROZEN_FILES = [*seeded_v2.FROZEN_FILES, "vera/audit/basis.py", "vera/audit/figure_check.py", "vera/audit/method_code.py",
                "vera/audit/novelty.py", "vera/loop/figures.py"]  # fmt: skip
INVENTED_STEPS = [
    "It then refits each component by isotonic regression to smooth the result.",
    "A final step rescales every component by its bootstrap standard deviation.",
    "Components whose variance falls below one percent of the total are set to zero.",
    "The depth parameter is chosen by five-fold cross-validation on the training rows.",
]
EXTRA_FUNCTION = '''

def _winsorise_components(components, lower=0.01, upper=0.99):
    """Clip every component to its own quantile range (a step the paper does not describe)."""
    clipped = {}
    for key, values in components.items():
        lo, hi = np.quantile(values, [lower, upper])
        clipped[key] = np.clip(values, lo, hi)
    return clipped
'''


def audit_source_sha256(root: Path) -> str:
    h = hashlib.sha256()
    for rel in sorted(FROZEN_FILES):
        h.update(rel.encode() + b"\0" + (root / rel).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def plant_paper(kind: str, text: str, results_json: dict, rng: random.Random, *, methods: dict[str, str] | None = None,
                figures: list[dict] | None = None) -> tuple[str, str, str, dict[str, str]] | None:
    if kind in seeded_v2.PAPER_FAULTS:
        planted = seeded_v2.plant_paper(kind, text, results_json, rng)
        return None if planted is None else (*planted, {})
    if kind == "method_code_missing_step":
        method = method_section(text)
        for idea in rng.sample(sorted(methods or {}), len(methods or {})):
            for para in idea_paragraphs(method, idea):
                first = re.split(r"(?<=[.!?])\s+", para, maxsplit=1)
                step = rng.choice(INVENTED_STEPS)
                new_para = f"{first[0]} {step}" + (f" {first[1]}" if len(first) > 1 else "")
                return text.replace(para, new_para, 1), f"Method, {idea}", f"added a step with no code: {step!r}", {}
        return None
    if kind == "method_code_undescribed":
        method = method_section(text)
        for idea in rng.sample(sorted(methods or {}), len(methods or {})):
            if idea_paragraphs(method, idea):
                code = methods[idea]
                new_code = code.rstrip() + "\n" + EXTRA_FUNCTION
                if "import numpy" not in new_code:
                    new_code = "import numpy as np\n" + new_code
                return text, f"code of {idea}", "added a substantial function the paper does not describe", {"methods.json": json.dumps({**methods, idea: new_code})}
        return None
    if kind == "figure_altered":
        if not figures:
            return None
        rec = rng.choice(figures)
        points = [p for pts in rec["data"].values() for p in pts]
        point = rng.choice(points)
        for p in points:
            if p["cell"] == point["cell"]:
                p["mean"] = p["mean"] * 1.5 + 1.0
        return text, f"figure {rec['id']}", f"one plotted point changed ({point['cell']})", {"figures.json": json.dumps(figures)}
    if kind == "reproduction_basis_wrong":
        for _, s in sentences(text):
            if re.search(r"reproduc", s, re.IGNORECASE) and re.search(r"in[- ]sample|held[- ]out", s, re.IGNORECASE):
                swapped = re.sub(r"in[- ]sample", "§HELD§", s, count=1, flags=re.IGNORECASE)
                if swapped != s:
                    new = swapped.replace("§HELD§", "held-out")
                else:
                    new = re.sub(r"held[- ]out", "in-sample", s, count=1, flags=re.IGNORECASE)
                return text.replace(s, new, 1), "Method", f"reproduction basis swapped: {new[:100]!r}", {}
        return None
    return None


# ── running the audit on an item ─────────────────────────────────────────────────────────────────────

SEEDED_V3 = Path("data") / "seeded_v3"
METHOD_FAULTS = {"method_code_missing_step", "method_code_undescribed"}


def item_dir(root: Path, row: dict) -> Path:
    if row["fault_type"] == "control":
        return root / SEEDED_V3 / "base" / row["doc"]
    return root / SEEDED_V3 / "items" / f"{row['doc']}__{row['fault_type']}"


def _json_if(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def audit_item(root: Path, row: dict, *, ask, lookup, target: dict | None = None):
    """The v3 audit's run on one item: a paper with its code and figures, or a literature section."""
    from vera.audit import run_audit, run_literature_audit  # noqa: PLC0415

    base = root / SEEDED_V3 / "base" / row["doc"]
    here = item_dir(root, row)
    retrieved = seeded_v2.load_jsonl(base / "retrieved.jsonl")
    if row["kind"] == "paper":
        results = json.loads((base / "results.json").read_text(encoding="utf-8"))
        text = (here / "paper.md").read_text(encoding="utf-8")
        methods = _json_if(here / "methods.json", None) or _json_if(base / "methods.json", {})
        figures = _json_if(here / "figures.json", None)
        if figures is None:
            figures = _json_if(base / "figures.json", None)
        ideas = {i["name"]: i["description"] for i in results.get("ideas", []) if i["name"] in methods}
        return run_audit(text, results, retrieved, ask=ask, lookup=lookup, paper_id=row["fault_id"],
                         paper_source=f"{here.name}/paper.md", target=target, figures=figures, basis=True,
                         methods=methods or None, ideas=ideas or None, records=retrieved)  # fmt: skip
    text = (here / "literature.md").read_text(encoding="utf-8")
    claims = seeded_v2.load_jsonl(here / "claims.jsonl")
    return run_literature_audit(text, claims, seeded_v2.load_jsonl(base / "passages.jsonl"), retrieved, ask=ask,
                                paper_id=row["fault_id"], paper_source=f"{here.name}/literature.md")  # fmt: skip
