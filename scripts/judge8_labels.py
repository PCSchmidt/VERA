# ruff: noqa: E501
"""Labels on a sample of the Increment 8 judge set's test items (SPEC decision 4): a check on the reference judge itself.

    sheet                        write data/judge8/label_sheet.md: 15 test items per question, seeded, shuffled, no judge's answer
    record --by NAME [--attribution TEXT]
                                 read the filled sheet, check every item has Y or N and no item text changed, and write
                                 data/judge8/labels.json; --attribution is required when the labeller is not Chris

Labels must be recorded before the test run (`scripts/measure_judge8.py test`), so the labeller cannot have seen any judge's
answer on these items. Y/N mean the same as the question's true/false: the claim says only what its quote says; the sentence
states no fact; the statement follows from its premises.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / "data" / "judge8"
SHEET = SET / "label_sheet.md"
SEED = 20261015
PER_KIND = 15
ASK = {"within_quote": "Does the claim say only what the quote says?",
       "no_fact": "Does the sentence state no fact about the literature (only introduce, order or signpost)?",
       "inference": "Does the statement follow from these claims alone, clause by clause, without overstating them?"}  # fmt: skip
_HEAD = re.compile(r"^## (L\d+) · (within_quote|no_fact|inference)\s*$")
_LABEL = re.compile(r"^(Label \(Y/N\): ?)(.*)$")


def test_items() -> list[dict]:
    rows = [json.loads(ln) for ln in (SET / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["split"] == "test"]


def sheet() -> None:
    if (SET / "labels.json").exists():
        sys.exit("labels are recorded; the sheet is not rebuilt")
    if any((SET / "raw" / "test").glob("*.jsonl")):
        sys.exit("the test run has happened: a sheet made now would not be blind")
    rng = random.Random(SEED)
    chosen = []
    for kind in ASK:
        pool = [i for i in test_items() if i["kind"] == kind]
        chosen += rng.sample(pool, min(PER_KIND, len(pool)))
    rng.shuffle(chosen)
    lines = ["# Judge set labels (Increment 8, test sample)", "",
             "Answer each item Y or N after `Label (Y/N):`, judging only from what is shown. Do not open data/judge8/raw/ or",
             "data/results/judge8_*.json. Change nothing but the letters.", ""]  # fmt: skip
    mapping = {}
    for n, it in enumerate(chosen, start=1):
        sid = f"L{n:02d}"
        mapping[sid] = it["id"]
        lines += [f"## {sid} · {it['kind']}", "", f"**{ASK[it['kind']]}**", "", it["state"], "", "Label (Y/N): ", ""]
    text = "\n".join(lines)
    SHEET.write_text(text, encoding="utf-8")
    (SET / "label_sheet_map.json").write_text(json.dumps({"built_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                          "sheet_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                                                          "items": mapping}, indent=1), encoding="utf-8")  # fmt: skip
    print(f"wrote {SHEET.relative_to(ROOT)} ({len(chosen)} items)")


def record(by: str, attribution: str) -> None:
    if (SET / "labels.json").exists():
        sys.exit("labels.json exists; labels are recorded once")
    if any((SET / "raw" / "test").glob("*.jsonl")):
        sys.exit("the test run has happened: labels recorded now are not blind")
    if by != "Chris" and not attribution.strip():
        sys.exit("--attribution is required when the labeller is not Chris")
    meta = json.loads((SET / "label_sheet_map.json").read_text(encoding="utf-8"))
    text = SHEET.read_text(encoding="utf-8").replace("\r\n", "\n")
    labels, problems, stripped, current = {}, [], [], None
    for line in text.split("\n"):
        head = _HEAD.match(line)
        if head:
            current = head.group(1)
        m = _LABEL.match(line)
        if m and current:
            letter = m.group(2).strip().upper()
            if letter not in ("Y", "N"):
                problems.append(f"{current}: {letter or 'no label'!r}")
            else:
                labels[meta["items"][current]] = letter == "Y"
            line = m.group(1)
        stripped.append(line)
    if hashlib.sha256("\n".join(stripped).encode("utf-8")).hexdigest() != meta["sheet_sha256"]:
        problems.append("item text differs from the sheet as built")
    if problems or len(labels) != len(meta["items"]):
        sys.exit("not recorded:\n  " + "\n  ".join(problems or ["not every item labelled"]))
    out = {"labelled_by": by, "attribution": attribution.strip() or None, "labelled_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "sheet_sha256": meta["sheet_sha256"], "labels": labels}  # fmt: skip
    (SET / "labels.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"recorded {len(labels)} labels by {by}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["sheet", "record"])
    ap.add_argument("--by", default="")
    ap.add_argument("--attribution", default="")
    args = ap.parse_args()
    if args.cmd == "sheet":
        sheet()
    else:
        if not args.by:
            sys.exit("--by is required")
        record(args.by, args.attribution)


if __name__ == "__main__":
    main()
