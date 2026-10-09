# ruff: noqa: E501
"""Gate `rubric5_scored` (before Chris approves): the outputs were scored by a person, blind, before the independent scorer.

Requires:
- data/results/rubric5_chris.json with an entry for every output (W1, R1, R2), each by a named human (not the independent scorer), marked
  blind, with five scores of 1 to 5, and recorded before the independent scorer's file was written (its first entry's time);
- data/results/rubric5_evaluator.json (the independent scorer, run afterwards on the same files) covering the same outputs;
- the person's entries not equal to the independent scores in every cell of every output (a copy is not a scoring).
Agreement between the two scorers is reported, not gated.
"""

from __future__ import annotations

import json

from _common import block, ok, repo_root_arg

OUTPUTS = ("W1", "R1", "R2")
CRITERIA = ("answers_question", "coverage", "correctness", "reproducibility", "honesty")


def load(path, what: str):
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    results = args.root / "data" / "results"
    human = load(results / "rubric5_chris.json", "the person's scores")
    indep = load(results / "rubric5_evaluator.json", "the independent scorer's scores")
    if human["by"].lower() in ("evaluator", "codex", "claude", "claude code"):
        block("the person's file is not by a person")
    first_indep = min(e["at"] for e in indep["entries"])
    latest_human: dict[str, dict] = {}
    for e in human["entries"]:
        latest_human[e["output"]] = e
    for o in OUTPUTS:
        e = latest_human.get(o)
        if e is None:
            block(f"no human score for {o}")
        if not e.get("blind"):
            block(f"{o}: the human score is not marked blind")
        if e["at"] >= first_indep:
            block(f"{o}: the human score was recorded after the independent scorer's file was started")
        if sorted(e["scores"]) != sorted(CRITERIA) or not all(1 <= v <= 5 for v in e["scores"].values()):
            block(f"{o}: the human scores are malformed")
    latest_indep = {e["output"]: e for e in indep["entries"]}
    if set(OUTPUTS) - set(latest_indep):
        block(f"the independent scorer did not score {sorted(set(OUTPUTS) - set(latest_indep))}")
    if all(latest_human[o]["scores"] == latest_indep[o]["scores"] for o in OUTPUTS):
        block("the human scores equal the independent scores in every cell: a copy, not a scoring")
    equal = sum(latest_human[o]["scores"][c] == latest_indep[o]["scores"][c] for o in OUTPUTS for c in CRITERIA)
    ok(
        f"{len(OUTPUTS)} outputs scored blind by {human['by']} before the independent scorer; {equal} of {len(OUTPUTS) * len(CRITERIA)} cells equal"
    )


if __name__ == "__main__":
    main()
