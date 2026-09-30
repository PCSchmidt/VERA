"""Write the checking sheet for the current inventory spot-check (gate inventory_verified).

Reads data/inventory_spotcheck.csv (drawn by tools/checks/check_inventory.py
--sample) and writes data/cache/spotcheck_sheet.md: per sampled row, the
recorded values and every source the checker needs, pointing at the papers
themselves rather than at anything this pipeline derived:

- the generated paper, and every PDF held for the parent (the version the
  inventory was built from and the camera-ready, when there is one);
- the venue statement to find in the parent (camera-ready footer or header,
  quoted, with its file), from data/parent_versions.csv.

Written after round 1 (data/inventory_spotcheck_round1.csv), whose sheet sent
the checker to an arXiv preprint's first page for the venue, which a preprint
doesn't carry, and gave only one version of each parent.

Usage: uv run python scripts/spotcheck_sheet.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cache" / "spotcheck_sheet.md"
FIELDS = [
    "domain", "subdomain", "method_name", "parent_title", "parent_venue", "parent_id_arxiv_or_doi",
    "gen_code_url", "parent_code_url", "reported_gain_pct", "compute_class", "candidate_for_p3",
]  # fmt: skip

HOW = """## How to judge a row

A row is `correct` only if every field below holds; otherwise `incorrect`,
with a note naming the field. Judge from the papers, not from other repo files.

- **Parent**: the generated paper's abstract or introduction presents this
  parent's method as the main baseline it improves on.
- **Parent id**: the arXiv id / OpenReview forum matches the parent PDF.
- **Venue**: the quoted venue statement appears in the listed parent file
  (page 1 footer for ICML and NeurIPS, page header for ICLR), or, where the
  source says so, in the authors' arXiv record. The venue must name the same
  conference and year as `parent_venue`.
- **gen_code_url**: `none` unless the generated paper links its own code.
- **parent_code_url**: the parent's own repository if **any** listed parent
  version links one (check the camera-ready too); `unknown` only if none does.
  Third-party repos a paper uses don't count.
- **compute_class**: matches the hardware the parent reports for a single
  run (`multi_gpu` only if one run needs more than one GPU). If the notes say
  "inferred", judge whether the inference is reasonable.
- **reported_gain_pct**: a number only if the generated paper states one
  percentage improvement over the parent; otherwise `unknown`.
- **notes**: quoted claims are accurate.
"""


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def main() -> None:
    sample = read(ROOT / "data" / "inventory_spotcheck.csv")
    inv = {r["gen_paper_id"]: r for r in read(ROOT / "data" / "corpus_inventory.csv")}
    parents = {r["parent_title"]: r for r in read(ROOT / "data" / "parent_papers.csv")}
    versions = {r["parent_title"]: r for r in read(ROOT / "data" / "parent_versions.csv")}
    seed = sample[0]["seed"] if sample else "?"
    out = [f"# Spot-check sheet (seed {seed})", "",
           "Record `correct` or `incorrect` (with a note) in `data/inventory_spotcheck.csv`.", "", HOW]  # fmt: skip
    for n, s in enumerate(sample, 1):
        r = inv[s["gen_paper_id"]]
        p, v = parents[r["parent_title"]], versions.get(r["parent_title"], {})
        files = [f"`{p['pdf_path']}` (version the inventory was built from)"]
        if v.get("camera_ready_pdf"):
            files.insert(0, f"`{v['camera_ready_pdf']}` (camera-ready)")
        evidence = v.get("venue_evidence") or "(none found; check the parent's OpenReview page)"
        out += [
            f"## {n}. {s['gen_paper_id']}", "",
            f"- Generated paper: `data/raw/scientisttwo/{s['gen_paper_id']}.pdf`",
            "- Parent PDFs: " + "; ".join(files),
            f"- Venue statement to find: \"{evidence}\" (in `{v.get('evidence_source') or '-'}`)", "",
            "| Field | Value |", "|---|---|",
            *[f"| {k} | {r[k]} |" for k in FIELDS],
            "", f"Notes: {r['notes']}", "",
        ]  # fmt: skip
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} for {len(sample)} rows (seed {seed})")


if __name__ == "__main__":
    main()
