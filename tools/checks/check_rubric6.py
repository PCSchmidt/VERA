# ruff: noqa: E501
"""Gate `rubric6_scored` (before Chris approves): the three review papers scored by a person, blind, before the independent scorer.

Requires data/results/rubric6_chris.json with a latest entry for each paper (P1, P2, P3) by a named human, marked blind, with six scores
of 1 to 5 and a preference, recorded before the independent scorer's file was started; data/results/rubric6_evaluator.json covering the
same papers; and the two not equal in every cell (a copy is not a scoring). Agreement, preferences and any model help are reported.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

OUTPUTS = ("P1", "P2", "P3")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty", "interpretation_follows")


def load(path, what: str):
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
    human = load(results / "rubric6_chris.json", "the person's scores")
    indep = load(results / "rubric6_evaluator.json", "the independent scorer's scores")
    if human["by"].lower() in ("evaluator", "codex", "claude", "claude code"):
        block("the person's file is not by a person")
    first_indep = min(e["at"] for e in indep["entries"])
    h, i = latest(human["entries"]), latest(indep["entries"])
    for o in OUTPUTS:
        e = h.get(o)
        if e is None:
            block(f"no human score for {o}")
        if not e.get("blind") or e["at"] >= first_indep:
            block(f"{o}: the human score is not blind, or was recorded after the independent scorer started")
        if sorted(e["scores"]) != sorted(CRITERIA) or not all(1 <= v <= 5 for v in e["scores"].values()):
            block(f"{o}: the human scores are malformed")
        if e.get("prefer") not in ("paper", "review", "same"):
            block(f"{o}: no preference between the paper and its review")
        if o not in i:
            block(f"the independent scorer did not score {o}")
    if all(h[o]["scores"] == i[o]["scores"] for o in OUTPUTS):
        block("the human scores equal the independent scores in every cell: a copy, not a scoring")
    equal = sum(h[o]["scores"][c] == i[o]["scores"][c] for o in OUTPUTS for c in CRITERIA)
    helped = [f"{o} ({h[o]['helped_by']})" for o in OUTPUTS if h[o].get("helped_by")]
    prefs = ", ".join(f"{o}: {h[o]['prefer']}/{i[o].get('prefer', '?')}" for o in OUTPUTS)
    ok(f"3 papers scored blind by {human['by']} before the independent scorer; {equal} of {len(OUTPUTS) * len(CRITERIA)} cells equal; "
       f"preference (person/independent) {prefs}; model help: {', '.join(helped) or 'none stated'}")  # fmt: skip


if __name__ == "__main__":
    main()
