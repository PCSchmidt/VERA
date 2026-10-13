# ruff: noqa: E501
"""Gate `rubric7_scored` (Increment 7): the two new papers scored first, blind, then by the independent scorer.

Requires data/results/rubric7_first.json with a latest entry for each paper (N1, N2), marked blind, with six scores of 1 to 5
and a preference, recorded before the independent scorer's file was started; when its scorer is not Chris, an attribution
saying who scored (the SPEC has Chris score first; on 2026-10-13 Chris had an assistant score instead). Requires
data/results/rubric7_evaluator.json covering both papers, each entry listing the defects it found by claim, sentence or
statement id (an empty list is allowed only with a note saying none was found); and the two files not equal in every cell.
"""

from __future__ import annotations

import json
import re

from _common import block, ok, repo_root_arg

OUTPUTS = ("N1", "N2")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty", "interpretation_follows")
ID = re.compile(r"^[CSI]\d+$")


def load(path, what: str) -> dict:
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def latest(entries: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for e in entries:
        out[e["output"]] = e
    return out


def main() -> None:
    results = repo_root_arg(__doc__).parse_args().root / "data" / "results"
    first = load(results / "rubric7_first.json", "the first scorer's scores")
    indep = load(results / "rubric7_evaluator.json", "the independent scorer's scores")
    if first["by"].lower() == "evaluator":
        block("the first scorer's file is the independent scorer's")
    if first["by"] != "Chris" and not str(first.get("attribution") or "").strip():
        block(f"the first scorer is {first['by']!r}, not Chris, and the file does not say who scored at whose request")
    first_indep = min(e["at"] for e in indep["entries"])
    f, i = latest(first["entries"]), latest(indep["entries"])
    defects = 0
    for o in OUTPUTS:
        e = f.get(o)
        if e is None:
            block(f"no first score for {o}")
        if not e.get("blind") or e["at"] >= first_indep:
            block(f"{o}: the first score is not blind, or was recorded after the independent scorer started")
        for who, entry in (("first", e), ("independent", i.get(o))):
            if entry is None:
                block(f"the {who} scorer did not score {o}")
            if sorted(entry["scores"]) != sorted(CRITERIA) or not all(1 <= v <= 5 for v in entry["scores"].values()):
                block(f"{o}: the {who} scores are malformed")
            if entry.get("prefer") not in ("paper", "review", "same"):
                block(f"{o}: the {who} scorer gave no preference")
        listed = i[o].get("defects")
        if not isinstance(listed, list) or any(not ID.match(str(d.get("id", ""))) for d in listed):
            block(f"{o}: the independent scorer's defects are not listed by claim, sentence or statement id")
        if not listed and "none" not in str(i[o].get("note", "")).lower():
            block(f"{o}: no defect listed and no note saying none was found")
        defects += len(listed)
    if all(f[o]["scores"] == i[o]["scores"] for o in OUTPUTS):
        block("the two files are equal in every cell: a copy, not a scoring")
    equal = sum(f[o]["scores"][c] == i[o]["scores"][c] for o in OUTPUTS for c in CRITERIA)
    ok(f"2 papers scored blind by {first['by']} before the independent scorer; {equal} of 12 cells equal; "
       f"{defects} defects listed by the independent scorer")


if __name__ == "__main__":
    main()
