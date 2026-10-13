# ruff: noqa: E501
"""Record Chris's labels for the real-case test split (Increment 7, gate `realcase_labelled`).

Reads `data/realcase/test_sheet.md` after Chris has put one letter after each `Label:`, checks every item is labelled
with an allowed letter and that no item's text was changed (the sheet with the letters removed must hash as built),
and writes `data/realcase/labels_test.json` with who labelled it and when. Refuses to overwrite existing labels.

    uv run python scripts/record_realcase_labels.py --by "Chris"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "realcase"
_HEAD = re.compile(r"^## (T\d+) · (claim|sentence|inference)\s*$")
_LABEL = re.compile(r"^(Label \([A-Z/]+\): ?)(.*)$")


def read_sheet(text: str, allowed: dict[str, dict]) -> tuple[dict[str, str], str, list[str]]:
    """(labels by sheet id, the sheet with every label removed, problems)."""
    labels, problems, stripped, current = {}, [], [], None
    for line in text.split("\n"):
        head = _HEAD.match(line)
        if head:
            current = head.groups()
        m = _LABEL.match(line)
        if m and current:
            letter = m.group(2).strip().upper()
            sid, kind = current
            if not letter:
                problems.append(f"{sid}: no label")
            elif letter not in allowed[kind]:
                problems.append(f"{sid}: {letter!r} is not one of {'/'.join(allowed[kind])}")
            else:
                labels[sid] = letter
            line = m.group(1)
        stripped.append(line)
    return labels, "\n".join(stripped), problems


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--by", required=True, help="who labelled the sheet")
    args = ap.parse_args()
    target = OUT / "labels_test.json"
    if target.exists():
        sys.exit("labels_test.json exists; labels are recorded once")
    meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
    text = (OUT / "test_sheet.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    labels, stripped, problems = read_sheet(text, meta["labels"])
    if hashlib.sha256(stripped.encode("utf-8")).hexdigest() != meta["sheet_sha256"]:
        problems.append("the sheet's item text differs from the sheet as built (only the letters after Label: may change)")
    items = [json.loads(ln) for ln in (OUT / "items.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    missing = sorted({it["sheet_id"] for it in items if it["split"] == "test"} - set(labels))
    if missing and not problems:
        problems.append(f"no label for {missing}")
    if problems:
        sys.exit("not recorded:\n  " + "\n  ".join(problems))
    out = {"labelled_by": args.by, "labelled_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "sheet_sha256": meta["sheet_sha256"], "labelled_sheet_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
           "labels": dict(sorted(labels.items()))}  # fmt: skip
    target.write_text(json.dumps(out, indent=1), encoding="utf-8")
    counts: dict[str, int] = {}
    for v in labels.values():
        counts[v] = counts.get(v, 0) + 1
    print(f"Recorded {len(labels)} labels by {args.by}: {counts}")


if __name__ == "__main__":
    main()
