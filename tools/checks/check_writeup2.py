# ruff: noqa: E501
"""Gate `writeup2_ready`: the paper-shaped write-up, figures and ablations (Increment 4).

Requires:
- the demonstrations: tests/test_loop_ablation.py holds the winner-is-ablated and no-winner-no-ablation tests, and
  tests/test_figures.py the figure-data and figure-fault tests;
- a produced paper (the protocol live run's, docs/results/protocol-live-1/): every required section as a heading, at least one
  figure whose image file is committed and whose plotted data equal the results.json cell it names (recomputed here), every
  figure referred to in the text, the reproduction basis stated (held-out or in-sample, in its Method section), an audit report
  that ran the figure check and is not red, and artifacts/ablation.json stating whether the ablation ran and why or why not.
"""

from __future__ import annotations

import json
import re

from _common import block, ok, repo_root_arg

SECTIONS = ("Abstract", "Related work", "Method", "Results", "Limitations", "References")


def load(path, what: str):
    if not path.exists():
        block(f"{what} not found ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def cell(results_json: dict, ref: str) -> dict | None:
    table, method, dataset, metric = ref.split("/")
    root = results_json.get("protocol") if table == "protocol" else {"results": results_json["results"]}
    entry = ((root or {}).get("results", {}).get(method) or {}).get(dataset) or {}
    value = entry.get(metric)
    return value if isinstance(value, dict) and entry.get("valid", True) else None


def main() -> None:
    args = repo_root_arg(__doc__).parse_args()
    tests = args.root / "tests"
    for name, needles in (("test_loop_ablation.py", ("test_RSH_F_04_the_winning_idea_is_ablated", "test_RSH_F_04_no_winner")),
                          ("test_figures.py", ("test_a_figure_drawn_from_altered_numbers_is_a_fail",))):  # fmt: skip
        text = (tests / name).read_text(encoding="utf-8") if (tests / name).exists() else block(f"tests/{name} not found")
        for n in needles:
            if n not in text:
                block(f"tests/{name} lacks {n}")
    folder = args.root / "docs" / "results" / "protocol-live-1"
    paper = (folder / "paper.md").read_text(encoding="utf-8") if (folder / "paper.md").exists() else block("the paper is not committed")
    for s in SECTIONS:
        if re.search(rf"^#{{1,6}}\s*{re.escape(s)}\b", paper, re.IGNORECASE | re.MULTILINE) is None:
            block(f"the paper has no {s} section")
    records = load(folder / "figures" / "figures.json", "the figure records")
    rj = load(folder / "results.json", "results.json")
    if not records:
        block("the paper has no figures")
    for n, rec in enumerate(records, start=1):
        if not (folder / "figures" / rec["file"]).exists() or f"figures/{rec['file']}" not in paper:
            block(f"figure {rec['id']} is not committed or not in the paper")
        if not re.search(rf"\bFigure {n}\b", re.sub(r"^\s*Figure \d+\..*$", "", paper, flags=re.MULTILINE)):
            block(f"Figure {n} is not referred to in the text")
        plotted = {p["cell"]: p for pts in rec["data"].values() for p in pts}
        if set(plotted) != set(rec["cells"]):
            block(f"{rec['id']}: the plotted cells differ from the cells it names")
        for ref, p in plotted.items():
            v = cell(rj, ref)
            if v is None or abs(v["mean"] - p["mean"]) > 1e-9 or abs(v["std"] - p["std"]) > 1e-9:
                block(f"{rec['id']}: {ref} does not equal its results.json cell")
    method = re.search(r"^#{1,6}\s*Method.*?(?=^#{1,6}\s)", paper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if method is None or not re.search(r"in-sample|held-out", method.group(0), re.IGNORECASE):
        block("the Method section does not state the reproduction basis (held-out or in-sample)")
    audit = load(folder / "audit_report.json", "the audit report")
    if "figure" not in audit["checks_run"] or audit["overall"] == "red":
        block(f"the audit must include the figure check and not be red ({audit['checks_run']}, {audit['overall']})")
    ablation = load(folder / "ablation.json", "the ablation record")
    if "ran" not in ablation or (not ablation["ran"] and not ablation.get("reason")):
        block("the ablation record must say whether it ran, and why not")
    ok(f"{len(records)} figures match their cells; all sections present; audit {audit['overall']} with the figure check; "
       f"ablation {'ran' if ablation['ran'] else 'skipped: ' + ablation['reason'][:60]}")


if __name__ == "__main__":
    main()
